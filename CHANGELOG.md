# Changelog

All notable changes to ghstats will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed the distribution to `ghstats-py`. The name `ghstats` on PyPI belongs to
  a different author (kefir500/ghstats), so `pip install ghstats` would have
  installed someone else's program. The `ghstats` command is unchanged.

### Fixed
- Fix the crash in every command that called the API: REST endpoint paths are now
  passed to `gh api` as a single joined argument (`users/<login>`) instead of
  split segments (`users <login>`), which `gh` rejects with
  `accepts 1 arg(s), received 2`
- Route search queries through the REST `search/issues` endpoint reachable via
  `gh api`, replacing the invalid `gh api search issues ... --limit` form
- Page the repository listing with `?per_page=&page=` query parameters, since
  `gh api` has no `--per-page`/`--paginate` flags
- Use a `YYYY-MM-DD` cutoff in the `updated:` search qualifier, which is the only
  date format GitHub search accepts

## [0.1.0] - 2026-09-09

### Added
- Initial release: GitHub Stats Dashboard
- User statistics command (`ghstats stats`) with followers, contributions, and PR counts
- 4-week activity contribution heatmap grid
- Repository explorer and statistics commands (`ghstats repos`, `ghstats repo`)
- Recent activity feed (`ghstats activity`)
- Markdown badge generation for profile READMEs (`ghstats badge`)
- JSON output mode (`--json-output`) for CI and automation
