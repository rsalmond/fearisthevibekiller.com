import re
from pathlib import Path
from typing import Dict

from paths import DATA_ROOT, DEFAULT_TEMPLATE


def load_template() -> str:
    """Load the event template from the repo data directory."""
    if DEFAULT_TEMPLATE.exists():
        return DEFAULT_TEMPLATE.read_text()
    raise FileNotFoundError(f"No template found at {DEFAULT_TEMPLATE}")


TIME_PATTERN = re.compile(r"(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>am|pm)?")


def normalize_time_value(value: str, default_meridiem: str = "pm") -> str:
    """Normalize time strings to a compact 12-hour format."""
    if not value:
        return ""
    lowered = value.strip().lower()
    match = TIME_PATTERN.search(lowered)
    if not match:
        return lowered
    hour = int(match.group("hour"))
    minute = match.group("minute")
    meridiem = match.group("meridiem")
    if meridiem is None:
        if hour >= 24:
            hour = hour % 24
        if hour >= 13:
            meridiem = "pm"
        elif hour == 0:
            meridiem = "am"
            hour = 12
        elif hour == 12:
            meridiem = "pm"
        else:
            meridiem = default_meridiem
    if meridiem == "pm" and hour > 12:
        hour -= 12
    if meridiem == "am" and hour == 0:
        hour = 12
    if minute:
        return f"{hour}:{minute}{meridiem}"
    return f"{hour}{meridiem}"


def format_time_block(start_time: str, end_time: str) -> str:
    """Format a time range, handling late-night phrasing."""
    if not start_time and not end_time:
        return ""
    start_raw = (start_time or "").strip()
    end_raw = (end_time or "").strip()
    start_lower = start_raw.lower()
    end_lower = end_raw.lower()
    late_in_start = "late" in start_lower and any(token in start_lower for token in ["till", "til", "until"])
    late_in_end = "late" in end_lower

    start_display = normalize_time_value(start_raw)
    if late_in_start:
        return f"{start_display}-late".strip("-")
    if late_in_end:
        return f"{start_display}-late".strip("-")

    end_display = normalize_time_value(end_raw)
    return f"{start_display}-{end_display}".strip("-")


def render_template(template: str, event: Dict) -> str:
    """Render the template with event metadata."""
    def safe(value: str) -> str:
        """Return a non-empty string or empty placeholder."""
        return value if value else ""

    def meta_value(value: str) -> str:
        """Sanitize metadata values for HTML comments."""
        cleaned = (value or "").replace("\n", " ").replace("\r", " ")
        cleaned = cleaned.replace(";", ",").replace("-->", "--")
        return cleaned.strip()

    dj_lines = []
    seen_names = set()
    for dj in event.get("djs") or []:
        name = dj.get("name") or ""
        link = dj.get("link") or ""
        normalized = name.strip().lower()
        if not normalized or normalized in seen_names:
            continue
        seen_names.add(normalized)
        if name and link:
            dj_lines.append(f"* [{name}]({link})")
        elif name:
            dj_lines.append(f"* {name}")

    dj_block = "\n".join(dj_lines) if dj_lines else "*"

    start_time = event.get("start_time") or ""
    end_time = event.get("end_time") or ""
    time_block = format_time_block(start_time, end_time)

    ticket_link = event.get("ticket_or_info_link") or ""
    ticket_label = "Tickets" if event.get("ticket_link_type") == "tickets" else "Info"

    post_url = meta_value(event.get("post_url") or "")
    event_name = meta_value(event.get("event_name") or "")
    event_date = meta_value(event.get("date") or "")
    meta_comment = (
        "<!-- event-meta: "
        f"post_url={post_url}; "
        f"ticket_link={meta_value(ticket_link)}; "
        f"event_date={event_date}; "
        f"event_name={event_name} -->\n"
    )

    rendered = meta_comment + template
    rendered = rendered.replace("<EVENT NAME>", safe(event.get("event_name")))
    rendered = rendered.replace("STARTTIME-ENDTIME", time_block)
    rendered = rendered.replace("* [DJ Name](DJ Link)", dj_block)
    rendered = re.sub(r"^[ \\t]*\\* \\[DJ Name\\].*$", dj_block, rendered, flags=re.MULTILINE)
    rendered = rendered.replace("[Tickets or Info](URL)", f"[{ticket_label}]({ticket_link})")
    rendered = rendered.replace("[Tickets|Info](URL)", f"[{ticket_label}]({ticket_link})")
    return rendered


def event_filename(event: Dict) -> str:
    """Build a filename for the rendered event template."""
    date = event.get("date") or ""
    event_name = (event.get("event_name") or "").strip().lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in event_name)
    slug = "-".join(filter(None, slug.split("-")))
    if date:
        parts = date.split("-")
        if len(parts) == 3:
            date = f"{parts[1]}-{parts[2]}-{parts[0]}"
    return f"{date}-{slug}.qmd".strip("-")
