#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

UPSTREAM = "https://cadem4.github.io/nfl-calendar/nfl-2026.ics"
ESPN_SCOREBOARD = (
    "https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    "?limit=1000&dates=20260901-20270228"
)
OUTPUT = Path("docs/panthers-playoffs.ics")


def fetch_text(url: str, *, user_agent: str | None = "panthers-nfl-calendar/1.0") -> str:
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


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


def replace_field(event: list[str], name: str, value: str) -> list[str]:
    prefix = name + ":"
    out: list[str] = []
    replaced = False
    for line in event:
        if line.startswith(prefix):
            out.append(prefix + value)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.insert(1, prefix + value)
    return out


def keep_event(event: list[str]) -> bool:
    summary = field(event, "SUMMARY")
    categories = field(event, "CATEGORIES")

    panthers = "Carolina Panthers" in summary
    cats = {c.strip() for c in categories.split(",") if c.strip()}
    regular_season = any(c.startswith("Week ") for c in cats)
    postseason = ("NFL" in cats and "Football" in cats and not regular_season)

    return panthers or postseason


def fetch_final_scores() -> dict[tuple[str, str], tuple[str, str]]:
    """
    Return {(away_display_name, home_display_name): (away_score, home_score)}
    for completed 2026-season NFL games.

    ESPN is an enrichment source only. If it is unavailable or returns an
    unexpected payload, calendar generation continues without score changes.
    """
    try:
        payload = json.loads(fetch_text(ESPN_SCOREBOARD, user_agent=None))
        results: dict[tuple[str, str], tuple[str, str]] = {}

        for item in payload.get("events", []):
            season = item.get("season", {})
            if season.get("year") != 2026 or season.get("type") not in (2, 3):
                continue

            competitions = item.get("competitions") or []
            if not competitions:
                continue

            competition = competitions[0]
            status_type = ((competition.get("status") or {}).get("type") or {})
            if not status_type.get("completed"):
                continue

            competitors = competition.get("competitors") or []
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            if not away or not home:
                continue

            away_name = ((away.get("team") or {}).get("displayName") or "").strip()
            home_name = ((home.get("team") or {}).get("displayName") or "").strip()
            away_score = str(away.get("score", "")).strip()
            home_score = str(home.get("score", "")).strip()

            if away_name and home_name and away_score and home_score:
                results[(away_name, home_name)] = (away_score, home_score)

        print(f"Loaded {len(results)} completed scores from ESPN.")
        return results
    except Exception as exc:
        print(f"Warning: ESPN score enrichment unavailable: {exc}")
        return {}


def add_final_score(
    event: list[str],
    final_scores: dict[tuple[str, str], tuple[str, str]],
) -> list[str]:
    summary = field(event, "SUMMARY")
    if " @ " not in summary:
        return event

    away_name, home_name = (part.strip() for part in summary.split(" @ ", 1))
    score = final_scores.get((away_name, home_name))
    if not score:
        return event

    away_score, home_score = score
    scored_summary = f"{away_name} {away_score} @ {home_name} {home_score}"
    return replace_field(event, "SUMMARY", scored_summary)


def rewrite_calendar_name(lines: list[str]) -> list[str]:
    replacements = {
        "X-WR-CALDESC:": (
            "X-WR-CALDESC:Carolina Panthers regular season plus every NFL postseason "
            "game. TV and streaming details included when published; completed games "
            "include final scores."
        ),
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
    raw = fetch_text(UPSTREAM)
    lines = unfold_ical(raw)
    before, events, after = extract_events(lines)

    kept = [event for event in events if keep_event(event)]
    if not kept:
        raise RuntimeError("Filter produced zero events; refusing to overwrite calendar.")

    final_scores = fetch_final_scores()
    kept = [add_final_score(event, final_scores) for event in kept]
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
    OUTPUT.write_text(
        "\r\n".join(out_lines).rstrip("\r\n") + "\r\n",
        encoding="utf-8",
    )

    panthers_count = sum("Carolina Panthers" in field(e, "SUMMARY") for e in kept)
    scored_count = sum(
        " @ " in field(e, "SUMMARY")
        and any(ch.isdigit() for ch in field(e, "SUMMARY"))
        for e in kept
    )
    print(f"Wrote {len(kept)} events to {OUTPUT}")
    print(f"Panthers games currently present: {panthers_count}")
    print(f"Completed games enriched with scores: {scored_count}")


if __name__ == "__main__":
    main()
