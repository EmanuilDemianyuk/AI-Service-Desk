"""Executor keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from app.database.models import TaskStatus

STATUS_EMOJI: dict = {
    TaskStatus.NEW: "🔵",
    TaskStatus.IN_PROGRESS: "🟡",
    TaskStatus.WAITING_APPLICANT: "🟠",
    TaskStatus.WAITING_EXECUTOR: "🟣",
    TaskStatus.DONE: "🟢",
    TaskStatus.CANCELLED: "🔴",
}


def get_executor_main_menu() -> ReplyKeyboardMarkup:
    """Get executor main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Нові завдання")],
            [KeyboardButton(text="⏳ Мої завдання")],
            [KeyboardButton(text="✅ Позначити як завершене")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Get task action keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Почати виконання",
                    callback_data=f"take_task_{task_id}",
                ),
            ],
        ]
    )
    return keyboard


def get_complete_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Get complete task keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Позначити як завершене",
                    callback_data=f"mark_complete_{task_id}",
                ),
            ],
        ]
    )
    return keyboard


def get_task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """InlineKeyboard listing NEW tasks for preview (no auto-assignment)."""
    buttons = []
    for task in tasks:
        emoji = STATUS_EMOJI.get(task.status, "⚪")
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} #{task.id} — {task.title}",
                callback_data=f"view_new_task_{task.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_new_tasks_nav_keyboard() -> ReplyKeyboardMarkup:
    """Bottom navigation for the new-tasks screen: single 🏠 Головне меню button."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Головне меню")]],
        resize_keyboard=True,
    )


def get_accept_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """InlineKeyboard on new-task detail card with accept button."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Прийняти",
            callback_data=f"accept_task_{task_id}",
        )
    ]])


def get_my_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Get my tasks list keyboard with status emoji and title per task."""
    buttons = []
    for task in tasks:
        emoji = STATUS_EMOJI.get(task.status, "⚪")
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {task.title}",
                callback_data=f"view_my_task_{task.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_my_tasks_nav_keyboard() -> ReplyKeyboardMarkup:
    """Bottom navigation for the task-list screen: single 🏠 Головне меню button."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Головне меню")]],
        resize_keyboard=True,
    )


def get_task_detail_nav_keyboard() -> ReplyKeyboardMarkup:
    """Bottom navigation for the task-detail screen: single ⬅️ Назад button."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True,
    )


def get_complete_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """InlineKeyboard listing IN_PROGRESS tasks for the complete-task flow."""
    buttons = []
    for task in tasks:
        emoji = STATUS_EMOJI.get(task.status, "⚪")
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {task.title}",
                callback_data=f"complete_task_{task.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_complete_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """InlineKeyboard for task-detail screen in the complete-task flow."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Підтвердити завершення",
            callback_data=f"confirm_complete_{task_id}",
        )
    ]])
