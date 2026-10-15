import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.task_states import InvalidTransition, TaskStatus, check_transition
from app.models.audit import AdminAlert, AuditLog
from app.models.delivery import DeliveryEvent, DeliveryTask
from app.models.ledger import CustomerLedgerEntry, LedgerEntryType
from app.services.errors import Conflict, ValidationFailed


def require_reason(reason: Optional[str], what: str = "This action") -> str:
    if not reason or not reason.strip():
        raise ValidationFailed(f"{what} requires a reason")
    return reason.strip()


def audit(db: AsyncSession, actor_id: Optional[uuid.UUID], action: str, entity_type: str, entity_id,
          reason: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> None:
    db.add(AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=str(entity_id),
                    reason=reason, data=data or {}))


def alert(db: AsyncSession, kind: str, message: str, task_id: Optional[uuid.UUID] = None) -> None:
    db.add(AdminAlert(kind=kind, message=message, task_id=task_id))


def move_task(db: AsyncSession, task: DeliveryTask, target: TaskStatus, actor_id: Optional[uuid.UUID],
              note: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> None:
    """The only way task status changes: validates the transition and records who did it and when."""
    try:
        check_transition(task.status, target)
    except InvalidTransition as exc:
        raise Conflict(str(exc)) from exc
    db.add(DeliveryEvent(task_id=task.id, actor_id=actor_id, from_status=task.status.value,
                         to_status=target.value, note=note, data=data or {}))
    task.status = target


async def post_ledger(db: AsyncSession, *, customer_id: uuid.UUID, entry_type: LedgerEntryType, amount: Decimal,
                      description: str, idempotency_key: str, created_by_id: Optional[uuid.UUID] = None,
                      **links) -> bool:
    """Posts one ledger entry. Returns False when an entry with this key already exists."""
    result = await db.execute(
        insert(CustomerLedgerEntry).values(
            id=uuid.uuid4(), customer_id=customer_id, entry_type=entry_type, amount=amount,
            description=description, idempotency_key=idempotency_key, created_by_id=created_by_id, **links,
        ).on_conflict_do_nothing(index_elements=[CustomerLedgerEntry.idempotency_key]).returning(CustomerLedgerEntry.id)
    )
    return result.scalar_one_or_none() is not None


async def lock(db: AsyncSession, model, entity_id, label: str):
    from app.services.errors import NotFound
    obj = (await db.execute(select(model).where(model.id == entity_id).with_for_update())).scalars().first()
    if obj is None:
        raise NotFound(f"{label} not found")
    return obj
