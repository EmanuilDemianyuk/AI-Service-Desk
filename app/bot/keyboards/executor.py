"""Executor keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def get_executor_main_menu() -> ReplyKeyboardMarkup:
    """Get executor main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 New Tasks")],
            [KeyboardButton(text="⏳ My Tasks")],
            [KeyboardButton(text="✅ Complete Task")],
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
                    text="Take into Progress",
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
                    text="Mark as Complete",
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
                    callback_data=f"task_select_{task.id}",
                ),
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
