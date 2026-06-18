"""Executor bot handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.bot.states import ExecutorStates
from app.bot.keyboards import (
    get_executor_main_menu,
    get_task_action_keyboard,
    get_task_list_keyboard,
    get_complete_task_keyboard,
    get_my_tasks_keyboard,
    get_my_tasks_nav_keyboard,
    get_task_detail_nav_keyboard,
    get_complete_tasks_keyboard,
    get_confirm_complete_keyboard,
    get_new_tasks_nav_keyboard,
    get_accept_task_keyboard,
    STATUS_EMOJI,
)
from app.database.models import TaskStatus
from app.services import UserService, TaskService

router = Router()


async def _show_task_list(
    target: Message,
    telegram_id: int,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Shared logic: fetch executor tasks and render the task-list screen."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        await target.answer("❌ Користувач не знайдений")
        return

    tasks = await task_service.get_executor_tasks(user.id)

    # Update bottom ReplyKeyboard first — it persists for following messages.
    if not tasks:
        await target.answer(
            "📭 У вас поки немає завдань.",
            reply_markup=get_my_tasks_nav_keyboard(),
        )
        await state.set_state(ExecutorStates.my_tasks)
        return

    await target.answer(
        "📋 Мої завдання",
        reply_markup=get_my_tasks_nav_keyboard(),
    )
    await target.answer(
        "Оберіть завдання для перегляду:",
        reply_markup=get_my_tasks_keyboard(tasks),
    )
    await state.set_state(ExecutorStates.my_tasks)


async def _show_complete_task_list(
    target: Message,
    telegram_id: int,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Shared logic: fetch IN_PROGRESS tasks and render the complete-task-list screen."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        await target.answer("❌ Користувач не знайдений")
        return

    all_tasks = await task_service.get_executor_tasks(user.id)
    tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS]

    if not tasks:
        await target.answer(
            "📭 У вас немає активних завдань для завершення.",
            reply_markup=get_my_tasks_nav_keyboard(),
        )
        await state.set_state(ExecutorStates.complete_task)
        return

    await target.answer(
        "✅ Позначити як завершене",
        reply_markup=get_my_tasks_nav_keyboard(),
    )
    await target.answer(
        "Оберіть завдання для завершення:",
        reply_markup=get_complete_tasks_keyboard(tasks),
    )
    await state.set_state(ExecutorStates.complete_task)


async def _show_new_tasks(
    target: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Fetch NEW tasks and render the new-tasks list screen."""
    tasks = await task_service.get_new_tasks()
    if not tasks:
        await target.answer(
            "📭 Нових завдань немає.",
            reply_markup=get_new_tasks_nav_keyboard(),
        )
        await state.set_state(ExecutorStates.new_tasks)
        return
    await target.answer(
        "🆕 Нові завдання",
        reply_markup=get_new_tasks_nav_keyboard(),
    )
    await target.answer(
        "Оберіть завдання для перегляду:",
        reply_markup=get_task_list_keyboard(tasks),
    )
    await state.set_state(ExecutorStates.new_tasks)


@router.message(ExecutorStates.main_menu, F.text == "🆕 Нові завдання")
async def new_tasks(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Показати нові завдання."""
    await _show_new_tasks(message, state, task_service)


@router.message(ExecutorStates.new_tasks, F.text == "🏠 Головне меню")
async def new_tasks_go_main_menu(message: Message, state: FSMContext) -> None:
    """Return to executor main menu from new-tasks list screen."""
    await message.answer("🏠 Головне меню", reply_markup=get_executor_main_menu())
    await state.set_state(ExecutorStates.main_menu)


@router.callback_query(ExecutorStates.new_tasks, F.data.startswith("view_new_task_"))
async def view_new_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show full task card. Does NOT assign the executor — that requires ✅ Прийняти."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("view_new_task_"):])
        task = await task_service.get_task_with_relations(task_id)

        applicant_name = task.applicant.full_name if task.applicant else "—"
        created = task.created_at.strftime("%Y-%m-%d %H:%M")
        emoji = STATUS_EMOJI.get(task.status, "⚪")

        detail = (
            f"📋 Завдання #{task.id}\n\n"
            f"📌 {task.title}\n"
            f"📝 {task.description or '—'}\n\n"
            f"🚦 Статус: {emoji} {task.status.value}\n"
            f"⚡ Пріоритет: {task.priority.value}\n"
            f"🔧 Тип: {task.type.value}\n\n"
            f"👤 Заявник: {applicant_name}\n"
            f"📅 Створено: {created}\n"
        )

        await callback_query.message.answer(
            detail,
            reply_markup=get_task_detail_nav_keyboard(),
        )
        await callback_query.message.answer(
            "Прийняти завдання до виконання?",
            reply_markup=get_accept_task_keyboard(task_id),
        )
        await state.set_state(ExecutorStates.new_task_detail)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.new_task_detail, F.text == "⬅️ Назад")
async def new_task_detail_go_back(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Return to new-tasks list from task-detail screen."""
    await _show_new_tasks(message, state, task_service)


@router.callback_query(ExecutorStates.new_task_detail, F.data.startswith("accept_task_"))
async def accept_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Assign executor and take task into progress."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("accept_task_"):])
        user = await user_service.get_user_by_telegram_id(callback_query.from_user.id)
        if not user:
            await callback_query.message.answer("❌ Користувач не знайдений")
            return

        await task_service.take_task(task_id, user.id)

        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback_query.message.answer(
            f"✅ Завдання #{task_id} прийнято до виконання!",
        )
        await _show_task_list(
            callback_query.message,
            callback_query.from_user.id,
            state,
            user_service,
            task_service,
        )

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.main_menu, F.text == "⏳ Мої завдання")
async def my_tasks(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show the tasks currently being performed by the worker."""
    await _show_task_list(message, message.from_user.id, state, user_service, task_service)


@router.callback_query(F.data.startswith("view_my_task_"))
async def view_my_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show full details of a selected task."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("view_my_task_"):])
        task = await task_service.get_task(task_id)

        emoji = STATUS_EMOJI.get(task.status, "⚪")
        detail = (
            f"📋 Завдання #{task.id}\n\n"
            f"📌 {task.title}\n"
            f"📝 {task.description or '—'}\n\n"
            f"Статус: {emoji} {task.status.value}\n"
            f"Пріоритет: {task.priority.value}\n"
            f"Тип: {task.type.value}\n"
        )
        if task.feedback:
            detail += f"\n💬 Відгук: {task.feedback}"

        await callback_query.message.answer(
            detail,
            reply_markup=get_task_detail_nav_keyboard(),
        )
        await state.set_state(ExecutorStates.task_in_progress)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.my_tasks, F.text == "🏠 Головне меню")
async def my_tasks_go_main_menu(
    message: Message,
    state: FSMContext,
) -> None:
    """Return to executor main menu from task-list screen."""
    await message.answer("🏠 Головне меню", reply_markup=get_executor_main_menu())
    await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.task_in_progress, F.text == "⬅️ Назад")
async def task_detail_go_back(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Return to task list from task-detail screen."""
    await _show_task_list(message, message.from_user.id, state, user_service, task_service)


@router.message(ExecutorStates.main_menu, F.text == "✅ Позначити як завершене")
async def complete_task_section(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Enter the complete-task section: show IN_PROGRESS task list."""
    await _show_complete_task_list(message, message.from_user.id, state, user_service, task_service)


@router.message(ExecutorStates.complete_task, F.text == "🏠 Головне меню")
async def complete_task_go_main_menu(message: Message, state: FSMContext) -> None:
    """Return to executor main menu from the complete-task list screen."""
    await message.answer("🏠 Головне меню", reply_markup=get_executor_main_menu())
    await state.set_state(ExecutorStates.main_menu)


@router.callback_query(F.data.startswith("complete_task_"))
async def complete_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show full task detail + confirm button for a selected IN_PROGRESS task."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data[len("complete_task_"):])
        task = await task_service.get_task(task_id)

        emoji = STATUS_EMOJI.get(task.status, "⚪")
        detail = (
            f"📋 Завдання #{task.id}\n\n"
            f"📌 {task.title}\n"
            f"📝 {task.description or '—'}\n\n"
            f"Статус: {emoji} {task.status.value}\n"
            f"Пріоритет: {task.priority.value}\n"
            f"Тип: {task.type.value}\n"
        )

        await callback_query.message.answer(
            detail,
            reply_markup=get_task_detail_nav_keyboard(),
        )
        await callback_query.message.answer(
            "Підтвердіть завершення завдання:",
            reply_markup=get_confirm_complete_keyboard(task_id),
        )
        await state.set_state(ExecutorStates.task_confirmation)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.task_confirmation, F.text == "⬅️ Назад")
async def confirm_task_go_back(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Return to IN_PROGRESS task list from task-detail/confirmation screen."""
    await _show_complete_task_list(message, message.from_user.id, state, user_service, task_service)


@router.callback_query(F.data.startswith("confirm_complete_"))
async def confirm_complete_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
) -> None:
    """Request feedback text before completing the task."""
    await callback_query.answer()
    task_id = int(callback_query.data[len("confirm_complete_"):])
    await state.update_data(task_id=task_id)
    await state.set_state(ExecutorStates.feedback_input)
    await callback_query.message.answer(
        "📝 Опишіть, будь ласка, що було виконано. Без коментаря завдання не може бути завершене.",
    )


@router.message(ExecutorStates.feedback_input, F.text == "⬅️ Назад")
async def feedback_go_back(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Abort feedback input and return to IN_PROGRESS task list."""
    await state.clear()
    await _show_complete_task_list(message, message.from_user.id, state, user_service, task_service)


@router.message(ExecutorStates.feedback_input)
async def complete_task_submit(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
    user_service: UserService,
) -> None:
    """Submit feedback and complete the task."""
    feedback = message.text.strip() if message.text else ""
    if not feedback:
        await message.answer(
            "📝 Коментар не може бути порожнім. Опишіть, будь ласка, що було виконано.",
        )
        return

    try:
        state_data = await state.get_data()
        task_id = state_data.get("task_id")

        await task_service.complete_task(task_id, feedback)
        await state.clear()

        await message.answer(
            f"✅ Завдання #{task_id} передано на підтвердження заявнику!",
        )
        await _show_complete_task_list(message, message.from_user.id, state, user_service, task_service)

    except Exception as e:
        await message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.callback_query(F.data.startswith("take_task_"))
async def take_task_callback(
    callback_query: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Handle take task action."""
    await callback_query.answer()
    try:
        task_id = int(callback_query.data.split("_")[2])
        user = await user_service.get_user_by_telegram_id(callback_query.from_user.id)

        if not user:
            await callback_query.message.answer("❌ Користувач не знайдений")
            return

        task = await task_service.take_task(task_id, user.id)

        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback_query.message.answer(
            f"✅ Завдання #{task_id} взято в обробку!\n\n"
            f"Перейдіть до «⏳ Мої завдання» для відстеження.",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)

    except Exception as e:
        await callback_query.message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)
