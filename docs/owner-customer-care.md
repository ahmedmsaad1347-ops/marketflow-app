# Owner customer care and follow-up

The owner console now links account management to useful customer service context: actual recorded sign-ins and workspace activity, recent saved work, private service notes, and an internal follow-up queue. The records help the owner remember questions, set priorities and follow through. They do not send email, WhatsApp, social messages or any other outside-platform communication.

## Customer profile

An owner can open a customer profile from Users to review:

- The last recorded successful sign-in and last observed authenticated workspace activity. New tracking begins with this update; activity writes are throttled to at most once every five minutes. Neither field means that the customer is currently online.
- The latest saved-work update, plus up to20 recent campaigns, creative projects, strategies and strategy conversations. This is a feed of current saved-record metadata and update timestamps, not a reconstruction of every historical interaction. Strategy titles can be synthetic record labels because the feed does not load private brief/result JSON just to build a list.
- The latest20 private service notes, their author/time and the total note count.
- The latest20 follow-ups and the customer's open/overdue totals. The full paginated task list is available in Customer care.

For accounts without a newly recorded sign-in, the backend can use the creation time of the latest retained session as a limited fallback and returns `last_sign_in_evidence_source`. Retained-session fallback data may disappear when sessions are revoked or cleaned up; persistent sign-in tracking is not inferred from it. `last_seen_at` is the separate recorded workspace-request timestamp. No page visits or legacy login history are invented.

## Internal notes and follow-ups

A service note is nonblank plain text, at most2000 characters. A follow-up requires a nonblank subject of at most160 characters and useful nonblank details of at most3000 characters. Its priority is Normal or High, with an optional due date. Notes and descriptions remain private to owner administration; the UI escapes them as text. They are service records, not customer chat messages.

New follow-ups start as `new`. The owner can change them to `in_progress`, `waiting_customer` or `resolved`, change priority, and set or remove the due date. Dates use a valid calendar `YYYY-MM-DD` value; past dates are allowed to represent an overdue task. Open means any status except Resolved. A task is overdue when it is open and its due date is before the current UTC date; a task due today is not yet overdue.

Resolving records a resolution timestamp. Updating an already resolved task retains that timestamp; reopening clears it and makes any past-due date actionable again. Updates do not reassign a task to another customer or rewrite its subject/description. There is no deletion or bulk-contact action in this release.

The queue can filter All/Open or an individual status and Normal/High priority, with20 tasks per page. Its Open/Overdue summary covers the whole service queue, independently of the current list filter. Open tasks sort before resolved tasks, and high-priority tasks before normal ones; updates then sort newest first. Overdue status is calculated from saved due dates, not claimed from a prediction.

## Access, data and audit

All routes are under `/api/owner/` and require the current server-side owner role. The existing owner response no-store handling and global CSRF/origin checks apply. A member cannot read notes, the follow-up queue or another account's care context by changing a URL. Ordinary customer workspace ownership rules remain unchanged.

Notes and follow-ups do not change account privileges or customer access, so they use owner authentication and CSRF without another password challenge. Suspension, session revocation and other sensitive administration retain their separate current-password-and-reason confirmation.

Schema initialization adds `owner_customer_notes` and `owner_support_tickets` with indexes and bounded fields. It is idempotent and preserves existing users, campaigns and stored work. Explicit allowlisted response fields include task/account identifiers and customer identity for the owner; they do not include password hashes/salts, session tokens, authentication links or provider secrets. Activity queries are scoped to the selected user and do not load every JSON brief or result.

Writes and their audit records use the same database transaction. Audit actions are `owner.customer_note_added`, `owner.support_ticket_created` and `owner.support_ticket_updated`; their metadata includes IDs, status, priority and date, not note text, task subject or description. A direct care-profile request records `owner.customer_care_view`; the combined owner user-detail view retains its normal audited account-review action. The snapshot helper itself is read-only and leaves audit responsibility to its authenticated caller.

## Integration and limits

`init_customer_care_schema(db)` adds the CRM tables. `register_customer_care(app, get_db, auth, require_owner)` registers the protected routes. `customer_care_snapshot(db, uid)` provides the shared read model for an already-authorized owner endpoint. Authentication/schema tracking lives in the owner/auth integration; the care module does not promote accounts, request passwords or import/start the application.

Endpoints:

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/owner/customers/{uid}/care` | Customer service context and recent internal records. |
| GET | `/api/owner/support` | Filtered, paginated internal follow-up queue and totals. |
| POST | `/api/owner/customers/{uid}/notes` | Save a private service note. |
| POST | `/api/owner/customers/{uid}/tickets` | Create a follow-up for that customer. |
| PATCH | `/api/owner/support/{tid}` | Update status, priority and optional due date. |

This is local customer care tooling, with no paid model key, billing calculation, ticket-to-customer delivery, read receipts, availability prediction or automatic account changes. All customers must continue to authenticate through the normal workflow. Historical work timestamps and newly recorded requests provide evidence; they are not a complete customer analytics timeline.

## Verification

The combined release passes147 unit/API checks, including11 focused customer-care cases and17 owner security cases. Production build and the full real-backend owner/CRM browser journey pass, with no browser errors across both themes and320/390/768/1440 widths. Tests verify private note escaping/persistence/draft retention, real activity, customer access denial, ticket filtering/date/priority/resolution and counts, and audit metadata that omits private note/task content. All fixtures were disposable; no actual account was promoted.
