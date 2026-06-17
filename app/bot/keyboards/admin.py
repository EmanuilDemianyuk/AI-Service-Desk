"""Admin keyboards."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.database.models import User


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Get admin main menu keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Користувачі")],
            [KeyboardButton(text="📋 Всі завдання")],
        ],
        resize_keyboard=True,
    )


def get_user_list_keyboard(users: list[User]) -> InlineKeyboardMarkup:
    """Inline list of users with their current role shown."""
    role_icon = {"APPLICANT": "👤", "EXECUTOR": "🔧", "ADMIN": "👑"}
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{role_icon.get(u.role.value, '')} {u.full_name}",
                callback_data=f"admin_user_{u.id}",
            )
        ]
        for u in users
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_role_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Role selection keyboard for a given user."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заявник", callback_data=f"setrole_{user_id}_APPLICANT")],
            [InlineKeyboardButton(text="🔧 Виконавець", callback_data=f"setrole_{user_id}_EXECUTOR")],
            [InlineKeyboardButton(text="👑 Адмін", callback_data=f"setrole_{user_id}_ADMIN")],
        ]
    )
