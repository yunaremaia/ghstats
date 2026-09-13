# ghstats — GitHub Stats Dashboard

Visualize your GitHub contributions, PRs, and activity from the terminal.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Show your stats
ghstats stats yunaremaia

# Show top repos
ghstats repos yunaremaia --limit 10

# Show recent activity
ghstats activity yunaremaia --days 30

# Show repo stats
ghstats repo yunaremaia/driftcheck

# Generate markdown badges
ghstats badge yunaremaia

# JSON output
ghstats stats yunaremaia --json-output
```

## Why

Quick overview of GitHub activity without leaving the terminal. Useful for:
- Profile README updates
- Tracking contribution metrics
- Monitoring PR merge rates

## License

MIT
