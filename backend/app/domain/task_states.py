from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, FrozenSet, Iterable


class TaskStatus(str, Enum):
    PENDING = "PENDING"                          # generated, not yet assigned
    ASSIGNED = "ASSIGNED"                        # offered to a driver, awaiting response
    REASSIGNMENT_NEEDED = "REASSIGNMENT_NEEDED"  # declined or timed out; back with admin
    ACCEPTED = "ACCEPTED"
    EN_ROUTE = "EN_ROUTE"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"                      # e.g. meal skipped before the task started


TERMINAL: FrozenSet[TaskStatus] = frozenset({
    TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.PARTIAL, TaskStatus.CANCELLED,
})

# Tasks in these states have not been started by a driver and may be cancelled by a skip.
UNSTARTED: FrozenSet[TaskStatus] = frozenset({
    TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.REASSIGNMENT_NEEDED,
})

ALLOWED: Dict[TaskStatus, FrozenSet[TaskStatus]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.ASSIGNED, TaskStatus.CANCELLED}),
    TaskStatus.ASSIGNED: frozenset({TaskStatus.ACCEPTED, TaskStatus.REASSIGNMENT_NEEDED, TaskStatus.CANCELLED}),
    TaskStatus.REASSIGNMENT_NEEDED: frozenset({TaskStatus.ASSIGNED, TaskStatus.CANCELLED}),
    TaskStatus.ACCEPTED: frozenset({
        TaskStatus.EN_ROUTE, TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.PARTIAL,
        TaskStatus.REASSIGNMENT_NEEDED,  # admin pulls the task back before delivery
        TaskStatus.CANCELLED,            # explicit admin exception path only
    }),
    TaskStatus.EN_ROUTE: frozenset({TaskStatus.DELIVERED, TaskStatus.FAILED, TaskStatus.PARTIAL}),
}


class InvalidTransition(Exception):
    def __init__(self, current: TaskStatus, target: TaskStatus):
        super().__init__(f"Cannot move a task from {current.value} to {target.value}")
        self.current = current
        self.target = target


def check_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in ALLOWED.get(current, frozenset()):
        raise InvalidTransition(current, target)


def assignment_expired(offered_at: datetime, now: datetime, timeout_minutes: int) -> bool:
    return now >= offered_at + timedelta(minutes=timeout_minutes)


class TripEndBlocked(Exception):
    pass


def check_trip_can_end(statuses: Iterable[TaskStatus], allow_unattempted: bool, reason: str | None) -> None:
    """
    By default every task on the trip must be delivered or explicitly exceptioned (failed/partial)
    before End Trip. With allow_unattempted, accepted-but-unattempted tasks are allowed if a reason is given.
    """
    open_tasks = [s for s in statuses if s not in TERMINAL]
    if not open_tasks:
        return
    if allow_unattempted and reason and reason.strip():
        return
    raise TripEndBlocked(
        f"{len(open_tasks)} task(s) are not delivered or recorded as failed/partial"
        + ("; a reason is required to end the trip" if allow_unattempted else "")
    )
