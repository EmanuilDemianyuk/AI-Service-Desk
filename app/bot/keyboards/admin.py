"""Admin keyboards."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.database.models import User


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Користувачі")],
            [KeyboardButton(text="➕ Створити користувача")],
            [KeyboardButton(text="📋 Всі завдання")],
        ],
        resize_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Single-button reply keyboard shown during multi-step forms."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True,
    )


def get_admin_nav_keyboard() -> ReplyKeyboardMarkup:
    """Navigation reply keyboard shown in admin sub-states (user list, detail, etc.).

    Replaces the main menu keyboard so all reply buttons remain functional
    while the user browses inline-keyboard-driven views.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Головне меню")]],
        resize_keyboard=True,
    )


def get_user_list_keyboard(users: list[User]) -> InlineKeyboardMarkup:
    """Inline list of users — each button opens the user detail view."""
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


def get_user_actions_keyboard(user_id: int, is_self: bool = False) -> InlineKeyboardMarkup:
    """Action buttons for a specific user (change role / delete / back)."""
    rows = [
        [InlineKeyboardButton(text="✏️ Змінити роль", callback_data=f"user_setrole_{user_id}")],
    ]
    if not is_self:
        rows.append(
            [InlineKeyboardButton(text="🗑 Видалити", callback_data=f"user_delete_{user_id}")]
        )
    rows.append([InlineKeyboardButton(text="↩ Назад", callback_data="user_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_role_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Role selection keyboard used when changing an existing user's role."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заявник", callback_data=f"setrole_{user_id}_APPLICANT")],
            [InlineKeyboardButton(text="🔧 Виконавець", callback_data=f"setrole_{user_id}_EXECUTOR")],
            [InlineKeyboardButton(text="👑 Адмін", callback_data=f"setrole_{user_id}_ADMIN")],
            [InlineKeyboardButton(text="↩ Назад", callback_data="user_back")],
        ]
    )


def get_delete_confirmation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for user deletion."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"confirm_delete_{user_id}")],
            [InlineKeyboardButton(text="❌ Скасувати", callback_data="user_back")],
        ]
    )


def get_create_role_keyboard() -> InlineKeyboardMarkup:
    """Role selection keyboard used during the create-user form."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Заявник", callback_data="create_role_APPLICANT")],
            [InlineKeyboardButton(text="🔧 Виконавець", callback_data="create_role_EXECUTOR")],
            [InlineKeyboardButton(text="👑 Адмін", callback_data="create_role_ADMIN")],
        ]
    )
