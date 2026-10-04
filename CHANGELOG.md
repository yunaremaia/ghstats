# Changelog

All notable changes to ghstats will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Error chaining in `StatsFetcher._run_gh`: the three `GHRuntimeError` raises
  inside `except` blocks now chain their cause (`raise ... from e`). Without the
  chain, Python prints "During handling of the above exception, another
  exception occurred" and buries the original diagnostic — for the timeout arm
  that meant the hanging `gh` command was unrecoverable from the traceback, and
  for the missing-binary arm `FileNotFoundError.filename` (which separates "gh
  is not installed" from "gh is installed but not on PATH") was discarded in
  favour of a fixed install hint.
- `zip()` in the compare path now passes `strict=True`. `users` and `values` are
  built from the same list today so the lengths always agree, but a bare `zip()`
  truncates to the shorter sequence: any future refactor that made them diverge
  would silently drop a user from the `--json-output` payload and from the
  winner list while still exiting 0. It now raises instead. Two guards added —
  an AST check that every `zip()` in `cli.py` is explicit, and a behavioural
  test that feeds the command a deliberately mismatched row.

### Changed
- `ruff check .` now selects `B904` and `B905`, so both defects above are caught
  by the CI lint job. The selection is green across `src/` and `tests/`.

## [0.2.0] - 2026-10-02

### Changed
- Renamed the distribution to `ghstats-py`. The name `ghstats` on PyPI belongs to
  a different author (kefir500/ghstats), so `pip install ghstats` would have
  installed someone else's program. The `ghstats` command is unchanged.

### Fixed
- `--version` no longer crashes after the distribution rename. It was declared
  as `@click.version_option(package_name="ghstats")`, which resolves through the
  *installed distribution* metadata; once the distribution became `ghstats-py`
  that lookup raised `RuntimeError: 'ghstats' maps to multiple installed
  distributions` and killed the flag on every invocation. It now reads
  `__version__` from the package, so it is independent of the PyPI name. Two
  regression guards were added.
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
