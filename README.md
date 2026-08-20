# ILR180daytracker
A Claude Skill to keep tabs on your continuous residence for ILR in the UK (illustrative only)

See [`SKILL.md`](./SKILL.md) for how the skill works, and
[`scripts/compute_absences.py`](./scripts/compute_absences.py) for the
day-counting logic. Trips are logged in a CSV with columns
`depart_date,return_date,location,reason` -- `location` and `reason` are
optional free-text fields for where each trip abroad went and why.
