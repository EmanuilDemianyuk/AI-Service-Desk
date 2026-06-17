# Bot keyboards
from app.bot.keyboards.applicant import (
    get_applicant_main_menu,
    get_confirmation_keyboard,
    get_task_actions_keyboard,
)
from app.bot.keyboards.executor import (
    get_executor_main_menu,
    get_task_action_keyboard,
    get_complete_task_keyboard,
    get_task_list_keyboard,
)
from app.bot.keyboards.admin import (
    get_admin_main_menu,
    get_cancel_keyboard,
    get_user_list_keyboard,
    get_user_actions_keyboard,
    get_role_keyboard,
    get_delete_confirmation_keyboard,
    get_create_role_keyboard,
)

__all__ = [
    "get_applicant_main_menu",
    "get_confirmation_keyboard",
    "get_task_actions_keyboard",
    "get_executor_main_menu",
    "get_task_action_keyboard",
    "get_complete_task_keyboard",
    "get_task_list_keyboard",
    "get_admin_main_menu",
    "get_cancel_keyboard",
    "get_user_list_keyboard",
    "get_user_actions_keyboard",
    "get_role_keyboard",
    "get_delete_confirmation_keyboard",
    "get_create_role_keyboard",
]
