import asyncio
import logging

from app.core.database import SessionLocal
from app.core.time import utcnow
from app.services.task_service import expire_overdue_assignments

logger = logging.getLogger(__name__)

EXPIRY_CHECK_SECONDS = 30


async def run_assignment_expiry_once() -> int:
    async with SessionLocal() as db:
        expired = await expire_overdue_assignments(db, utcnow())
        await db.commit()
    if expired:
        logger.info("Expired %d unanswered driver assignment(s)", expired)
    return expired


async def assignment_expiry_loop() -> None:
    """Returns unanswered task offers to the admin once their 5-minute window passes."""
    while True:
        try:
            await run_assignment_expiry_once()
        except Exception:  # keep the loop alive; the next tick retries
            logger.exception("Assignment expiry job failed")
        await asyncio.sleep(EXPIRY_CHECK_SECONDS)
