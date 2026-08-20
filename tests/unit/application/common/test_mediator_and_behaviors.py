from __future__ import annotations

import dataclasses
from datetime import timedelta
from typing import Any, ClassVar

import pytest

from app.application.common.behaviors.authorization import AuthorizationBehavior
from app.application.common.behaviors.idempotency import IdempotencyBehavior
from app.application.common.behaviors.validation import ValidationBehavior
from app.application.common.exceptions import (
    AuthenticationException,
    AuthorizationException,
    ValidationException,
)
from app.application.common.interfaces.idempotency import IdempotencyStore
from app.application.common.interfaces.identity import AuthContext
from app.application.common.mediator import HandlerNotRegistered, Mediator
from app.application.common.messages import Command, Request, RequestHandler
from app.application.common.request_context import RequestContext


@dataclasses.dataclass(frozen=True)
class _EchoCommand(Command[str]):
    value: str

    def validate(self) -> dict[str, list[str]]:
        return {} if self.value else {"value": ["must not be empty"]}


@dataclasses.dataclass(frozen=True)
class _RestrictedCommand(Command[str]):
    required_permission: ClassVar[str | None] = "widgets:write"
    value: str = "ok"


class _EchoHandler(RequestHandler[str]):
    def __init__(self) -> None:
        self.calls = 0

    async def handle(self, request: Request[str]) -> str:
        assert isinstance(request, _EchoCommand | _RestrictedCommand)
        self.calls += 1
        return request.value


class FakeIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self._results: dict[str, tuple[str, Any]] = {}
        self._locks: set[str] = set()

    async def get_cached_result(self, idempotency_key: str, fingerprint: str) -> Any | None:
        cached = self._results.get(idempotency_key)
        if cached is None or cached[0] != fingerprint:
            return None
        return cached[1]

    async def store_result(
        self, idempotency_key: str, fingerprint: str, result: Any, *, ttl: timedelta
    ) -> None:
        self._results[idempotency_key] = (fingerprint, result)

    async def try_acquire_lock(self, idempotency_key: str, *, ttl: timedelta) -> bool:
        if idempotency_key in self._locks:
            return False
        self._locks.add(idempotency_key)
        return True

    async def release_lock(self, idempotency_key: str) -> None:
        self._locks.discard(idempotency_key)


def _context(**overrides: Any) -> RequestContext:
    return RequestContext(**overrides)


class TestMediator:
    async def test_dispatches_to_the_registered_handler(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_EchoCommand: handler})

        result = await mediator.send(_EchoCommand(value="hi"), _context())

        assert result == "hi"
        assert handler.calls == 1

    async def test_raises_when_no_handler_is_registered(self) -> None:
        mediator = Mediator({})

        with pytest.raises(HandlerNotRegistered):
            await mediator.send(_EchoCommand(value="hi"), _context())

    async def test_behaviors_run_in_order_around_the_handler(self) -> None:
        trace: list[str] = []

        class _TraceBehavior:
            def __init__(self, name: str) -> None:
                self._name = name

            async def handle(self, request: Any, context: Any, call_next: Any) -> Any:
                trace.append(f"{self._name}.before")
                result = await call_next(request, context)
                trace.append(f"{self._name}.after")
                return result

        handler = _EchoHandler()
        mediator = Mediator(
            {_EchoCommand: handler}, behaviors=[_TraceBehavior("outer"), _TraceBehavior("inner")]
        )

        await mediator.send(_EchoCommand(value="hi"), _context())

        assert trace == ["outer.before", "inner.before", "inner.after", "outer.after"]


class TestValidationBehavior:
    async def test_raises_validation_exception_and_skips_the_handler(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_EchoCommand: handler}, behaviors=[ValidationBehavior()])

        with pytest.raises(ValidationException):
            await mediator.send(_EchoCommand(value=""), _context())

        assert handler.calls == 0


class TestAuthorizationBehavior:
    async def test_public_requests_skip_the_check(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_EchoCommand: handler}, behaviors=[AuthorizationBehavior()])

        result = await mediator.send(_EchoCommand(value="hi"), _context())

        assert result == "hi"

    async def test_unauthenticated_caller_is_rejected(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_RestrictedCommand: handler}, behaviors=[AuthorizationBehavior()])

        with pytest.raises(AuthenticationException):
            await mediator.send(_RestrictedCommand(), _context())

    async def test_authenticated_but_missing_permission_is_rejected(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_RestrictedCommand: handler}, behaviors=[AuthorizationBehavior()])
        auth = AuthContext(user_id=None, is_authenticated=True)

        with pytest.raises(AuthorizationException):
            await mediator.send(_RestrictedCommand(), _context(auth=auth))

    async def test_caller_with_the_required_permission_passes(self) -> None:
        handler = _EchoHandler()
        mediator = Mediator({_RestrictedCommand: handler}, behaviors=[AuthorizationBehavior()])
        auth = AuthContext(
            user_id=None, is_authenticated=True, permissions=frozenset({"widgets:write"})
        )

        result = await mediator.send(_RestrictedCommand(), _context(auth=auth))

        assert result == "ok"


class TestIdempotencyBehavior:
    async def test_without_a_key_the_handler_runs_every_time(self) -> None:
        handler = _EchoHandler()
        store = FakeIdempotencyStore()
        mediator = Mediator({_EchoCommand: handler}, behaviors=[IdempotencyBehavior(store)])

        await mediator.send(_EchoCommand(value="hi"), _context())
        await mediator.send(_EchoCommand(value="hi"), _context())

        assert handler.calls == 2

    async def test_a_replayed_key_short_circuits_the_handler(self) -> None:
        handler = _EchoHandler()
        store = FakeIdempotencyStore()
        mediator = Mediator({_EchoCommand: handler}, behaviors=[IdempotencyBehavior(store)])
        context = _context(idempotency_key="key-1")

        first = await mediator.send(_EchoCommand(value="hi"), context)
        second = await mediator.send(_EchoCommand(value="hi"), context)

        assert first == second == "hi"
        assert handler.calls == 1
