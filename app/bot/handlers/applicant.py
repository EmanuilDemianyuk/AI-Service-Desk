"""Applicant bot handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from app.bot.states import ApplicantStates
from app.bot.keyboards import (
    get_applicant_main_menu,
    get_confirmation_keyboard,
    get_task_actions_keyboard,
)
from app.services import UserService, TaskService, AIService, NotionService

router = Router()


@router.message(ApplicantStates.main_menu, F.text == "📝 Створити запит")
async def create_request_start(message: Message, state: FSMContext) -> None:
    """Start creating a request."""
    await state.set_state(ApplicantStates.request_description)
    await message.answer(
        "📝 Опишіть вашу проблему:\n\nБудь ласка, надайте детальний опис проблеми.",
    )


@router.message(ApplicantStates.request_description)
async def create_request_description(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
    ai_service: AIService,
    notion_service: NotionService,
) -> None:
    """Process request description."""
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Користувач не знайдений")
        return

    # Classify ticket using AI
    try:
        await message.answer("⏳ Класифікація вашого запиту... Будь ласка, зачекайте.")
        classification = await ai_service.classify_ticket(message.text)

        # Get executor
        executor = await user_service.get_executor_for_type(classification.type.value)

        # Create task in database
        task = await task_service.create_task(
            applicant_id=user.id,
            title=classification.title,
            description=classification.description,
            task_type=classification.type,
            priority=classification.priority,
            executor_id=executor.id,
        )

        # Create task in Notion
        try:
            notion_page_id = await notion_service.create_task_page(task)
            if notion_page_id:
                await task_service.update_notion_page_id(task.id, notion_page_id)
        except Exception as e:
            print(f"Помилка інтеграції з Notion: {e}")

        # Send confirmation to applicant
        response_text = f"""
✅ Запит #{task.id} створено!

📋 Деталі:
• Тип: {classification.type.value}
• Пріоритет: {classification.priority.value}
• Виконавець: {executor.full_name}
• Назва: {classification.title}
• Опис: {classification.description}

Статус: NEW
Виконавець зв'яжеться з вами найближчим часом.
        """
        await message.answer(response_text, reply_markup=get_applicant_main_menu())

        # Notify executor
        try:
            from aiogram import Bot

            bot = Bot(token="")  # Will be set from context
            await bot.send_message(
                executor.telegram_id,
                f"🔔 Нове завдання призначено вам:\n\n#{task.id} - {classification.title}\n\nЗаявник: {user.full_name}",
            )
        except Exception as e:
            print(f"Помилка сповіщення виконавця: {e}")

        await state.set_state(ApplicantStates.main_menu)

    except Exception as e:
        await message.answer(
            f"❌ Помилка обробки запиту: {str(e)}\n\nБудь ласка, спробуйте ще раз.",
            reply_markup=get_applicant_main_menu(),
        )
        await state.set_state(ApplicantStates.main_menu)


@router.message(ApplicantStates.main_menu, F.text == "📋 Мої запити")
async def my_requests(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show user's requests."""
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Користувач не знайдений")
        return

    tasks = await task_service.get_user_tasks(user.id)

    if not tasks:
        await message.answer("📭 У вас немає запитів.")
        return

    response = "📋 Ваші запити:\n\n"
    for task in tasks:
        response += f"#{task.id} | {task.title} | {task.status.value}\n"

    await message.answer(response, reply_markup=get_applicant_main_menu())


@router.message(ApplicantStates.main_menu, F.text == "🔍 Статус запиту")
async def request_status_start(message: Message, state: FSMContext) -> None:
    """Start request status check."""
    await state.set_state(ApplicantStates.status_input)
    await message.answer("🔍 Введіть номер запиту:")

@router.message(ApplicantStates.status_input)
async def request_status_show(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show request status."""
    try:
        task_id = int(message.text)
        task = await task_service.get_task(task_id)

        response = f"""
📋 Запит #{task.id}

Назва: {task.title}

Статус: {task.status.value}

Виконавець: {task.executor.full_name if task.executor else "Не призначено"}
Тип: {task.type.value}
Пріоритет: {task.priority.value}

Створено: {task.created_at.strftime('%Y-%m-%d %H:%M')}
        """

        await message.answer(response, reply_markup=get_applicant_main_menu())
        await state.set_state(ApplicantStates.main_menu)

    except ValueError:
        await message.answer("❌ Недійсний номер запиту. Будь ласка, введіть номер.")
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}", reply_markup=get_applicant_main_menu())
        await state.set_state(ApplicantStates.main_menu)


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_task_completion(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Handle task confirmation."""
    action = callback_query.data.split("_")[1]
    task_id = int(callback_query.data.split("_")[2]) if len(callback_query.data.split("_")) > 2 else 0

    # Get task_id from state data
    state_data = await state.get_data()
    task_id = state_data.get("task_id")

    if action == "yes":
        task = await task_service.confirm_task(task_id)
        await callback_query.message.answer(
            f"✅ Завдання #{task_id} підтверджено як завершене!",
            reply_markup=get_applicant_main_menu(),
        )
    else:
        task = await task_service.reject_task(task_id)
        await callback_query.message.answer(
            f"❌ Завдання #{task_id} відхилено. Виконавець продовжить роботу.",
            reply_markup=get_applicant_main_menu(),
        )

    await state.set_state(ApplicantStates.main_menu)
    await callback_query.answer()
