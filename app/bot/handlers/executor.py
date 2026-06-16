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


@router.message(ExecutorStates.main_menu, F.text == "🆕 New Tasks")
async def new_tasks(
    message: Message,
    state: FSMContext,
    task_service: TaskService,
) -> None:
    """Show new tasks."""
    tasks = await task_service.get_new_tasks()

    if not tasks:
        await message.answer(
            "🎉 No new tasks at the moment!",
            reply_markup=get_executor_main_menu(),
        )
        return

    response = "🆕 New Tasks:\n\n"
    keyboard_buttons = []

    for task in tasks:
        response += f"#{task.id} - {task.title}\n"
        keyboard_buttons.append([
            F.CallbackButton(
                text=f"#{task.id}",
                callback_data=f"take_task_{task.id}",
            )
        ])

    await message.answer(
        response,
        reply_markup=get_task_list_keyboard(tasks) if tasks else None,
    )
    await state.set_state(ExecutorStates.new_tasks)


@router.message(ExecutorStates.main_menu, F.text == "⏳ My Tasks")
async def my_tasks(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    task_service: TaskService,
) -> None:
    """Show executor's tasks in progress."""
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ User not found")
        return

    tasks = await task_service.get_executor_tasks(user.id)

    if not tasks:
        await message.answer(
            "📭 You have no tasks in progress.",
            reply_markup=get_executor_main_menu(),
        )
        return

    response = "⏳ Your Tasks in Progress:\n\n"
    for task in tasks:
        response += f"#{task.id} - {task.title} ({task.status.value})\n"

    await message.answer(
        response,
        reply_markup=get_task_list_keyboard(tasks) if tasks else None,
    )
    await state.set_state(ExecutorStates.my_tasks)


@router.message(ExecutorStates.main_menu, F.text == "✅ Complete Task")
async def complete_task_start(message: Message, state: FSMContext) -> None:
    """Start task completion."""
    await state.set_state(ExecutorStates.complete_task)
    await message.answer("✅ Enter task number to complete:")


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
            f"📝 Describe the work completed for task #{task_id}:",
        )

    except ValueError:
        await message.answer("❌ Invalid task number. Please enter a number.")
    except Exception as e:
        await message.answer(
            f"❌ Error: {str(e)}",
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
                f"✅ Task #{task_id} has been completed!\n\n"
                f"Feedback: {message.text}\n\n"
                f"Please confirm the work is complete.",
            )
        except Exception as e:
            print(f"Applicant notification error: {e}")

        await message.answer(
            f"✅ Task #{task_id} marked as waiting for applicant confirmation!",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)

    except Exception as e:
        await message.answer(
            f"❌ Error: {str(e)}",
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
    try:
        task_id = int(callback_query.data.split("_")[2])
        user = await user_service.get_user_by_telegram_id(callback_query.from_user.id)

        if not user:
            await callback_query.answer("❌ User not found")
            return

        task = await task_service.take_task(task_id, user.id)

        await callback_query.message.answer(
            f"✅ Task #{task_id} taken into progress!",
            reply_markup=get_executor_main_menu(),
        )
        await state.set_state(ExecutorStates.main_menu)
        await callback_query.answer()

    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}")
