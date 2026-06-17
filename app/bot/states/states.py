"""FSM states for the bot."""

from aiogram.fsm.state import State, StatesGroup


class ApplicantStates(StatesGroup):
    """States for applicant users."""

    main_menu = State()
    create_request = State()
    request_description = State()
    my_requests = State()
    request_status = State()
    status_input = State()


class ExecutorStates(StatesGroup):
    """States for executor users."""

    main_menu = State()
    new_tasks = State()
    my_tasks = State()
    task_in_progress = State()
    complete_task = State()
    feedback_input = State()
    task_confirmation = State()


class AdminStates(StatesGroup):
    """States for admin users."""

    main_menu = State()
    # User list & per-user actions
    user_list = State()
    user_detail = State()
    set_role_select_role = State()
    confirm_delete_user = State()
    # Create user multi-step form
    create_user_first_name = State()
    create_user_last_name = State()
    create_user_telegram_id = State()
    create_user_role = State()
    # Task overview
    task_list = State()
