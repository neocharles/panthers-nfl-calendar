#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

UPSTREAM = "https://cadem4.github.io/nfl-calendar/nfl-2026.ics"
ESPN_CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
ESPN_CDN_GAME = "https://cdn.espn.com/core/nfl/game?xhr=1&gameId={game_id}"
PANTHERS_ESPN_TEAM_ID = "29"
OUTPUT = Path("docs/panthers-playoffs.ics")


def fetch_text(url: str, *, user_agent: str | None = "panthers-nfl-calendar/1.0") -> str:
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str) -> dict:
    return json.loads(fetch_text(url, user_agent=None))


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
    before, events, after = [], [], []
    current = None
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
    out, replaced = [], False
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


def event_ids_from_collection(url: str) -> set[str]:
    payload = fetch_json(url)
    ids: set[str] = set()
    for item in payload.get("items", []):
        ref = item.get("$ref", "")
        match = re.search(r"/events/(\d+)", ref)
        if match:
            ids.add(match.group(1))
    return ids


def relevant_espn_event_ids() -> set[str]:
    ids: set[str] = set()

    # Only Panthers games are needed during the regular season.
    try:
        ids |= event_ids_from_collection(
            f"{ESPN_CORE}/seasons/2026/teams/{PANTHERS_ESPN_TEAM_ID}/events?limit=40"
        )
    except Exception as exc:
        print(f"Warning: ESPN Panthers event discovery failed: {exc}")

    # Add every postseason game. Empty/unpublished rounds are harmless.
    for week in range(1, 6):
        try:
            ids |= event_ids_from_collection(
                f"{ESPN_CORE}/seasons/2026/types/3/weeks/{week}/events?limit=20"
            )
        except Exception as exc:
            print(f"Warning: ESPN postseason week {week} discovery failed: {exc}")

    print(f"Discovered {len(ids)} relevant ESPN event IDs.")
    return ids


def score_from_game_package(game_id: str) -> tuple[tuple[str, str], tuple[str, str]] | None:
    payload = fetch_json(ESPN_CDN_GAME.format(game_id=game_id))
    package = payload.get("gamepackageJSON") or {}
    header = package.get("header") or {}
    competitions = header.get("competitions") or []
    if not competitions:
        return None

    competition = competitions[0]
    status = ((competition.get("status") or {}).get("type") or {})
    if not status.get("completed"):
        return None

    competitors = competition.get("competitors") or []
    away = next((c for c in competitors if c.get("homeAway") == "away"), None)
    home = next((c for c in competitors if c.get("homeAway") == "home"), None)
    if not away or not home:
        return None

    # The header reliably has IDs + scores. The boxscore provides display names.
    team_names: dict[str, str] = {}
    for team_entry in ((package.get("boxscore") or {}).get("teams") or []):
        team = team_entry.get("team") or {}
        team_id = str(team.get("id", ""))
        display_name = (team.get("displayName") or "").strip()
        if team_id and display_name:
            team_names[team_id] = display_name

    away_name = team_names.get(str(away.get("id", "")), "")
    home_name = team_names.get(str(home.get("id", "")), "")
    away_score = str(away.get("score", "")).strip()
    home_score = str(home.get("score", "")).strip()

    if not all((away_name, home_name, away_score, home_score)):
        return None

    return (away_name, home_name), (away_score, home_score)


def fetch_final_scores() -> dict[tuple[str, str], tuple[str, str]]:
    results: dict[tuple[str, str], tuple[str, str]] = {}
    failures = 0

    for game_id in sorted(relevant_espn_event_ids()):
        try:
            result = score_from_game_package(game_id)
            if result:
                matchup, score = result
                results[matchup] = score
        except Exception as exc:
            failures += 1
            print(f"Warning: ESPN game {game_id} score lookup failed: {exc}")

    print(f"Loaded {len(results)} completed scores from ESPN; {failures} game lookup failures.")
    return results


def add_final_score(event: list[str], final_scores: dict[tuple[str, str], tuple[str, str]]) -> list[str]:
    summary = field(event, "SUMMARY")
    if " @ " not in summary:
        return event

    away_name, home_name = (part.strip() for part in summary.split(" @ ", 1))
    score = final_scores.get((away_name, home_name))
    if not score:
        return event

    away_score, home_score = score
    return replace_field(event, "SUMMARY", f"{away_name} {away_score} @ {home_name} {home_score}")


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
    out = []
    for line in lines:
        for prefix, replacement in replacements.items():
            if line.startswith(prefix):
                out.append(replacement)
                break
        else:
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

    out_lines = []
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
    scored_count = sum(
        any(char.isdigit() for char in field(e, "SUMMARY"))
        and " @ " in field(e, "SUMMARY")
        for e in kept
    )
    print(f"Wrote {len(kept)} events to {OUTPUT}")
    print(f"Panthers games currently present: {panthers_count}")
    print(f"Completed games enriched with scores: {scored_count}")


if __name__ == "__main__":
    main()
