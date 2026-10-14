from datetime import datetime, timedelta, timezone

import pytest

from app.domain.task_states import (
    InvalidTransition, TaskStatus, TripEndBlocked,
    assignment_expired, check_transition, check_trip_can_end,
)


def test_happy_path_and_reassignment_loop():
    check_transition(TaskStatus.PENDING, TaskStatus.ASSIGNED)
    check_transition(TaskStatus.ASSIGNED, TaskStatus.REASSIGNMENT_NEEDED)
    check_transition(TaskStatus.REASSIGNMENT_NEEDED, TaskStatus.ASSIGNED)
    check_transition(TaskStatus.ASSIGNED, TaskStatus.ACCEPTED)
    check_transition(TaskStatus.ACCEPTED, TaskStatus.EN_ROUTE)
    check_transition(TaskStatus.EN_ROUTE, TaskStatus.DELIVERED)


@pytest.mark.parametrize("terminal", [TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.PARTIAL, TaskStatus.CANCELLED])
def test_terminal_states_are_final(terminal):
    with pytest.raises(InvalidTransition):
        check_transition(terminal, TaskStatus.DELIVERED if terminal != TaskStatus.DELIVERED else TaskStatus.FAILED)


def test_cannot_deliver_without_acceptance():
    with pytest.raises(InvalidTransition):
        check_transition(TaskStatus.ASSIGNED, TaskStatus.DELIVERED)


def test_five_minute_expiry():
    offered = datetime(2026, 10, 15, 6, 0, tzinfo=timezone.utc)
    assert not assignment_expired(offered, offered + timedelta(minutes=4, seconds=59), 5)
    assert assignment_expired(offered, offered + timedelta(minutes=5), 5)


def test_trip_end_rules():
    check_trip_can_end([TaskStatus.DELIVERED, TaskStatus.FAILED], allow_unattempted=False, reason=None)
    with pytest.raises(TripEndBlocked):
        check_trip_can_end([TaskStatus.DELIVERED, TaskStatus.ACCEPTED], allow_unattempted=False, reason="traffic")
    with pytest.raises(TripEndBlocked):
        check_trip_can_end([TaskStatus.ACCEPTED], allow_unattempted=True, reason="  ")
    check_trip_can_end([TaskStatus.ACCEPTED], allow_unattempted=True, reason="Vehicle breakdown")
