#!/usr/bin/env python3
from __future__ import annotations

import urllib.request
from pathlib import Path

UPSTREAM = "https://cadem4.github.io/nfl-calendar/nfl-2026.ics"
OUTPUT = Path("docs/panthers-playoffs.ics")


def unfold_ical(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def fold_line(line: str, limit: int = 75) -> list[str]:
    # iCalendar folding is specified in octets. For this feed's mostly ASCII
    # content, character-length folding is sufficient and keeps the output valid.
    if len(line) <= limit:
        return [line]
    parts = [line[:limit]]
    line = line[limit:]
    while line:
        take = limit - 1
        parts.append(" " + line[:take])
        line = line[take:]
    return parts


def extract_events(lines: list[str]) -> tuple[list[str], list[list[str]], list[str]]:
    before: list[str] = []
    events: list[list[str]] = []
    after: list[str] = []
    current: list[str] | None = None
    seen_event = False

    for line in lines:
        if line == "BEGIN:VEVENT":
            current = [line]
            seen_event = True
        elif line == "END:VEVENT" and current is not None:
            current.append(line)
            events.append(current)
            current = None
        elif current is not None:
            current.append(line)
        elif not seen_event:
            before.append(line)
        else:
            after.append(line)
    return before, events, after


def field(event: list[str], name: str) -> str:
    prefix = name + ":"
    for line in event:
        if line.startswith(prefix):
            return line[len(prefix):]
    return ""


def keep_event(event: list[str]) -> bool:
    summary = field(event, "SUMMARY")
    categories = field(event, "CATEGORIES")

    panthers = "Carolina Panthers" in summary

    cats = {c.strip() for c in categories.split(",") if c.strip()}
    regular_season = any(c.startswith("Week ") for c in cats)
    postseason = ("NFL" in cats and "Football" in cats and not regular_season)

    return panthers or postseason


def rewrite_calendar_name(lines: list[str]) -> list[str]:
    replacements = {
        "X-WR-CALDESC:": "X-WR-CALDESC:Carolina Panthers regular season plus every NFL postseason game. TV and streaming details included when published.",
        "NAME:": "NAME:Panthers + NFL Playoffs",
        "X-WR-CALNAME:": "X-WR-CALNAME:Panthers + NFL Playoffs",
    }
    out: list[str] = []
    for line in lines:
        replaced = False
        for prefix, replacement in replacements.items():
            if line.startswith(prefix):
                out.append(replacement)
                replaced = True
                break
        if not replaced:
            out.append(line)
    return out


def main() -> None:
    with urllib.request.urlopen(UPSTREAM, timeout=30) as response:
        raw = response.read().decode("utf-8")

    lines = unfold_ical(raw)
    before, events, after = extract_events(lines)

    kept = [event for event in events if keep_event(event)]
    if not kept:
        raise RuntimeError("Filter produced zero events; refusing to overwrite calendar.")

    before = rewrite_calendar_name(before)

    out_lines: list[str] = []
    for line in before:
        out_lines.extend(fold_line(line))
    for event in kept:
        for line in event:
            out_lines.extend(fold_line(line))
    for line in after:
        if line:
            out_lines.extend(fold_line(line))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\r\n".join(out_lines).rstrip("\r\n") + "\r\n", encoding="utf-8")

    panthers_count = sum("Carolina Panthers" in field(e, "SUMMARY") for e in kept)
    postseason_count = len(kept) - sum(
        any(c.startswith("Week ") for c in field(e, "CATEGORIES").split(","))
        for e in kept
        if "Carolina Panthers" not in field(e, "SUMMARY")
    )
    print(f"Wrote {len(kept)} events to {OUTPUT}")
    print(f"Panthers games currently present: {panthers_count}")


if __name__ == "__main__":
    main()
