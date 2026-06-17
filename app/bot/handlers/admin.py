"""Admin bot handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.states import AdminStates
from app.bot.keyboards import get_admin_main_menu, get_user_list_keyboard, get_role_keyboard
from app.database.models import UserRole
from app.exceptions import AuthorizationError
from app.services import UserService, TaskService

router = Router()

_ROLE_LABELS = {
    UserRole.APPLICANT: "Заявник",
    UserRole.EXECUTOR: "Виконавець",
    UserRole.ADMIN: "Адмін",
}


async def _assert_admin(user_service: UserService, telegram_id: int) -> None:
    """Guard: raises AuthorizationError if the caller is not ADMIN."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user or user.role != UserRole.ADMIN:
        raise AuthorizationError("Access denied")


@router.message(AdminStates.main_menu, F.text == "👥 Користувачі")
async def admin_user_list(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Show all users with roles and an inline keyboard to manage them."""
    await _assert_admin(user_service, message.from_user.id)

    users = await user_service.get_all_users()
    if not users:
        await message.answer("📭 Немає користувачів.")
        return

    lines = [f"{_ROLE_LABELS[u.role]} — {u.full_name} (@{u.username or 'N/A'})" for u in users]
    text = "👥 Користувачі:\n\n" + "\n".join(lines) + "\n\nОберіть користувача, щоб змінити роль:"

    await message.answer(text, reply_markup=get_user_list_keyboard(users))
    await state.set_state(AdminStates.user_list)


@router.callback_query(AdminStates.user_list, F.data.startswith("admin_user_"))
async def admin_select_user(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Show role selection keyboard for the chosen user."""
    await _assert_admin(user_service, callback_query.from_user.id)

    user_id = int(callback_query.data.split("_")[2])
    target = await user_service.get_user(user_id)

    await callback_query.message.answer(
        f"Поточна роль {target.full_name}: {_ROLE_LABELS[target.role]}\nОберіть нову роль:",
        reply_markup=get_role_keyboard(user_id),
    )
    await state.set_state(AdminStates.set_role_select_role)
    await callback_query.answer()


@router.callback_query(AdminStates.set_role_select_role, F.data.startswith("setrole_"))
async def admin_set_role(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Apply the selected role to the target user."""
    await _assert_admin(user_service, callback_query.from_user.id)

    parts = callback_query.data.split("_")
    user_id, role_str = int(parts[1]), parts[2]
    new_role = UserRole(role_str)

    updated = await user_service.set_role(user_id, new_role)

    await callback_query.message.answer(
        f"✅ Роль {updated.full_name} змінено на: {_ROLE_LABELS[new_role]}",
        reply_markup=get_admin_main_menu(),
    )
    await state.set_state(AdminStates.main_menu)
    await callback_query.answer()


@router.message(AdminStates.main_menu, F.text == "📋 Всі завдання")
async def admin_task_list(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show a summary of all tasks."""
    await _assert_admin(user_service, message.from_user.id)

    tasks = await task_service.get_all_tasks()
    if not tasks:
        await message.answer("📭 Завдань немає.", reply_markup=get_admin_main_menu())
        return

    lines = [f"#{t.id} | {t.status.value} | {t.title}" for t in tasks[:20]]
    text = "📋 Всі завдання:\n\n" + "\n".join(lines)
    if len(tasks) > 20:
        text += f"\n\n…та ще {len(tasks) - 20} завдань."

    await message.answer(text, reply_markup=get_admin_main_menu())
    await state.set_state(AdminStates.main_menu)
