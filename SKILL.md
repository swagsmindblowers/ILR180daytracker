---
name: uk-continuous-residence-tracker
description: Track a person's absences from the UK against the 180-days-in-any-rolling-12-months rule used for Indefinite Leave to Remain (ILR) on the standard 5-year settlement routes (e.g. Skilled Worker, Spouse/Partner visa, Innovator Founder). Use this whenever someone wants to check their continuous residence for ILR, asks whether their travel puts their ILR at risk, wants to log trips abroad against their visa, mentions "180 days" or "continuous residence" in a UK immigration context, or gives you a file/list of travel dates and asks you to check it against their settlement route. Also use it to update or re-run a previous residence check once new trips have happened. Do not use it for the 10-year long residence route (548-day total cap) or for British citizenship applications (450-day cap) unless the user says that's what they mean -- ask if unsure, since the caps differ.
---

# UK ILR continuous residence tracker

## What this checks

Most UK settlement (ILR) routes require that absences from the UK do not
exceed **180 days in any rolling 12-month period** across the whole
qualifying period (5 years for most routes). This is *not* the same as 180
days per calendar year -- the relevant window can start on any day, so a
trip pattern that looks fine year-by-year can still breach the rule over a
window that straddles two calendar years. That's exactly the kind of check
that's easy to get wrong by eye, which is why the day-counting here is done
by a script (`scripts/compute_absences.py`), not estimated.

This skill is scoped to the 180-day / 5-year ILR rule specifically. If the
user is on the 10-year long residence route (548 days total) or asking about
naturalisation (450 days in 5 years, max 90 in the last 12 months), say so
explicitly and ask whether they want the calculation adjusted -- don't quietly
apply the wrong cap.

## Workflow

### 1. Find or start the trip log

This is meant to be re-run over years, so it works off a persistent CSV trip
log rather than a one-off file, with columns `depart_date,return_date,location,reason`
(dates in ISO `YYYY-MM-DD`), one row per trip abroad. `location` and `reason`
are free text -- `location` is where the trip was to (country or city is
fine), and `reason` is a short description of why (e.g. "family visit",
"work conference", "holiday"). Both are optional per row (leave blank if the
user doesn't know or doesn't want to share), but ask for them when logging a
new trip rather than leaving them out by default -- they're what make the
log useful as a travel record later, not just a day-count input.

- If the user has used this before, ask for (or look for) their existing log
  file before starting fresh -- don't silently start a new log and lose
  prior trips.
- Maintain the working log at `uk_residence_log.csv` in the session
  workspace as you go.
- If an existing log predates the `location`/`reason` columns (just
  `depart_date,return_date`), add the two columns and leave them blank for
  historical rows rather than blocking or rejecting the file -- backfill
  them only if the user volunteers the detail. Don't invent a location or
  reason for a trip the user hasn't described.
- Because a cloud session's filesystem doesn't necessarily persist to the
  next session, tell the user plainly that they should keep the log file
  you send them (or, if they have a folder connected via the desktop
  bridge, save it there) and hand it back to you next time so trips aren't
  lost. Don't let this be a surprise the user discovers only when the log
  is gone.

### 2. Parse whatever file the user gives you

The input format is not fixed -- it could be a spreadsheet with
departure/return columns, a calendar export (.ics) where trips show up as
events, a passport-stamps PDF, or just a list of dates in an email. Inspect
the actual file before assuming its shape.

- Figure out which column/field is the UK-departure date and which is the
  UK-return date. Column names vary a lot ("out", "departed", "left UK",
  event start/end in an .ics, etc.) -- if it's genuinely ambiguous which
  date means what, ask the user rather than guessing, since getting
  departure and return backwards silently corrupts every downstream number.
- Also look for anything that indicates where the trip was to and why it
  happened -- a calendar event's title/location field, a destination column
  in a spreadsheet, a note in an email -- and carry it into `location` /
  `reason`. If the source doesn't say, ask the user rather than leaving
  every row blank by default; a quick "where did each of these trips go,
  and why (roughly)?" is enough, and they can skip any they don't recall.
- Convert whatever you find into the `depart_date,return_date,location,reason`
  CSV format the script expects, and merge it into the running log (append
  new trips, and flag -- don't silently drop -- anything that looks like a
  duplicate or that overlaps a trip already in the log).
- A trip that's still in progress (no return date yet) should either be
  asked about ("are you still away, and if so as of when should I treat you
  as still absent?") or treated as ending on today's date with a note that
  it'll need updating once they're back.

### 3. Run the calculation

```
python3 scripts/compute_absences.py uk_residence_log.csv --as-of YYYY-MM-DD
```

Omit `--as-of` to use today's date. This prints JSON with the parsed trips
(including `location` and `reason` when present), every contiguous period
where the rolling 365-day total exceeded 180 (with the peak day count), the
single worst rolling window across the whole log, and the current status
(trailing 365-day total, days remaining before the cap, whether they're over
it right now). Read this script's own docstring if you want to understand
exactly how it counts days at trip boundaries -- worth doing once so you can
explain the convention to the user if they ask.

### 4. Write the report

Produce a markdown report covering:

- A table of every trip (dates, days abroad, location, reason) -- leave the
  location/reason cells blank rather than "N/A" or similar when the log
  doesn't have them, so genuinely-missing detail doesn't read as data.
- The current status in plain language: days used in the trailing 12
  months, days remaining before the 180 cap, and whether they're currently
  over it. If the most recent trip in the log ended well before the
  as-of date, say so explicitly next to this number -- a "1 day used,
  179 remaining" reading is only true of the log as given, and reads as
  reassuring in a way that's misleading if the user has traveled since
  their last logged trip and just hasn't told you yet. Pair it with the
  worst historical rolling window so the user isn't left with only a
  number that's really measuring "how long ago was your last logged trip."
- Any breach periods found, described as date ranges with the peak day
  count reached -- not a wall of overlapping windows. Where a breach period
  lines up with specific trips, naming their location/reason (e.g. "driven
  by an extended stay in India for a family matter") makes the report more
  useful to hand to an adviser than the date range alone.
- A short, clearly-labelled caveats section. This is a mechanical
  day-count against the general rule, not legal advice, and several things
  can change the real answer that this script cannot know about: the Home
  Office's COVID-19 absence disregard for certain periods in 2020-2021,
  discretion for a single absence over 180 days for a serious or
  compassionate reason (illness, death of a close family member, etc.),
  Crown/government service exceptions, and route-specific quirks. A trip's
  logged `reason` can be directly relevant here -- if a breach or
  near-breach trip was for something like a family illness or bereavement,
  say so and flag that discretion may apply, rather than treating every
  over-cap trip the same. Tell the user to run anything borderline past
  their immigration adviser rather than treating the script's answer as
  final -- especially if a breach period is close to now or the current
  trailing total is close to 180.

### 5. Build the chart

Use the **dataviz** skill for the actual chart styling and colour choices --
read its SKILL.md before writing chart code, don't freehand a palette.

The chart should show, on a shared time axis: each trip as a marked period
(so the user can see when they travelled -- a hover/label with the
location is a nice touch if the chart format supports it), and a line for
the trailing 365-day rolling total (from the script's `rolling_series`)
against a horizontal reference line at 180. This lets the user see at a
glance how close the line got to the threshold and when, not just today's
number.

### 6. Deliver

Combine the report and chart into a single self-contained HTML file: inline
all CSS and JS directly in the file, with no `<script src="https://...">`
or other network requests. Don't reach for a CDN-hosted charting library
(Chart.js and similar) for this -- draw the chart as inline SVG instead. An
SVG line/area chart is simple enough to hand-build for this data (a couple
of `<path>`/`<rect>` elements plus a dashed reference line) and it keeps the
file genuinely self-contained, which matters because this file gets
persisted and reopened later, possibly without network access.

Send it with `SendUserFile`. Since the
user will want to re-check this after future trips, follow this session's
guidance on persisting revisitable HTML outputs (e.g. the `Artifact` tool or
the desktop artifact bridge, if available) rather than treating it as a
one-off. Also send back the updated `uk_residence_log.csv` itself as a
plain file (not just embedded in the HTML) so the user has something to
hand back to you next time -- the whole point of the persistent log is that
they don't have to reconstruct their travel history from scratch on every
run.
