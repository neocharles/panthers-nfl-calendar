# Panthers + NFL Playoffs Calendar

[![Update Calendar](https://github.com/neocharles/panthers-nfl-calendar/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/neocharles/panthers-nfl-calendar/actions/workflows/update-calendar.yml)
![Calendar](https://img.shields.io/badge/format-iCalendar%20%2F%20ICS-0057B8)
![Refresh](https://img.shields.io/badge/refresh-every%206%20hours-0085CA)
![Panthers](https://img.shields.io/badge/team-Carolina%20Panthers-101820)
![Built with ChatGPT](https://img.shields.io/badge/built%20with-ChatGPT-10A37F)

A lightweight, automatically updated calendar feed for **Carolina Panthers football and the complete NFL postseason**.

Subscribe once and keep Panthers games, playoff matchups, broadcast information, kickoff changes, and final scores synchronized with your calendar.

## Subscribe

**Calendar feed**

```text
https://neocharles.github.io/panthers-nfl-calendar/panthers-playoffs.ics
```

### iPhone / iPad

1. Open **Calendar**.
2. Tap **Calendars**.
3. Tap **Add Calendar**.
4. Choose **Add Subscription Calendar**.
5. Paste the calendar feed URL above.

Use a **subscription** rather than downloading and importing the `.ics` file. A subscription allows future schedule, broadcast, playoff, and score changes to update the existing calendar events.

## What's included

| Feature | Included |
| --- | :---: |
| Carolina Panthers regular-season games | ✅ |
| Carolina Panthers postseason games | ✅ |
| Every Wild Card game | ✅ |
| Every Divisional Round game | ✅ |
| Both Conference Championship games | ✅ |
| Super Bowl | ✅ |
| TV network information | ✅ |
| Streaming service information | ✅ |
| Venue information | ✅ |
| Kickoff/date changes | ✅ |
| Final scores for completed games | ✅ |
| Automatic refresh | ✅ |
| Preseason | ❌ |
| Pro Bowl | ❌ |
| Other teams' regular-season games | ❌ |

## Event format

Before a game:

```text
Carolina Panthers @ Tampa Bay Buccaneers
```

After the game is completed:

```text
Carolina Panthers 30 @ Tampa Bay Buccaneers 48
```

The event keeps the same calendar UID, allowing subscribed calendar clients to update the existing event instead of creating a duplicate.

TV and streaming details remain in the event description when they are available from the source data.

## How it works

```text
CadeM4/nfl-calendar
        │
        │ schedule + kickoff + venue + TV/streaming
        ▼
generate_calendar.py ──────── ESPN NFL scoreboard
        │                         │
        │ filter                  │ completed scores
        │                         │
        └────────────┬────────────┘
                     ▼
          panthers-playoffs.ics
                     │
                     ▼
               GitHub Pages
                     │
                     ▼
          Calendar subscription
```

The generator keeps an event when either:

1. the Carolina Panthers are playing, or
2. the event is an NFL postseason game.

Regular-season games for the other 31 teams are discarded.

## Data sources

### Schedule, broadcast and venue data

Schedule and viewing information comes from the actively maintained [CadeM4/nfl-calendar](https://github.com/CadeM4/nfl-calendar) project.

That upstream feed provides the NFL schedule along with available venue, television network, streaming, and schedule-change information.

### Final scores

Completed-game scores are added using ESPN's public NFL scoreboard data.

ESPN is treated as **optional enrichment**. If that request fails or the response cannot be parsed, calendar generation continues normally using the schedule and broadcast information. A temporary scoreboard problem therefore does not break the calendar feed.

## Automatic updates

The GitHub Actions workflow runs every **six hours** and:

1. downloads the current upstream NFL calendar,
2. keeps all Panthers regular-season games,
3. keeps every NFL postseason game,
4. checks ESPN for completed-game scores,
5. updates event titles with final scores,
6. generates `docs/panthers-playoffs.ics`, and
7. commits the file only when something has changed.

The upstream NFL calendar also refreshes on a six-hour cadence.

> Calendar applications control how often subscribed calendars are polled. The feed may update on GitHub before a change appears on an iPhone or other calendar client.

## Project structure

| Path | Purpose |
| --- | --- |
| `generate_calendar.py` | Filters the upstream calendar and enriches completed games with scores |
| `.github/workflows/update-calendar.yml` | Scheduled six-hour GitHub Actions workflow |
| `docs/panthers-playoffs.ics` | Published calendar subscription |
| `docs/index.html` | GitHub Pages landing page |
| `docs/.nojekyll` | Serves the Pages files without Jekyll processing |

## Reliability

The project intentionally separates **schedule data** from **score enrichment**.

If ESPN is unavailable, the calendar can still update schedule, venue, broadcast, and playoff information. If the upstream calendar cannot be retrieved or filtering unexpectedly produces no events, the generator refuses to overwrite the published calendar with an empty feed.

## Acknowledgements

This project builds on the excellent work in [CadeM4/nfl-calendar](https://github.com/CadeM4/nfl-calendar), which provides the maintained NFL schedule and viewing-data foundation.

Project design, filtering logic, GitHub Actions automation, score enrichment, and documentation were developed collaboratively with **[ChatGPT by OpenAI](https://chatgpt.com/)**.

## Disclaimer

This is an independent personal project and is not affiliated with, endorsed by, or sponsored by the Carolina Panthers, the NFL, ESPN, or their respective affiliates.

Team names, league names, and related marks belong to their respective owners.
