#!/usr/bin/env python3
"""
compute_absences.py

Deterministic day-counting for the UK ILR "180 days absent in any rolling
12-month period" continuous residence rule.

Why this is a script and not something Claude does by mental arithmetic:
checking EVERY possible rolling 365-day window (not just calendar years) is
exactly the kind of thing that's tedious and error-prone by hand but trivial
and exact for code. Off-by-one errors here are not cosmetic -- they change
the legal answer -- so the counting itself is delegated to this script and
Claude's job is parsing input and writing up the result.

Input: a CSV of trips abroad with columns `depart_date,return_date`
(ISO 8601, e.g. 2024-03-01). `depart_date` is the last day physically in the
UK is depart_date - 1 (i.e. depart_date itself is already a day abroad), and
`return_date` is the day they land back in the UK (also counted as a day
abroad, since UKVI generally counts the day of return as still absent unless
told otherwise -- this convention is a simplification and is called out in
the output so the user can sanity-check it against their own itineraries).

Output: JSON to stdout with:
  - trips: parsed trip list with per-trip day counts
  - daily_series: date + cumulative "is abroad" for charting
  - rolling: the rolling 365-day-window absence total ending on each day
    that could plausibly be a local maximum (trip boundaries +/- 1 day),
    NOT literally every calendar day (that would be redundant -- the total
    can only change on days adjacent to a trip boundary)
  - violations: any window (start, end, total_days) where total_days > 180
  - current_status: as of the last date in the data (or --as-of), the
    trailing-365-day total, days remaining before the 180 cap, and whether
    currently over the limit
"""
import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta


def parse_date(s):
    s = s.strip()
    return datetime.strptime(s, "%Y-%m-%d").date()


def load_trips(csv_path):
    trips = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        required = {"depart_date", "return_date"}
        if not required.issubset(set(h.strip() for h in reader.fieldnames or [])):
            raise ValueError(
                f"CSV must have columns depart_date,return_date -- got {reader.fieldnames}"
            )
        for i, row in enumerate(reader):
            depart = parse_date(row["depart_date"])
            ret = parse_date(row["return_date"])
            if ret < depart:
                raise ValueError(
                    f"Row {i}: return_date {ret} is before depart_date {depart}"
                )
            trips.append({"depart_date": depart, "return_date": ret})
    trips.sort(key=lambda t: t["depart_date"])
    return trips


def check_overlaps(trips):
    for a, b in zip(trips, trips[1:]):
        if b["depart_date"] <= a["return_date"]:
            raise ValueError(
                f"Overlapping trips: {a['depart_date']}..{a['return_date']} and "
                f"{b['depart_date']}..{b['return_date']}. Fix the log before re-running."
            )


def build_prefix_sums(trips):
    """Day-level abroad indicator turned into a prefix-sum array so any
    window's total is a O(1) lookup instead of re-scanning every day."""
    if not trips:
        return {}, None, None
    min_day = trips[0]["depart_date"]
    max_day = trips[-1]["return_date"]
    n = (max_day - min_day).days + 1
    abroad = [0] * (n + 1)
    for t in trips:
        start_idx = (t["depart_date"] - min_day).days
        end_idx = (t["return_date"] - min_day).days
        for i in range(start_idx, end_idx + 1):
            abroad[i] = 1
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + abroad[i]
    return prefix, min_day, n


def window_total(prefix, min_day, n, window_end_date, window_days=365):
    """Total days abroad in the 365 days ending on window_end_date inclusive."""
    window_start_date = window_end_date - timedelta(days=window_days - 1)
    end_idx = (window_end_date - min_day).days
    start_idx = (window_start_date - min_day).days
    end_idx = max(0, min(end_idx, n - 1))
    start_idx = max(0, min(start_idx, n - 1))
    if window_end_date < min_day:
        return 0
    lo = max(start_idx, 0)
    hi = min(end_idx, n - 1)
    if lo > hi:
        return 0
    return prefix[hi + 1] - prefix[lo]


def candidate_check_dates(trips, as_of):
    """The trailing-365-day total only changes on two kinds of days: when a
    trip boundary first enters the window (window_end == boundary date), and
    365 days later when that same boundary is about to fall back out of the
    window (window_end == boundary date + 364, the last day it's still in
    range). Checking windows ending on those dates (+/- 1 day for safety)
    finds every local maximum and every threshold crossing without scanning
    every single calendar day -- same result as a brute-force scan, far
    fewer checks."""
    dates = set()
    for t in trips:
        for d in (t["depart_date"], t["return_date"]):
            for offset in (-1, 0, 1, 364, 365):
                dates.add(d + timedelta(days=offset))
    dates.add(as_of)
    return sorted(x for x in dates if x <= as_of)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", help="CSV with depart_date,return_date columns")
    ap.add_argument(
        "--as-of",
        default=None,
        help="Date (YYYY-MM-DD) to treat as 'today' for current-status calc. Defaults to actual today.",
    )
    ap.add_argument("--cap", type=int, default=180, help="Absence day cap (default 180 for ILR)")
    args = ap.parse_args()

    trips = load_trips(args.csv_path)
    check_overlaps(trips)

    as_of = parse_date(args.as_of) if args.as_of else date.today()

    for t in trips:
        t["days_abroad"] = (t["return_date"] - t["depart_date"]).days + 1

    if not trips:
        print(json.dumps({"trips": [], "violations": [], "current_status": None}))
        return

    prefix, min_day, n = build_prefix_sums(trips)

    # The rolling total is a step function that only changes value at the
    # candidate dates (each is a trip boundary entering or leaving the
    # window) -- it is constant in between. So evaluating just these points,
    # in order, is enough to find every contiguous stretch where the total
    # exceeds the cap; there's no hidden dip or spike hiding between them.
    check_dates = candidate_check_dates(trips, as_of)
    evaluated = []
    max_window = {"total_days": -1}
    for end_date in check_dates:
        total = window_total(prefix, min_day, n, end_date)
        start_date = end_date - timedelta(days=364)
        evaluated.append({"window_end": end_date, "window_start": start_date, "total_days": total})
        if total > max_window["total_days"]:
            max_window = {
                "window_end": end_date.isoformat(),
                "window_start": start_date.isoformat(),
                "total_days": total,
            }

    # Group consecutive evaluated points that are all over the cap into a
    # single contiguous breach period, tracking the peak within each.
    merged_violations = []
    current_group = None
    for point in evaluated:
        if point["total_days"] > args.cap:
            if current_group is None:
                current_group = {
                    "window_start": point["window_start"].isoformat(),
                    "window_end": point["window_end"].isoformat(),
                    "total_days": point["total_days"],
                    "peak_window_start": point["window_start"].isoformat(),
                }
            else:
                current_group["window_end"] = point["window_end"].isoformat()
                if point["total_days"] > current_group["total_days"]:
                    current_group["total_days"] = point["total_days"]
                    current_group["peak_window_start"] = point["window_start"].isoformat()
        else:
            if current_group is not None:
                merged_violations.append(current_group)
                current_group = None
    if current_group is not None:
        merged_violations.append(current_group)

    current_total = window_total(prefix, min_day, n, as_of)
    current_status = {
        "as_of": as_of.isoformat(),
        "trailing_365_day_total": current_total,
        "cap": args.cap,
        "days_remaining": args.cap - current_total,
        "currently_over_cap": current_total > args.cap,
    }

    # Sparse series of (date, cumulative_days_abroad_to_date) at trip boundaries, for charting
    boundary_series = []
    running = 0
    for t in trips:
        boundary_series.append({"date": t["depart_date"].isoformat(), "event": "depart"})
        running += t["days_abroad"]
        boundary_series.append(
            {
                "date": t["return_date"].isoformat(),
                "event": "return",
                "cumulative_days_abroad": running,
            }
        )

    # Rolling-total series sampled at every candidate check date, for the chart's threshold line
    rolling_series = [
        {
            "date": d.isoformat(),
            "trailing_365_day_total": window_total(prefix, min_day, n, d),
        }
        for d in candidate_check_dates(trips, as_of)
    ]

    out = {
        "trips": [
            {
                "depart_date": t["depart_date"].isoformat(),
                "return_date": t["return_date"].isoformat(),
                "days_abroad": t["days_abroad"],
            }
            for t in trips
        ],
        "total_days_abroad_all_time": sum(t["days_abroad"] for t in trips),
        "max_rolling_window": max_window,
        "violations": merged_violations,
        "current_status": current_status,
        "rolling_series": rolling_series,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
