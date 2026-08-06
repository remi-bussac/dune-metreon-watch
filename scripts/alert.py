"""Gmail SMTP alerting. Three distinct email shapes so the user can never
mistake one for another at a glance: a ticket alert (act now), a leading-
indicator mention (heads up), a broken-monitor alert (fix me), and a weekly
heartbeat (silence would otherwise be ambiguous).

Credentials come from environment variables (repo secrets in CI, a local
.env-style export for manual testing) — never hardcoded, never logged.
"""

from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText

from normalize import SourceResult


def _send(subject: str, body: str) -> None:
    gmail_address = os.environ["GMAIL_ADDRESS"].strip()
    # Google displays app passwords as four space-separated groups ("abcd efgh
    # ijkl mnop"). Pasting that verbatim is the obvious thing to do and gets a
    # completely unhelpful "535 Username and Password not accepted" from SMTP,
    # which reads like a wrong password rather than a formatting problem.
    # Strip all whitespace so either form works.
    app_password = "".join(os.environ["GMAIL_APP_PASSWORD"].split())
    to_addr = os.environ["ALERT_EMAIL_TO"].strip()

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_addr

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, app_password)
        server.sendmail(gmail_address, [to_addr], msg.as_string())


def send_ticket_alert(target: dict, result: SourceResult) -> None:
    subject = f"🎟️ TICKETS: {target['film_name']} 70mm at {target['venue']} — {result.source}"
    lines = [
        f"New {target['format']} showtime(s) detected for {target['film_name']} "
        f"at {target['venue']}, via {result.source}.",
        "",
        "GO NOW — this can sell out in minutes:",
        result.showtimes[0].booking_url if result.showtimes else "(no URL captured)",
        "",
        "Showtimes found:",
    ]
    for st in result.showtimes:
        lines.append(f"  - {st.date} {st.time} · {st.format} · {st.venue}")
    lines += ["", f"Detected at {result.checked_at}."]
    _send(subject, "\n".join(lines))


def send_mention_alert(target: dict, result: SourceResult) -> None:
    subject = f"👀 Leading indicator: {target['film_name']} mentioned near '70mm'/'tickets'"
    lines = [
        f"A Reddit post matching {target['film_name']} + 70mm/tickets keywords was found.",
        "This is NOT confirmation tickets are on sale — it's a heads-up to watch closely.",
        "",
    ]
    for st in result.showtimes:
        lines.append(f"  - {st.venue}: {st.format}")
        lines.append(f"    {st.booking_url}")
    lines += ["", f"Detected at {result.checked_at}."]
    _send(subject, "\n".join(lines))


def send_broken_alert(source_name: str, target_id: str, consecutive_failures: int, error: str | None) -> None:
    subject = f"⚠️ MONITOR BROKEN: {source_name} ({target_id})"
    body = (
        f"{source_name} has failed to parse the page structure {consecutive_failures} runs in a row "
        f"for target '{target_id}'.\n\n"
        f"Last error: {error}\n\n"
        "This likely means the site changed its layout and the extraction logic needs updating. "
        "This is a DISTINCT alert from a ticket alert — it does NOT mean tickets are on sale, "
        "it means this one source can no longer confirm either way. The other independent sources "
        "are still running."
    )
    _send(subject, body)


def send_blocked_alert(
    source_name: str, target_id: str, error: str | None, consecutive: int = 1
) -> None:
    subject = f"🚫 BLOCKED: {source_name} ({target_id}) — {consecutive} runs in a row"
    body = (
        f"{source_name} has been blocked for {consecutive} consecutive runs while checking "
        f"target '{target_id}' (HTTP 403/429 or a waiting-room interstitial).\n\n"
        f"Detail: {error}\n\n"
        "Nothing has been lost: known showtimes are stored as a union, so a blocked run "
        "contributes nothing rather than erasing anything. This is only worth acting on "
        "if it persists.\n\n"
        "This could mean: (a) this source is now blocking the monitor's requests, or "
        "(b) a real traffic spike is happening right now — possibly the drop itself. "
        "Worth checking the site manually either way."
    )
    _send(subject, body)


def send_heartbeat(status_summary: str) -> None:
    subject = "✅ Monitor heartbeat — alive, nothing missed"
    body = f"Weekly heartbeat. Nothing to act on unless noted below.\n\n{status_summary}"
    _send(subject, body)
