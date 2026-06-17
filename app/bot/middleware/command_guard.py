"""Middleware that guards BotCommand execution during active multi-step flows."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.states import FLOW_STATES

# Commands that are explicitly meant to stop the current flow — never intercepted.
_BYPASS_COMMANDS: frozenset[str] = frozenset({"/cancel"})


class CommandGuardMiddleware(BaseMiddleware):
    """Intercepts slash commands while the user is in an active multi-step flow.

    Saves the pending command to FSM data under ``_pending_command`` and shows
    a confirmation inline keyboard. The ``guard_confirm`` / ``guard_cancel``
    callbacks in ``common.py`` handle the user's response.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        text = event.text.strip()
        if not text.startswith("/"):
            return await handler(event, data)

        command = text.split()[0].lower()
        if command in _BYPASS_COMMANDS:
            return await handler(event, data)

        state: FSMContext | None = data.get("state")
        if state is None:
            return await handler(event, data)

        current_state = await state.get_state()
        if current_state not in FLOW_STATES:
            return await handler(event, data)

        # User is inside an active flow — ask for confirmation before switching.
        await state.update_data(_pending_command=command)
        await event.answer(
            "⚠️ У вас є незавершена дія. "
            "Якщо перейти до іншої команди, поточний прогрес буде втрачено. Продовжити?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Так", callback_data="guard_confirm"),
                        InlineKeyboardButton(text="❌ Ні", callback_data="guard_cancel"),
                    ]
                ]
            ),
        )
        # Do not call handler — stop propagation.
