"""Common bot handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.states import ApplicantStates, ExecutorStates
from app.bot.keyboards import get_applicant_main_menu, get_executor_main_menu
from app.database.models import UserRole
from app.services import UserService

router = Router()


@router.message(lambda msg: msg.text == "/start")
async def start(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Handle /start command."""
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name or "Unknown",
        username=message.from_user.username,
    )

    if user.role == UserRole.APPLICANT:
        await state.set_state(ApplicantStates.main_menu)
        await message.answer(
            f"👋 Ласкаво просимо, {user.full_name}!\n\nВи зареєстровані як заявник.",
            reply_markup=get_applicant_main_menu(),
        )
    elif user.role == UserRole.EXECUTOR:
        await state.set_state(ExecutorStates.main_menu)
        await message.answer(
            f"👋 Ласкаво просимо, {user.full_name}!\n\nВи зареєстровані як виконавець.",
            reply_markup=get_executor_main_menu(),
        )


@router.message(lambda msg: msg.text == "/help")
async def help_command(message: Message) -> None:
    """Handle /help command."""
    help_text = """
    🤖 Команди бота HelpDesk:
    
    /start — запустити бота
    /help — показати це повідомлення довідки
    /my_tasks — показати ваші завдання
    /new_tasks — показати нові завдання (лише для виконавців)
    
    Для навігації використовуйте кнопки меню.
    """
    await message.answer(help_text)


@router.message(lambda msg: msg.text == "/cancel")
async def cancel(message: Message, state: FSMContext) -> None:
    """Handle /cancel command."""
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("❌ Operation cancelled.")
