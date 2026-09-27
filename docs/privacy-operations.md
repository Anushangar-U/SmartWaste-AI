# Privacy and operating controls

Complaint text, optional public area and clarification answers may be sent to the configured
analysis/knowledge/decision providers. Avoid unnecessary names, personal addresses and
sensitive details. Tracking IDs are random capabilities: anyone holding one can see the
safe status/history, so do not publish them. Public responses omit original text, prompts,
provider errors, staff identities, review reasons and resolution notes.

Stored SQLite data contains private complaint and account data and is ignored by Git.
Limit filesystem access and back up before maintenance. The application is not claiming
legal compliance. Default RETENTION_DAYS=90 applies only to resolved cases, based on the
resolution timestamp. `python -m backend.maintenance` previews the count; `--apply` deletes
eligible resolved records and cascades their events/duplicate links. It does not delete
users or open cases. RETENTION_DAYS=0 disables this action. No deletion runs on startup.
Deletion does not erase independent backups; manage backup retention separately.

Public submission defaults to 30 requests/minute per direct client address; login/registration
share 20/minute. Expensive processing allows two concurrent pipelines per process. These
are configurable demo defaults. Rate state is memory-bounded and expires after a minute;
pipeline attempts and SDK retries are separately bounded. Bodies are capped at 16 KiB.
Controls are per application process, so deploy one worker for this demo. Multi-worker
deployment needs shared admission/rate control. Streamlit makes server-side requests, so
citizens may share its server IP; tune limits for that deployment. Forwarded IP headers are
not trusted without a separately secured proxy design. Public read endpoints remain safe
status views; this is not a demonstrated DoS-resistant internet service.

Application logs use route templates and one correlation ID across API and agent stages.
They do not deliberately log complaint text, tokens, credentials or tracking capabilities.
Use `uvicorn backend.main:app --no-access-log` to avoid separate server access logs recording
tracking URLs. Keep external SDK debug logging disabled. Use TLS and appropriate proxy
configuration before exposing beyond trusted localhost.
