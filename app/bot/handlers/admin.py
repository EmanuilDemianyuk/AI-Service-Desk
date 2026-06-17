"""Admin bot handlers."""

from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    get_admin_main_menu,
    get_admin_nav_keyboard,
    get_cancel_keyboard,
    get_create_role_keyboard,
    get_delete_confirmation_keyboard,
    get_role_keyboard,
    get_user_actions_keyboard,
    get_user_list_keyboard,
)
from app.bot.states import AdminStates
from app.database.models import UserRole
from app.exceptions import AuthorizationError, ValidationError
from app.services import TaskService, UserService

router = Router()

_ROLE_LABELS = {
    UserRole.APPLICANT: "Заявник",
    UserRole.EXECUTOR: "Виконавець",
    UserRole.ADMIN: "Адмін",
}

_MAX_NAME_LEN = 50


# ── Helpers ────────────────────────────────────────────────────────────────

async def _assert_admin(user_service: UserService, telegram_id: int) -> None:
    """Guard: raises AuthorizationError if the caller is not ADMIN."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user or user.role != UserRole.ADMIN:
        raise AuthorizationError("Access denied")


async def _show_user_list(target: Message | CallbackQuery, state: FSMContext, user_service: UserService) -> None:
    """Fetch all users and display the list with inline keyboard.

    Also replaces the reply keyboard with a navigation button so the user is
    never stuck — main-menu button handlers only fire in main_menu state.
    """
    users = await user_service.get_all_users()
    msg = target if isinstance(target, Message) else target.message

    if not users:
        await msg.answer("📭 Немає користувачів.", reply_markup=get_admin_main_menu())
        await state.set_state(AdminStates.main_menu)
        return

    lines = [f"{_ROLE_LABELS[u.role]} — {u.full_name} (@{u.username or 'N/A'})" for u in users]
    # Inline keyboard for user selection.
    await msg.answer(
        "👥 Користувачі:\n\n" + "\n".join(lines) + "\n\nОберіть користувача:",
        reply_markup=get_user_list_keyboard(users),
    )
    # Replace the reply keyboard so the user can always return to the main menu.
    await msg.answer("↕️", reply_markup=get_admin_nav_keyboard())
    await state.set_state(AdminStates.user_list)


# ── Universal navigation — back to main menu from any admin sub-state ─────

@router.message(
    StateFilter(
        AdminStates.user_list,
        AdminStates.user_detail,
        AdminStates.set_role_select_role,
        AdminStates.confirm_delete_user,
        AdminStates.task_list,
    ),
    F.text == "🏠 Головне меню",
)
async def admin_nav_to_main_menu(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Return to admin main menu from any browsing sub-state."""
    await _assert_admin(user_service, message.from_user.id)
    await state.set_state(AdminStates.main_menu)
    await message.answer("🏠 Головне меню", reply_markup=get_admin_main_menu())


# ── User list ──────────────────────────────────────────────────────────────

@router.message(AdminStates.main_menu, F.text == "👥 Користувачі")
async def admin_user_list(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, message.from_user.id)
    await _show_user_list(message, state, user_service)


@router.callback_query(AdminStates.user_list, F.data.startswith("admin_user_"))
async def admin_user_detail(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Show details and action buttons for a specific user."""
    await _assert_admin(user_service, callback_query.from_user.id)

    user_id = int(callback_query.data.split("_")[2])
    target = await user_service.get_user(user_id)
    is_self = target.telegram_id == callback_query.from_user.id

    detail = (
        f"👤 <b>{target.full_name}</b>\n"
        f"📱 Telegram ID: <code>{target.telegram_id}</code>\n"
        f"🏷 Username: @{target.username or 'N/A'}\n"
        f"👔 Роль: {_ROLE_LABELS[target.role]}\n"
        f"📅 Зареєстровано: {target.created_at.strftime('%Y-%m-%d')}"
    )
    if is_self:
        detail += "\n\n⚠️ Це ваш акаунт — видалення недоступне."

    await callback_query.message.answer(
        detail,
        reply_markup=get_user_actions_keyboard(user_id, is_self=is_self),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.user_detail)
    await callback_query.answer()


# ── Back to user list (from detail / role-change / delete-confirmation) ───

@router.callback_query(
    StateFilter(AdminStates.user_detail, AdminStates.set_role_select_role, AdminStates.confirm_delete_user),
    F.data == "user_back",
)
async def admin_back_to_users(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)
    await _show_user_list(callback_query, state, user_service)
    await callback_query.answer()


# ── Change role ────────────────────────────────────────────────────────────

@router.callback_query(AdminStates.user_detail, F.data.startswith("user_setrole_"))
async def admin_user_start_role_change(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)

    user_id = int(callback_query.data.split("_")[2])
    target = await user_service.get_user(user_id)

    await callback_query.message.answer(
        f"Поточна роль <b>{target.full_name}</b>: {_ROLE_LABELS[target.role]}\n\nОберіть нову роль:",
        reply_markup=get_role_keyboard(user_id),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.set_role_select_role)
    await callback_query.answer()


@router.callback_query(AdminStates.set_role_select_role, F.data.startswith("setrole_"))
async def admin_set_role(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)

    parts = callback_query.data.split("_")
    user_id, role_str = int(parts[1]), parts[2]
    new_role = UserRole(role_str)

    updated = await user_service.set_role(user_id, new_role)

    await callback_query.message.answer(
        f"✅ Роль <b>{updated.full_name}</b> змінено на: {_ROLE_LABELS[new_role]}",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.main_menu)
    await callback_query.answer()


# ── Delete user ────────────────────────────────────────────────────────────

@router.callback_query(AdminStates.user_detail, F.data.startswith("user_delete_"))
async def admin_user_delete_start(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)

    user_id = int(callback_query.data.split("_")[2])
    target = await user_service.get_user(user_id)

    await callback_query.message.answer(
        f"⚠️ Ви впевнені, що хочете видалити користувача <b>{target.full_name}</b>?\n\n"
        f"Усі його заявки будуть видалені разом з ним.",
        reply_markup=get_delete_confirmation_keyboard(user_id),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.confirm_delete_user)
    await callback_query.answer()


@router.callback_query(AdminStates.confirm_delete_user, F.data.startswith("confirm_delete_"))
async def admin_user_delete_execute(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)

    user_id = int(callback_query.data.split("_")[2])
    target = await user_service.get_user(user_id)
    full_name = target.full_name

    await user_service.delete_user(user_id)

    await callback_query.message.answer(
        f"🗑 Користувача <b>{full_name}</b> видалено.",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.main_menu)
    await callback_query.answer()


# ── Create user — multi-step form ──────────────────────────────────────────

@router.message(AdminStates.main_menu, F.text == "➕ Створити користувача")
async def admin_create_user_start(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, message.from_user.id)
    await state.clear()
    await state.set_state(AdminStates.create_user_first_name)
    await message.answer(
        "➕ Створення нового користувача\n\n"
        "Крок 1/4 — Введіть <b>ім'я</b> користувача:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )


@router.message(
    StateFilter(
        AdminStates.create_user_first_name,
        AdminStates.create_user_last_name,
        AdminStates.create_user_telegram_id,
        AdminStates.create_user_role,
    ),
    F.text == "❌ Скасувати",
)
async def admin_cancel_create_user(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminStates.main_menu)
    await message.answer("❌ Створення скасовано.", reply_markup=get_admin_main_menu())


@router.message(AdminStates.create_user_first_name)
async def admin_create_user_first_name(message: Message, state: FSMContext) -> None:
    first_name = message.text.strip()
    if not first_name:
        await message.answer("⚠️ Ім'я не може бути порожнім. Спробуйте ще раз:")
        return
    if len(first_name) > _MAX_NAME_LEN:
        await message.answer(f"⚠️ Ім'я занадто довге (максимум {_MAX_NAME_LEN} символів). Спробуйте ще раз:")
        return

    await state.update_data(first_name=first_name)
    await state.set_state(AdminStates.create_user_last_name)
    await message.answer(
        f"✅ Ім'я: <b>{first_name}</b>\n\nКрок 2/4 — Введіть <b>прізвище</b>:",
        parse_mode="HTML",
    )


@router.message(AdminStates.create_user_last_name)
async def admin_create_user_last_name(message: Message, state: FSMContext) -> None:
    last_name = message.text.strip()
    if not last_name:
        await message.answer("⚠️ Прізвище не може бути порожнім. Спробуйте ще раз:")
        return
    if len(last_name) > _MAX_NAME_LEN:
        await message.answer(f"⚠️ Прізвище занадто довге (максимум {_MAX_NAME_LEN} символів). Спробуйте ще раз:")
        return

    await state.update_data(last_name=last_name)
    await state.set_state(AdminStates.create_user_telegram_id)
    await message.answer(
        f"✅ Прізвище: <b>{last_name}</b>\n\nКрок 3/4 — Введіть <b>Telegram ID</b> (числовий):",
        parse_mode="HTML",
    )


@router.message(AdminStates.create_user_telegram_id)
async def admin_create_user_telegram_id(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, message.from_user.id)

    raw = message.text.strip()
    try:
        telegram_id = int(raw)
        if telegram_id <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Telegram ID має бути позитивним числом. Спробуйте ще раз:")
        return

    existing = await user_service.get_user_by_telegram_id(telegram_id)
    if existing:
        await message.answer(
            f"⚠️ Користувач з Telegram ID <code>{telegram_id}</code> вже існує: <b>{existing.full_name}</b>.\n"
            "Введіть інший Telegram ID або натисніть ❌ Скасувати:",
            parse_mode="HTML",
        )
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(AdminStates.create_user_role)
    await message.answer(
        f"✅ Telegram ID: <code>{telegram_id}</code>\n\nКрок 4/4 — Оберіть <b>роль</b>:",
        reply_markup=get_create_role_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(AdminStates.create_user_role, F.data.startswith("create_role_"))
async def admin_create_user_role(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    await _assert_admin(user_service, callback_query.from_user.id)

    role = UserRole(callback_query.data.split("_")[2])
    data = await state.get_data()

    full_name = f"{data['first_name']} {data['last_name']}"
    telegram_id: int = data["telegram_id"]

    try:
        user = await user_service.create_user(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
        )
    except ValidationError as exc:
        await callback_query.message.answer(
            f"❌ Помилка: {exc.message}\n\nСпробуйте ще раз або натисніть ❌ Скасувати.",
        )
        await callback_query.answer()
        return

    await state.clear()
    await state.set_state(AdminStates.main_menu)
    await callback_query.message.answer(
        f"✅ Користувача успішно створено!\n\n"
        f"👤 <b>{user.full_name}</b>\n"
        f"📱 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"👔 Роль: {_ROLE_LABELS[user.role]}",
        reply_markup=get_admin_main_menu(),
        parse_mode="HTML",
    )
    await callback_query.answer()


# ── Task list ──────────────────────────────────────────────────────────────

@router.message(AdminStates.main_menu, F.text == "📋 Всі завдання")
async def admin_task_list(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
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
