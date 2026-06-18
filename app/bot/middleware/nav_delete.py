"""Middleware that silently deletes ReplyKeyboard navigation messages.

Navigation button presses (e.g. «🏠 Головне меню», «⬅️ Назад») clutter the chat.
This middleware deletes them so only bot messages remain visible.

Messages in FLOW_STATES are user input (descriptions, feedback, form fields) —
they are never deleted.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states import FLOW_STATES


class NavDeleteMiddleware(BaseMiddleware):
    """Deletes ReplyKeyboard navigation messages to keep the chat clean."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        # Slash commands are handled by CommandGuardMiddleware — skip.
        if event.text.strip().startswith("/"):
            return await handler(event, data)

        state: FSMContext | None = data.get("state")
        if state is not None:
            current_state = await state.get_state()
            if current_state in FLOW_STATES:
                # User is typing real input — preserve the message.
                return await handler(event, data)

        try:
            await event.delete()
        except Exception:
            pass  # No permission or message too old — silently ignore.

        return await handler(event, data)
