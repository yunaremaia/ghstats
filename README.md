# ghstats — GitHub Stats Dashboard

![CI](https://github.com/yunaremaia/ghstats/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10-blue.svg)
![License](https://img.shields.io/github/license/yunaremaia/ghstats)
![Stars](https://img.shields.io/github/stars/yunaremaia/ghstats)


Visualize your GitHub contributions, PRs, and activity from the terminal.

## Install

This project is not published on PyPI yet, so install it straight from git:

```bash
pip install git+https://github.com/yunaremaia/ghstats.git
```

The short name `ghstats` is **not** an install target for this project: on PyPI
that name belongs to a different author ([kefir500/ghstats](https://github.com/kefir500/ghstats),
a release download counter). Installing it would silently get you a different
program. When this project is published, the distribution name will be
`ghstats-py` and the command stays `ghstats`.

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

# Compare two or more users (up to five)
ghstats compare yunaremaia octocat
ghstats compare yunaremaia octocat --json-output

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


If this tool is useful to you, a star helps other people find it.

## Sponsoring / Treasury

ghstats is MIT licensed and maintained in the open. Rendering contribution graphs, PR
stats, and activity from the terminal stays free, and keeping the GitHub API handling
and output formats current is the ongoing work. If it saves you time, you can support
continued development through GitHub Sponsors or the Solana treasury below.

Funding details are declared in [`.github/FUNDING.yml`](.github/FUNDING.yml), which is
what GitHub reads to render the **Sponsor** button on this repository.

- **GitHub Sponsors:** [@yunaremaia](https://github.com/sponsors/yunaremaia)
- **Solana:** `Eeztv1nCYUt1fwGWpzKC948gaWfjejYCAuLtUMgzDWbW`

Use the Solana address only for intended donations. Anyone can generate a similar
address, so verify the address against `.github/FUNDING.yml` before sending funds.

## Related tools

- **[oss-contribution-finder](https://github.com/yunaremaia/oss-contribution-finder)** — find OSS projects ready to contribute to
- **[ci-test-gate](https://github.com/yunaremaia/ci-test-gate)** — block PRs until the required tests actually run
- **[agent-workspace](https://github.com/yunaremaia/agent-workspace)** — isolated workspaces per AI agent session
- **[gfi](https://github.com/yunaremaia/gfi)** — find well-scoped good first issues to start on

Part of a family of focused, single-purpose developer tools — each one does one thing
and does it well.

## License

MIT
