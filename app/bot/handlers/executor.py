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
)
from app.database.models import TaskStatus
from app.services import UserService, TaskService

router = Router()


@router.message(ExecutorStates.main_menu, F.text == "🆕 Нові завдання")
async def new_tasks(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Показати нові завдання."""
    tasks = await task_service.get_new_tasks()

    if not tasks:
        await message.answer(
            "🎉 Немає нових завдань наразі!",
            reply_markup=get_executor_main_menu(),
        )
        return

    response = "🆕 Нові завдання:\n\nОберіть завдання, щоб взяти в обробку:\n\n"
    for task in tasks:
        response += f"#{task.id} - {task.title}\n"

    await message.answer(
        response,
        reply_markup=get_task_list_keyboard(tasks),
    )
    await state.set_state(ExecutorStates.new_tasks)


@router.message(ExecutorStates.main_menu, F.text == "⏳ Мої завдання")
async def my_tasks(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show the tasks currently being performed by the worker."""
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Користувач не знайдений")
        return

    tasks = await task_service.get_executor_tasks(user.id)

    if not tasks:
        await message.answer(
            "📭 У вас немає завдань у процесі виконання.",
            reply_markup=get_executor_main_menu(),
        )
        return

    response = "⏳ Ваші завдання в процесі:\n\n"
    for task in tasks:
        response += f"#{task.id} - {task.title} ({task.status.value})\n"

    await message.answer(
        response,
        reply_markup=get_task_list_keyboard(tasks) if tasks else None,
    )
    await state.set_state(ExecutorStates.my_tasks)


@router.message(ExecutorStates.main_menu, F.text == "✅ Виконати завдання")
async def complete_task_start(message: Message, state: FSMContext) -> None:
    """Start task completion."""
    await state.set_state(ExecutorStates.complete_task)
    await message.answer("✅ Введіть номер завдання, яке потрібно виконати:")


@router.message(ExecutorStates.complete_task)
async def complete_task_feedback(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Request feedback for task completion."""
    try:
        task_id = int(message.text)
        task = await task_service.get_task(task_id)

        await state.update_data(task_id=task_id)
        await state.set_state(ExecutorStates.feedback_input)
        await message.answer(
            f"📝 Опишіть виконану роботу для завдання #{task_id}:",
        )

    except ValueError:
        await message.answer("❌ Невірний номер завдання. Будь ласка, введіть число.")
    except Exception as e:
        await message.answer(
            f"❌ Помилка: {str(e)}",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)


@router.message(ExecutorStates.feedback_input)
async def complete_task_submit(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
    user_service: UserService,
) -> None:
    """Submit task completion with feedback."""
    try:
        state_data = await state.get_data()
        task_id = state_data.get("task_id")

        task = await task_service.complete_task(task_id, message.text)

        # Notify applicant
        applicant = task.applicant
        try:
            from aiogram import Bot

            bot = Bot(token="")  # Will be set from context
            await bot.send_message(
                applicant.telegram_id,
                f"✅ Завдання #{task_id} завершено!\n\n"
                f"Відгуки: {message.text}\n\n"
                f"Будь ласка, підтвердьте, що робота виконана.",
            )
        except Exception as e:
            print(f"Помилка при надсиланні повідомлення заявнику: {e}")

        await message.answer(
            f"✅ Завдання #{task_id} позначено як очікує підтвердження від заявника!",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)

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
