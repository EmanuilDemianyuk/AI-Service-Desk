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
    """Get task list keyboard."""
    buttons = []
    for task in tasks:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"#{task.id} - {task.title}",
                    callback_data=f"take_task_{task.id}",
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
