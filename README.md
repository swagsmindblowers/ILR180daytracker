# ILR180daytracker
A Claude Skill to keep tabs on your continuous residence for ILR in the UK (illustrative only)

See [`SKILL.md`](./SKILL.md) for how the skill works, and
[`scripts/compute_absences.py`](./scripts/compute_absences.py) for the
day-counting logic. Trips are logged in a CSV with columns
`depart_date,return_date,location,reason` -- `location` and `reason` are
optional free-text fields for where each trip abroad went and why.

## Install

To use this as a Claude Code skill, clone this repo and copy (or symlink) it
into your skills directory under its skill name:

```
git clone https://github.com/swagsmindblowers/ILR180daytracker.git
mkdir -p ~/.claude/skills/uk-continuous-residence-tracker
cp ILR180daytracker/SKILL.md ILR180daytracker/scripts -r ~/.claude/skills/uk-continuous-residence-tracker/
```

Or symlink instead of copying so future `git pull`s in the clone keep the
installed skill up to date:

```
ln -s "$(pwd)/ILR180daytracker" ~/.claude/skills/uk-continuous-residence-tracker
```

Restart Claude Code (or start a new session) to pick it up. The skill
triggers automatically when you ask about UK ILR continuous residence, the
180-day rule, or give it a list of trips abroad to check.
