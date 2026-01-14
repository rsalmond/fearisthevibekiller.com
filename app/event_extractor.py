import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests


LOGGER = logging.getLogger(__name__)


@dataclass
class EventExtractionResult:
    """Return extracted data and the raw model response."""
    data: Optional[Dict]
    error: Optional[str]
    raw_response: Optional[Dict]


def _load_images(image_paths: List[Path], max_images: int = 3) -> List[Dict]:
    """Prepare base64-encoded images for the OpenAI payload."""
    payloads = []
    for path in image_paths[:max_images]:
        try:
            raw = path.read_bytes()
        except Exception:
            continue
        encoded = base64.b64encode(raw).decode("utf-8")
        mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        payloads.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"},
            }
        )
    return payloads


def _extract_json(text: str) -> Optional[Dict]:
    """Parse JSON from a response that may contain extra text."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def extract_event_metadata_from_post(
    api_key: str,
    model: str,
    caption: str,
    post_url: str,
    image_paths: List[Path],
    post_date: Optional[str] = None,
    post_author: Optional[str] = None,
) -> EventExtractionResult:
    """Extract event metadata from a post using the OpenAI API."""
    start_time = time.monotonic()
    LOGGER.debug("OpenAI extraction start for %s", post_url)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    system_prompt = (
        "You extract event details from Instagram posts. Return strict JSON only."
    )
    user_prompt = (
        "Extract event info. If a field is missing, return null. "
        "Include every DJ name mentioned in the caption or visible in the images. "
        "Use the post date as context when inferring the event date. "
        "If the caption indicates the location is only available by DM/PM, "
        "set location_name to 'DM @<post_author> for location' using the provided post author, "
        "and leave location_address blank. "
        "Use the instagram post URL as the fallback info link if no official link is present. "
        "ticket_link_type must be 'tickets' when the link is for tickets, or 'info' otherwise. "
        "Return confidence as a number between 0 and 1, where higher means more certain."
    )

    schema = {
        "event_name": "string",
        "date": "YYYY-MM-DD",
        "start_time": "HH:MM",
        "end_time": "HH:MM",
        "location_name": "string",
        "location_address": "string",
        "google_maps_link": "string",
        "djs": [{"name": "string", "link": "string"}],
        "ticket_or_info_link": "string",
        "ticket_link_type": "tickets|info",
        "confidence": "number (0-1)",
    }

    content = [
        {"type": "text", "text": user_prompt},
        {"type": "text", "text": f"POST URL: {post_url}"},
        {"type": "text", "text": f"POST DATE: {post_date or ''}"},
        {"type": "text", "text": f"POST AUTHOR: {post_author or ''}"},
        {"type": "text", "text": f"CAPTION: {caption or ''}"},
        {"type": "text", "text": f"OUTPUT JSON SCHEMA: {json.dumps(schema)}"},
    ]
    content.extend(_load_images(image_paths))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "temperature": 0.2,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    elapsed = time.monotonic() - start_time
    LOGGER.debug("OpenAI extraction finished for %s in %.2fs", post_url, elapsed)
    if response.status_code != 200:
        return EventExtractionResult(
            data=None,
            error=f"OpenAI API error {response.status_code}: {response.text}",
            raw_response=response.json() if response.content else None,
        )

    data = response.json()
    message = data["choices"][0]["message"]["content"]
    extracted = _extract_json(message)
    if not extracted:
        return EventExtractionResult(
            data=None,
            error="Unable to parse JSON from response",
            raw_response=data,
        )

    return EventExtractionResult(data=extracted, error=None, raw_response=data)
