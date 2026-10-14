# Phase 1 Report: Domain Model and Calculations

Date: 14 Oct 2026. Branch: `claude/phase0-audit-tdirql` (PR #1).

## Summary

Phase 1 adds the backend data model and business rules for the v2.0 spec: settings with effective dates, the service calendar, plan rate versions, subscriptions with meal slots, skips with cutoff-based credits, one-time requests and orders, delivery tasks with individual driver assignment and 5-minute expiry, trips with route legs, customer delivery fees, driver earnings with review and finalization, a customer ledger with payments, admin alerts and an audit log.

Phase 1 has no new HTTP endpoints. The spec puts the admin screens and their APIs in Phase 2, the driver app in Phase 3 and the customer app in Phase 4. The existing admin web and `/orders` endpoints are unchanged.

## Where things live

| Area | Pure rules (`app/domain/`) | Database service (`app/services/`) |
|---|---|---|
| Money and rounding | `money.py`: one rounding rule (2 dp, half up); `TOTAL` or `PER_SLOT` policy | |
| Calendar | `service_calendar.py` | `settings_service.py`: holidays and opened days |
| Settings | | `settings_service.py` + `app/schemas/settings.py` (versioned by effective date) |
| Proration and skip credit | `proration.py`, `meal_windows.py` (per-window cutoffs, IST) | `subscription_service.py` |
| One-time requests | | `one_time_order_service.py` |
| Tasks and assignment | `task_states.py` (state machine, expiry, End Trip rule) | `task_service.py`, `jobs.py` (expiry every 30 s) |
| Trips, route legs, customer fees | `delivery_fees.py` | `trip_service.py`, `route_distance.py` (Google Directions, server-side key) |
| Driver earnings | `payouts.py` | `earnings_service.py` |
| Ledger and payments | | `payment_service.py` |

## Migration

`backend/alembic/versions/0002_phase1_domain.py` adds 17 tables plus `users.driver_code`: `settings_versions`, `service_date_exceptions`, `plan_rate_versions`, `subscriptions`, `subscription_meal_slots`, `one_time_orders`, `one_time_order_lines`, `delivery_tasks`, `driver_assignments`, `delivery_events`, `delivery_trips`, `route_legs`, `driver_day_summaries`, `driver_earning_lines`, `customer_ledger_entries`, `payments`, `payment_allocations`, `admin_alerts`, `audit_logs`. Upgrade, downgrade and re-upgrade were run; `alembic check` reports no drift.

Duplicate protection lives in the database:

- one active subscription per customer and month;
- one live task per subscription slot or order line (a cancelled task keeps its history, and a restored slot gets a new task);
- one open offer per task;
- one trip per driver, date and meal window;
- one earnings summary per driver and date;
- unique idempotency keys on every ledger entry and payment.

## Rules as implemented

- **Per-meal value** = plan amount ÷ the slots generated for that month. January 2030 has 27 service days, so ₹5,500 / 81 = ₹67.90 per meal. With a holiday it has 26 days, giving ₹70.51.
- **Skip credit** is recalculated from the total number of on-time skips each time, and only the difference is posted. Skipping every meal one at a time credits exactly the plan amount. Restoring reverses the credit. Late skips earn nothing; admins can add an itemized manual credit.
- **Skips** cancel tasks that have not started, with an event record. A task a driver has already accepted or completed blocks the skip, so it has to go through the delivery exception path.
- **Assignment**: one task is offered to one driver. Decline needs a reason and raises an admin alert. An offer with no answer within 5 minutes expires and goes back to the admin with an alert. The task is never deleted.
- **Delivery**: Delivered takes an optional note, Failed needs a reason, and Partial needs both the delivered and the missing items. Repeating the same outcome changes nothing. Failed and partial deliveries raise alerts.
- **Customer delivery fee** = the route leg into that customer's stop (from the kitchen for the first stop) × rate. Failed stops and skipped meals are not charged, and the return leg is never charged to a customer. Distance corrections post only the difference.
- **Driver earnings** = km × rate + successful drops × per-drop amount + fixed allowance + adjustments. The return leg counts only if the setting includes it. Finalizing a day stores a snapshot of the policy, so later rate changes do not rewrite it. After finalization the only change allowed is an itemized adjustment with a reason.
- **Payments**: cash, UPI, bank transfer or other, recorded with an idempotency key. Allocation to a subscription or order is optional and manual. Balance = sum of ledger entries; a negative balance is an advance.

## Open decisions: defaults used until the owner decides

| # | Decision | Default in code | Where to change |
|---|---|---|---|
| 1 | Customer ₹/km and minimum fee | ₹0 and ₹0, so nothing is charged | `delivery_fees` settings |
| 2 | Return leg charged to customers | Never charged | Code (not a setting) |
| 3 | Rounding | `TOTAL` (round final amounts only) | `billing.rounding_policy` |
| 4 | Fixed allowance period | `PER_DAY`, amount ₹0 | `payout.fixed_allowance_period` |
| 5 | What counts as a drop | One per delivered task | `payout.drop_unit` (`PER_STOP` available) |
| 6 | Maps unavailable | Trip ends; distance marked "needs manual entry"; admin enters an audited distance; the day cannot be finalized until then | Code |
| 7 | Credit use and expiry | Credits sit on the ledger and reduce the balance; no expiry; no automatic invoice application | Phase 2 invoices |
| 8 | GST invoice fields | Not built | Phase 2 |
| 9 | OTP provider | Not built | Phase 4 |
| 10 | Maps credentials | `GOOGLE_MAPS_API_KEY` plus the kitchen location setting; without them distances need manual entry | `.env`, `kitchen` settings |
| 11 | End Trip with unattempted tasks | Blocked; an optional setting allows it with a reason | `operations.allow_end_trip_with_unattempted` |
| 12 | Opening a Sunday or holiday | Disabled | `calendar.allow_open_overrides` |
| 13 | Payment allocation | Manual only | Code |

## Tests

```bash
cd backend && pytest -q        # 43 passed
```

- 26 pure unit tests (`tests/unit/`) cover the calendar, proration and rounding drift, cutoffs in IST, delivery fees, payouts and the task state machine.
- 7 integration tests run on PostgreSQL (`tests/test_phase1_domain_services.py`). They cover activation, skip/restore credits, shared inbox, no duplicate tasks, accept/decline/expiry, trip fees and earnings with finalization, the Maps-failure manual path, and payments.
- The 10 earlier API and authorization tests still pass.

## Remaining gaps and risks

- The existing `orders` table and admin screens still run the old daily-order flow. Phase 2 moves the screens to subscriptions and delivery tasks; the old `/orders` endpoints can then be retired.
- Plan price edits through the existing `PUT /meal-plans` do not yet create rate versions. Activation snapshots the current price into a version. Phase 2 will route price edits through versions.
- No invoices or receipts yet; this waits on decision #8.
- The expiry job runs inside the API process. With more than one API process, move it to a single scheduler; the query already uses `SKIP LOCKED`, so running it twice is safe.
- The Google Directions provider is untested against the live API because no key is configured. It is covered through a fake provider.

## Manual QA (after Phase 2 screens exist)

1. Set rates and the kitchen location in settings, effective tomorrow.
2. Activate a subscription and check the service dates and meal count.
3. Skip a meal before and after its cutoff; check the credit on the ledger and the audit history.
4. Generate tasks, assign one, and let 5 minutes pass; check the alert.
5. Run a trip end to end; check the route legs, customer fee and driver summary; finalize; then add an adjustment.
