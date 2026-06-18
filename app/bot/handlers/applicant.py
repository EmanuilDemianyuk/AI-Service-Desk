"""Applicant bot handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from app.bot.states import ApplicantStates
from app.bot.keyboards import (
    get_applicant_main_menu,
    get_applicant_nav_keyboard,
    get_applicant_detail_nav_keyboard,
    get_my_requests_keyboard,
    get_waiting_tasks_keyboard,
    get_task_confirm_keyboard,
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
        reply_markup=get_applicant_detail_nav_keyboard(),
    )


@router.message(ApplicantStates.request_description, F.text == "⬅️ Назад")
async def cancel_create_request(message: Message, state: FSMContext) -> None:
    """Cancel request creation and return to main menu."""
    await state.clear()
    await message.answer("🏠 Головне меню", reply_markup=get_applicant_main_menu())
    await state.set_state(ApplicantStates.main_menu)


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


async def _show_my_requests_list(
    target: Message,
    telegram_id: int,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Shared logic: fetch all user requests and render the my-requests list screen."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        await target.answer("❌ Користувач не знайдений")
        return

    tasks = await task_service.get_user_tasks(user.id)

    if not tasks:
        await target.answer(
            "📭 У вас поки немає створених запитів.",
            reply_markup=get_applicant_nav_keyboard(),
        )
        await state.set_state(ApplicantStates.my_requests)
        return

    await target.answer(
        "📋 Мої запити",
        reply_markup=get_applicant_nav_keyboard(),
    )
    await target.answer(
        "Оберіть запит для перегляду:",
        reply_markup=get_my_requests_keyboard(tasks),
    )
    await state.set_state(ApplicantStates.my_requests)


@router.message(ApplicantStates.main_menu, F.text == "📋 Мої запити")
async def my_requests(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show user's requests."""
    await _show_my_requests_list(message, message.from_user.id, state, user_service, task_service)


@router.message(ApplicantStates.my_requests, F.text == "🏠 Головне меню")
async def my_requests_go_main_menu(message: Message, state: FSMContext) -> None:
    """Return to applicant main menu from my-requests list screen."""
    await message.answer("🏠 Головне меню", reply_markup=get_applicant_main_menu())
    await state.set_state(ApplicantStates.main_menu)


@router.callback_query(F.data.startswith("view_request_"))
async def view_request_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show full details of a user request."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("view_request_"):])
        task = await task_service.get_task_with_relations(task_id)

        executor_name = task.executor.full_name if task.executor else "—"
        applicant_name = task.applicant.full_name if task.applicant else "—"
        created = task.created_at.strftime("%Y-%m-%d %H:%M")
        closed = task.closed_at.strftime("%Y-%m-%d %H:%M") if task.closed_at else "—"

        STATUS_EMOJI = {
            "NEW": "🔵", "IN_PROGRESS": "🟡", "WAITING_APPLICANT": "🟠",
            "WAITING_EXECUTOR": "🟣", "DONE": "🟢", "CANCELLED": "🔴",
        }
        emoji = STATUS_EMOJI.get(task.status.value, "⚪")

        detail = (
            f"📋 Запит #{task.id}\n\n"
            f"📌 {task.title}\n"
            f"📝 {task.description or '—'}\n\n"
            f"🚦 Статус: {emoji} {task.status.value}\n"
            f"⚡ Пріоритет: {task.priority.value}\n"
            f"🔧 Тип: {task.type.value}\n\n"
            f"👤 Заявник: {applicant_name}\n"
            f"🛠  Виконавець: {executor_name}\n\n"
            f"📅 Створено: {created}\n"
            f"📅 Закрито: {closed}\n"
        )
        if task.feedback:
            detail += f"\n💬 Коментар виконавця: {task.feedback}\n"

        await callback_query.message.answer(
            detail,
            reply_markup=get_applicant_detail_nav_keyboard(),
        )
        await state.set_state(ApplicantStates.my_request_detail)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_applicant_main_menu(),
        )
        await state.set_state(ApplicantStates.main_menu)


@router.message(ApplicantStates.my_request_detail, F.text == "⬅️ Назад")
async def my_request_detail_go_back(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Return to requests list from request detail screen."""
    await _show_my_requests_list(message, message.from_user.id, state, user_service, task_service)


async def _show_confirm_requests_list(
    target: Message,
    telegram_id: int,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Shared logic: fetch WAITING_APPLICANT tasks and render the confirm-requests screen."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        await target.answer("❌ Користувач не знайдений")
        return

    tasks = await task_service.get_user_waiting_tasks(user.id)

    if not tasks:
        await target.answer(
            "📭 Немає запитів, що очікують підтвердження.",
            reply_markup=get_applicant_nav_keyboard(),
        )
        await state.set_state(ApplicantStates.confirm_requests)
        return

    await target.answer(
        "✅ Підтвердити запит",
        reply_markup=get_applicant_nav_keyboard(),
    )
    await target.answer(
        "Оберіть запит для перегляду:",
        reply_markup=get_waiting_tasks_keyboard(tasks),
    )
    await state.set_state(ApplicantStates.confirm_requests)


@router.message(ApplicantStates.main_menu, F.text == "✅ Підтвердити запит")
async def confirm_requests_section(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Enter the confirm-requests section."""
    await _show_confirm_requests_list(message, message.from_user.id, state, user_service, task_service)


@router.message(ApplicantStates.confirm_requests, F.text == "🏠 Головне меню")
async def confirm_requests_go_main_menu(message: Message, state: FSMContext) -> None:
    """Return to applicant main menu from confirm-requests list screen."""
    await message.answer("🏠 Головне меню", reply_markup=get_applicant_main_menu())
    await state.set_state(ApplicantStates.main_menu)


@router.callback_query(F.data.startswith("wait_view_"))
async def wait_view_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show full details of a WAITING_APPLICANT task."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("wait_view_"):])
        task = await task_service.get_task_with_relations(task_id)

        executor_name = task.executor.full_name if task.executor else "—"
        applicant_name = task.applicant.full_name if task.applicant else "—"
        closed = task.closed_at.strftime("%Y-%m-%d %H:%M") if task.closed_at else "—"

        detail = (
            f"📋 Запит #{task.id}\n\n"
            f"📌 {task.title}\n"
            f"📝 {task.description or '—'}\n\n"
            f"👤 Заявник: {applicant_name}\n"
            f"🔧 Виконавець: {executor_name}\n"
            f"Статус: 🟠 {task.status.value}\n"
            f"Пріоритет: {task.priority.value}\n\n"
            f"💬 Коментар виконавця: {task.feedback or '—'}\n"
            f"📅 Дата завершення: {closed}\n"
        )

        await state.update_data(task_id=task_id)

        await callback_query.message.answer(
            detail,
            reply_markup=get_applicant_detail_nav_keyboard(),
        )
        await callback_query.message.answer(
            "Підтвердьте або скасуйте виконання:",
            reply_markup=get_task_confirm_keyboard(task_id),
        )
        await state.set_state(ApplicantStates.confirm_request_detail)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_applicant_main_menu(),
        )
        await state.set_state(ApplicantStates.main_menu)


@router.message(ApplicantStates.confirm_request_detail, F.text == "⬅️ Назад")
async def confirm_request_detail_go_back(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Return to WAITING_APPLICANT task list from detail screen."""
    await _show_confirm_requests_list(message, message.from_user.id, state, user_service, task_service)


@router.callback_query(F.data.in_({"confirm_yes", "confirm_no"}))
async def confirm_task_completion(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
    user_service: UserService,
) -> None:
    """Handle task confirmation or rejection by applicant."""
    await callback_query.answer()
    try:
        state_data = await state.get_data()
        task_id = state_data.get("task_id")

        if task_id is None:
            await callback_query.message.answer(
                "❌ Не вдалося визначити завдання. Будь ласка, спробуйте ще раз.",
                reply_markup=get_applicant_main_menu(),
            )
            await state.set_state(ApplicantStates.main_menu)
            return

        if callback_query.data == "confirm_yes":
            await task_service.confirm_task(task_id)
            await callback_query.message.answer(
                f"✅ Завдання #{task_id} підтверджено як завершене!",
            )
        else:
            await task_service.reject_task(task_id)
            await callback_query.message.answer(
                f"↩️ Завдання #{task_id} повернуто виконавцю на доопрацювання.",
            )

        await _show_confirm_requests_list(
            callback_query.message,
            callback_query.from_user.id,
            state,
            user_service,
            task_service,
        )

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_applicant_main_menu(),
        )
        await state.set_state(ApplicantStates.main_menu)
