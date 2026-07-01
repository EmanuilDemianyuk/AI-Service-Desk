"""Common bot handlers."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TgUser

from app.bot.keyboards import get_admin_main_menu, get_applicant_main_menu, get_executor_main_menu
from app.bot.states import AdminStates, ApplicantStates, ExecutorStates
from app.database.models import UserRole
from app.services import UserService

router = Router()

_HELP_TEXT = (
    "🤖 Команди бота HelpDesk:\n\n"
    "/start — запустити бота\n"
    "/help — показати це повідомлення\n"
    "/cancel — скасувати поточну операцію\n\n"
    "Для навігації використовуйте кнопки меню."
)


async def _do_start(
    from_user: TgUser,
    answer_target: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Route user to their role-specific main menu."""
    user = await user_service.get_or_create_user(
        telegram_id=from_user.id,
        full_name=from_user.full_name or "Unknown",
        username=from_user.username,
    )

    if user.role == UserRole.APPLICANT:
        await state.set_state(ApplicantStates.main_menu)
        await answer_target.answer(
            f"👋 Ласкаво просимо, {user.full_name}!\n\nВи зареєстровані як заявник.",
            reply_markup=get_applicant_main_menu(),
        )
    elif user.role == UserRole.EXECUTOR:
        await state.set_state(ExecutorStates.main_menu)
        await answer_target.answer(
            f"👋 Ласкаво просимо, {user.full_name}!\n\nВи зареєстровані як виконавець.",
            reply_markup=get_executor_main_menu(),
        )
    elif user.role == UserRole.ADMIN:
        await state.set_state(AdminStates.main_menu)
        await answer_target.answer(
            f"👋 Ласкаво просимо, {user.full_name}!\n\n👑 Ви адміністратор.",
            reply_markup=get_admin_main_menu(),
        )


# ── Standard command handlers ──────────────────────────────────────────────

@router.message(lambda msg: msg.text == "/start")
async def start(message: Message, state: FSMContext, user_service: UserService) -> None:
    await _do_start(message.from_user, message, state, user_service)


@router.message(lambda msg: msg.text == "/help")
async def help_command(message: Message) -> None:
    await message.answer(_HELP_TEXT)


@router.message(lambda msg: msg.text == "/cancel")
async def cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("❌ Операцію скасовано.")


# ── CommandGuard confirmation callbacks ────────────────────────────────────

@router.callback_query(F.data == "guard_confirm")
async def guard_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """User confirmed switching away from an active flow — clear state and run the pending command."""
    if callback.message is None:
        await callback.answer()
        return

    data = await state.get_data()
    pending_command = data.get("_pending_command", "/start")

    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)

    if pending_command == "/start":
        await _do_start(callback.from_user, callback.message, state, user_service)
    elif pending_command == "/help":
        await callback.message.answer(_HELP_TEXT)
    elif pending_command == "/cancel":
        await callback.message.answer("❌ Операцію скасовано.")
    else:
        # Unknown future command — safe fallback to start.
        await _do_start(callback.from_user, callback.message, state, user_service)

    await callback.answer()


@router.callback_query(F.data == "guard_cancel")
async def guard_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """User chose to stay in the current flow — remove the confirmation message and continue."""
    if callback.message is None:
        await callback.answer()
        return

    state_data = await state.get_data()
    state_data.pop("_pending_command", None)
    await state.set_data(state_data)

    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)

    await callback.answer("Продовжуємо поточну дію.")


@router.message(StateFilter(None))
async def fallback_restore_state(
    message: Message,
    state: FSMContext,
    user_service: UserService,
) -> None:
    """Restore the user's menu when FSM state is missing (e.g. after bot restart).

    MemoryStorage loses all states on process restart. Instead of silently
    ignoring messages, this handler detects the missing state and re-runs the
    /start logic so the user lands on the correct role-based main menu without
    having to type /start manually.
    """
    if message.from_user is None:
        return
    await _do_start(message.from_user, message, state, user_service)
