# Panthers + NFL Playoffs Calendar

A personal iCalendar subscription containing:

- every Carolina Panthers regular-season game
- every NFL postseason game: Wild Card, Divisional, Conference Championships, and Super Bowl
- TV/network and streaming information when published
- automatic schedule/broadcast updates

The feed is generated from the actively maintained [CadeM4/nfl-calendar](https://github.com/CadeM4/nfl-calendar) master NFL calendar.

## Calendar feed

Once GitHub Pages is enabled for this repository from the `main` branch and `/docs` folder:

```
https://neocharles.github.io/panthers-nfl-calendar/panthers-playoffs.ics
```

Subscribe to the URL instead of downloading/importing the file so later changes can propagate to your calendar.

## What is included

The generator retains an event when either:

1. Carolina Panthers are one of the two teams, or
2. the event is a postseason game.

The upstream master feed excludes preseason and the Pro Bowl. Regular-season events carry a `Week 1` through `Week 18` category, so non-week NFL events in that feed are treated as postseason games.

## Updates

GitHub Actions checks the upstream feed every six hours. If the resulting calendar changes, the generated `docs/panthers-playoffs.ics` file is committed back to this repository.

The upstream project also refreshes its NFL source data on a six-hour cadence. Calendar-client subscription polling is controlled by the client, so iPhone Calendar may not reflect a newly published change immediately after this repository updates.

## Files

- `generate_calendar.py` filters the upstream NFL calendar.
- `.github/workflows/update-calendar.yml` runs the generator automatically.
- `docs/panthers-playoffs.ics` is the calendar subscription file.
