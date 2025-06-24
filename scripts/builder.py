#!/usr/bin/env python3

import os
import re
import sys
import click

from pathlib import Path
from datetime import date
from typing import List
from dataclasses import dataclass

PAST_EVENTS = {}
FUTURE_EVENTS = {}


class Event:
    path: Path

    def __init__(self, path: str):
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
        with self.path.open(mode="r") as f:
            return f.read()

    def __lt__(self, other) -> int:
        return self.name < other.name

    def __repr__(self) -> str:
        return self.name


def iter_events():
    """walk over ever file in the ./events directory that begins with DD-MM-YYYY"""
    events_path = os.path.join(os.getcwd(), "_events")
    for file in Path(events_path).iterdir():
        if file.is_file():
            # checx for files which begin with date in MM-DD-YYYY format
            if re.match(r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])-\d{4}", file.name):
                yield file


def load_events():
    """
    read every event file, categorize it as either past or future, then sort them alphabetically by event.name
    """

    today = date.today()

    for event_file in iter_events():
        event = Event(event_file)
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
    tmpl_path = os.path.join(os.getcwd(), "_templates", filename)
    with Path(tmpl_path).open(mode="r") as f:
        return f.read()


def get_footer(template: str) -> str:
    return read_tmpl(f"{template}.footer.tmpl")


def get_header(template: str) -> str:
    return read_tmpl(f"{template}.header.tmpl")


@click.group()
def cli():
    pass


@cli.command()
def future():
    load_events()
    future_rendered = get_header("future_events")
    for k, v in sorted(FUTURE_EVENTS.items()):
        future_rendered += render_events(k, v)

    future_rendered += get_footer("future_events")

    print(future_rendered)


@cli.command
def past():
    load_events()
    past_rendered = get_header("past_events")
    for k, v in sorted(PAST_EVENTS.items(), reverse=True):
        past_rendered += render_events(k, v)

    past_rendered += get_footer("past_events")

    print(past_rendered)


if __name__ == "__main__":
    cli()
