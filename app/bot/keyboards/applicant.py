"""Applicant keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from app.bot.keyboards.localizer import STATUS_EMOJI

def get_applicant_main_menu() -> ReplyKeyboardMarkup:
    """Get applicant main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Створити запит")],
            [KeyboardButton(text="📋 Мої запити")],
            [KeyboardButton(text="✅ Підтвердити запит")],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_applicant_nav_keyboard() -> ReplyKeyboardMarkup:
    """Bottom navigation for the confirm-requests list screen."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Головне меню")]],
        resize_keyboard=True,
    )


def get_applicant_detail_nav_keyboard() -> ReplyKeyboardMarkup:
    """Bottom navigation for the confirm-request detail screen."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True,
    )


def get_my_requests_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """InlineKeyboard listing all user requests with status emoji and title."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{STATUS_EMOJI.get(task.status.value, '⚪')} {task.title}",
            callback_data=f"view_request_{task.id}",
        )]
        for task in tasks
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_waiting_tasks_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """InlineKeyboard listing WAITING_APPLICANT tasks."""
    buttons = [
        [InlineKeyboardButton(
            text=f"🟠 {task.title}",
            callback_data=f"wait_view_{task.id}",
        )]
        for task in tasks
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_task_confirm_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """InlineKeyboard for task confirmation: confirm or reject."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm_yes"),
        InlineKeyboardButton(text="❌ Скасувати", callback_data="confirm_no"),
    ]])


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Get confirmation keyboard (Yes/No)."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Ні", callback_data="confirm_no"),
            ],
        ]
    )
    return keyboard


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Get task actions keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Переглянути деталі",
                    callback_data=f"task_details_{task_id}",
                ),
            ],
        ]
    )
    return keyboard
