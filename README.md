# ghstats — GitHub Stats Dashboard

Visualize your GitHub contributions, PRs, and activity from the terminal.

## Install

```bash
pip install ghstats
```

Or from source:

```bash
git clone https://github.com/yunaremaia/ghstats.git
cd ghstats
pip install -e .
```

## Features

- **User Stats**: Followers, repos, contributions, PRs
- **Contribution Heatmap**: 4-week activity grid
- **Repo Explorer**: Top repos by stars
- **Activity Feed**: Recent PRs and issues
- **Badge Generator**: Markdown badges for profile README
- **JSON Output**: For automation and CI

## Usage

```bash
# Your stats
ghstats stats yunaremaia

# Top repos
ghstats repos yunaremaia --limit 10

# Recent activity (last 30 days)
ghstats activity yunaremaia --days 30

# Repo stats
ghstats repo yunaremaia/driftcheck

# Generate badges
ghstats badge yunaremaia

# JSON output
ghstats stats yunaremaia --json-output
```

## Example Output

```
╭──────────────────── @yunaremaia ────────────────────╮
│ yunaremaia                                           │
│ Followers: 5 | Following: 10 | Repos: 12             │
╰──────────────────────────────────────────────────────┯
       Activity Summary        
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric             ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Contribs     │   903 │
│ PRs Opened         │    25 │
│ PRs Merged         │    18 │
│ Issues Opened      │    12 │
└────────────────────┴───────┘

Recent Activity (last 4 weeks)
🟩🟩🟩🟩🟩🟩🟩
🟩🟩🟩🟩🟩🟩🟩
🟩🟩🟩🟩🟩🟩🟩
🟩🟩🟩🟩🟩🟩🟩
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
