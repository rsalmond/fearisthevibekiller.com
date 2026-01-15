import re
from pathlib import Path
from typing import Dict

from paths import DATA_ROOT, DEFAULT_TEMPLATE


def load_template() -> str:
    """Load the event template from the repo data directory."""
    if DEFAULT_TEMPLATE.exists():
        return DEFAULT_TEMPLATE.read_text()
    raise FileNotFoundError(f"No template found at {DEFAULT_TEMPLATE}")


def render_template(template: str, event: Dict) -> str:
    """Render the template with event metadata."""
    def safe(value: str) -> str:
        return value if value else ""

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
    time_block = f"{start_time}-{end_time}".strip("-")

    ticket_link = event.get("ticket_or_info_link") or ""
    ticket_label = "Tickets" if event.get("ticket_link_type") == "tickets" else "Info"

    rendered = template
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
