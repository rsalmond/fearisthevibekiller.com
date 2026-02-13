#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
# ]
# ///

#!/usr/bin/env python3

import logging
import os
import re
import sys
import click

from pathlib import Path
from datetime import date
from typing import List
from dataclasses import dataclass

from logging_setup import configure_logging
from paths import DATA_ROOT

PAST_EVENTS = {}
FUTURE_EVENTS = {}
LOGGER = logging.getLogger(__name__)


class Event:
    """Wrap an event file on disk and expose parsed metadata."""
    path: Path

    def __init__(self, path: str):
        """Initialize the event wrapper with a file path."""
        self.path = Path(path)

    @property
    def date(self) -> date:
        """extract the DD-MM-YYYY portion of the filename and return it as a Date"""
        filename = self.path.name
        date_str = filename.split("-", 3)
        mm, dd, yyyy = map(int, date_str[:3])
        return date(yyyy, mm, dd)

    @property
    def name(self) -> str:
        """if file is 02-04-1980-robs-birthday.qmd then name is robs-birthday"""
        filename_without_date = self.path.name.split("-", 3)[-1]
        return filename_without_date.split(".")[0]

    @property
    def content(self) -> str:
        """Return the raw content of the event file."""
        with self.path.open(mode="r") as f:
            return f.read()

    def __lt__(self, other) -> int:
        """Sort events by name."""
        return self.name < other.name

    def __repr__(self) -> str:
        """Return a readable identifier for debug output."""
        return self.name


def iter_events():
    """walk over ever file in the _events directory that begins with DD-MM-YYYY"""
    events_path = DATA_ROOT / "_events"
    for file in events_path.iterdir():
        if file.is_file():
            if file.name.endswith(".qmd"):
                yield file


def load_events():
    """
    read every event file, categorize it as either past or future, then sort them alphabetically by event.name
    """

    today = date.today()

    for event_file in iter_events():
        event = Event(event_file)
        LOGGER.debug(f"Processing event: {event}")
        if event.date < today:
            if event.date not in PAST_EVENTS:
                PAST_EVENTS[event.date] = []

            PAST_EVENTS[event.date].append(event)
        else:
            if event.date not in FUTURE_EVENTS:
                FUTURE_EVENTS[event.date] = []

            FUTURE_EVENTS[event.date].append(event)

    for k, v in PAST_EVENTS.items():
        PAST_EVENTS[k].sort()

    for k, v in FUTURE_EVENTS.items():
        FUTURE_EVENTS[k].sort()


def render_events(target_date: date, event_list: List[Event]) -> str:
    """for a given calendar date, combine the contents of all the event files under an H2 heading for that date"""
    rendered = f"## {target_date.strftime('%A %B %-d, %Y')}\n\n"
    for event in event_list:
        rendered += f"{event.content}\n\n"

    return rendered


def read_tmpl(filename: str) -> str:
    """Read a template file from the _templates directory."""
    tmpl_path = os.path.join(os.getcwd(), "_templates", filename)
    with Path(tmpl_path).open(mode="r") as f:
        return f.read()


def get_footer(template: str) -> str:
    """Return the footer template for an events page."""
    return read_tmpl(f"{template}.footer.tmpl")


def get_header(template: str) -> str:
    """Return the header template for an events page."""
    return read_tmpl(f"{template}.header.tmpl")


@click.group()
def cli():
    """Render future or past event listings."""
    configure_logging()
    pass


@cli.command()
def future():
    """Render future events to stdout."""
    load_events()
    future_rendered = get_header("future_events")
    for k, v in sorted(FUTURE_EVENTS.items()):
        future_rendered += render_events(k, v)

    future_rendered += get_footer("future_events")

    total_events = sum(len(events) for events in FUTURE_EVENTS.values())
    LOGGER.info("Rendered %d future events across %d dates", total_events, len(FUTURE_EVENTS))
    click.echo(future_rendered)


@cli.command
def past():
    """Render past events to stdout."""
    load_events()
    past_rendered = get_header("past_events")
    for k, v in sorted(PAST_EVENTS.items(), reverse=True):
        past_rendered += render_events(k, v)

    past_rendered += get_footer("past_events")

    total_events = sum(len(events) for events in PAST_EVENTS.values())
    LOGGER.info("Rendered %d past events across %d dates", total_events, len(PAST_EVENTS))
    click.echo(past_rendered)


if __name__ == "__main__":
    cli()
