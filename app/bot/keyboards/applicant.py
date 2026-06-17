"""Applicant keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def get_applicant_main_menu() -> ReplyKeyboardMarkup:
    """Get applicant main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Створити запит")],
            [KeyboardButton(text="📋 Мої запити")],
            [KeyboardButton(text="🔍 Статус запиту")],
        ],
        resize_keyboard=True,
    )
    return keyboard


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
