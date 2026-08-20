from __future__ import annotations

import dataclasses
import uuid

from app.domain.shared.aggregate_root import AggregateRoot
from app.domain.shared.domain_event import DomainEvent
from app.domain.shared.entity import Entity
from app.domain.shared.result import Result


class _DummyEntity(Entity[uuid.UUID]):
    pass


class _DummyAggregate(AggregateRoot[uuid.UUID]):
    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class _DummyEvent(DomainEvent):
    pass


class TestEntity:
    def test_equality_is_by_identity_and_type_not_by_attributes(self) -> None:
        shared_id = uuid.uuid4()
        assert _DummyEntity(shared_id) == _DummyEntity(shared_id)
        assert _DummyEntity(uuid.uuid4()) != _DummyEntity(uuid.uuid4())

    def test_hash_is_stable_for_use_in_sets(self) -> None:
        shared_id = uuid.uuid4()
        assert {_DummyEntity(shared_id), _DummyEntity(shared_id)} == {_DummyEntity(shared_id)}


class TestAggregateRoot:
    def test_register_event_then_collect_drains_the_buffer(self) -> None:
        aggregate_id = uuid.uuid4()
        aggregate = _DummyAggregate(aggregate_id)
        event = _DummyEvent(aggregate_id=aggregate_id)

        aggregate.register_event(event)
        assert aggregate.domain_events == (event,)

        collected = aggregate.collect_events()
        assert collected == [event]
        assert aggregate.domain_events == ()

    def test_clear_events_discards_without_returning(self) -> None:
        aggregate_id = uuid.uuid4()
        aggregate = _DummyAggregate(aggregate_id)
        aggregate.register_event(_DummyEvent(aggregate_id=aggregate_id))

        aggregate.clear_events()

        assert aggregate.domain_events == ()

    def test_mark_persisted_sets_the_version(self) -> None:
        aggregate = _DummyAggregate(uuid.uuid4())

        aggregate.mark_persisted(3)

        assert aggregate.version == 3


class TestResult:
    def test_ok_carries_a_value(self) -> None:
        result = Result[int, str].ok(42)
        assert result.is_success
        assert result.value == 42

    def test_fail_carries_an_error(self) -> None:
        result = Result[int, str].fail("boom")
        assert result.is_failure
        assert result.error == "boom"

    def test_accessing_value_on_a_failed_result_raises(self) -> None:
        result = Result[int, str].fail("boom")
        try:
            _ = result.value
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
