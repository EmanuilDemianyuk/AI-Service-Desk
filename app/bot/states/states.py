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


# States that belong to active multi-step flows (user is inputting data).
# The CommandGuardMiddleware checks this set before allowing a command switch.
# Add new flow states here when implementing new multi-step scenarios.
FLOW_STATES: frozenset[str] = frozenset({
    ApplicantStates.request_description.state,
    ApplicantStates.status_input.state,
    ExecutorStates.complete_task.state,
    ExecutorStates.feedback_input.state,
    AdminStates.create_user_first_name.state,
    AdminStates.create_user_last_name.state,
    AdminStates.create_user_telegram_id.state,
    AdminStates.create_user_role.state,
})
