# ILR180daytracker

A Claude Skill to keep tabs on your continuous residence for ILR in the UK (illustrative only).

This skill tracks travel absences from the UK against the **180-days-in-any-rolling-12-months**
rule used for Indefinite Leave to Remain (ILR) on the standard 5-year settlement routes
(e.g. Skilled Worker, Spouse/Partner visa, Innovator Founder).

## Contents

- `SKILL.md` — the skill definition (trigger description + workflow instructions)
- `scripts/compute_absences.py` — deterministic rolling-12-month day-count script
- `evals/evals.json` — example test prompts used while developing this skill

## What it does

Most UK settlement (ILR) routes require that absences from the UK do not exceed 180 days
in *any* rolling 12-month period across the whole qualifying period (5 years for most
routes) — not simply 180 days per calendar year, since the relevant window can start on
any day. Checking every possible rolling 365-day window by eye is exactly the kind of thing
that's error-prone by hand, so the day-counting is delegated to `scripts/compute_absences.py`
rather than estimated.

Given a CSV trip log (`depart_date,return_date` columns, ISO `YYYY-MM-DD`), the skill:

1. Maintains/updates a persistent trip log, parsing whatever format the user provides
   (spreadsheet, calendar export, PDF, plain list of dates).
2. Runs the script to compute the trailing 365-day absence total, any breach periods, and
   the worst historical rolling window.
3. Produces a markdown report plus a self-contained HTML file with a chart of absences
   over time against the 180-day threshold.

## Installing

Drop this folder into your Claude skills directory (e.g. as `uk-continuous-residence-tracker/`
alongside your other skills), or package it as a `.skill` file and import it via Claude's
"Save skill" flow.

## Scope

This covers the ILR 180-day / 5-year rule only. It does not (yet) handle the 10-year long
residence route (548-day cap) or British citizenship (450-day/5-year, 90-day/final-year cap).

This is a mechanical calculator, not legal advice — see the caveats section the skill
generates in its reports.
