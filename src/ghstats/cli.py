"""CLI for ghstats — GitHub Stats Dashboard."""
from __future__ import annotations

import json
import sys
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn

from ghstats.fetcher import StatsFetcher, UserStats

console = Console()


def _comparison_metrics(stats: UserStats) -> dict[str, int]:
    """Return the comparable numeric metrics for one user, handling missing fields gracefully."""
    contributions = getattr(stats, "contributions", None)
    pull_requests = getattr(stats, "pull_requests", None)
    issues = getattr(stats, "issues", None)

    return {
        "Followers": getattr(stats, "followers", 0) if getattr(stats, "followers", None) is not None else 0,
        "Following": getattr(stats, "following", 0) if getattr(stats, "following", None) is not None else 0,
        "Public Repos": getattr(stats, "public_repos", 0) if getattr(stats, "public_repos", None) is not None else 0,
        "Contributions": getattr(contributions, "total_contributions", 0) if contributions is not None and getattr(contributions, "total_contributions", None) is not None else 0,
        "PRs Opened": getattr(pull_requests, "total_opened", 0) if pull_requests is not None and getattr(pull_requests, "total_opened", None) is not None else 0,
        "PRs Merged": getattr(pull_requests, "total_merged", 0) if pull_requests is not None and getattr(pull_requests, "total_merged", None) is not None else 0,
        "Issues Opened": getattr(issues, "total_opened", 0) if issues is not None and getattr(issues, "total_opened", None) is not None else 0,
    }


def _comparison_rows(stats_list: list[UserStats]) -> list[tuple[str, list[int], list[str]]]:
    """Build metric rows and the users tied for the highest value."""
    if not stats_list:
        return []

    rows: list[tuple[str, list[int], list[str]]] = []
    metrics = [_comparison_metrics(stats) for stats in stats_list]

    seen: set[str] = set()
    metric_names: list[str] = []
    for m in metrics:
        for k in m:
            if k not in seen:
                seen.add(k)
                metric_names.append(k)

    for metric_name in metric_names:
        values = [metric.get(metric_name, 0) for metric in metrics]
        highest = max(values) if values else 0
        winners = [getattr(stats, "login", "") for stats, value in zip(stats_list, values) if value == highest]
        rows.append((metric_name, values, winners))
    return rows


def _format_number(n: int) -> str:
    """Format number with k/M suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _format_date(date_str: str) -> str:
    """Format ISO date to readable string."""
    if not date_str:
        return "—"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str[:10]


@click.group()
@click.version_option(package_name="ghstats")
def cli():
    """ghstats — GitHub Stats Dashboard."""
    pass


@cli.command()
@click.argument("username", default="yunaremaia")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
def stats(username, json_out):
    """Show comprehensive stats for a GitHub user."""
    fetcher = StatsFetcher(username)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Fetching stats for {username}...", total=None)
        user_stats = fetcher.fetch_user_stats()
        progress.update(task, completed=True)

    if json_out:
        output = {
            "login": user_stats.login,
            "name": user_stats.name,
            "followers": user_stats.followers,
            "following": user_stats.following,
            "public_repos": user_stats.public_repos,
            "total_contributions": user_stats.contributions.total_contributions,
            "prs_opened": user_stats.pull_requests.total_opened,
            "prs_merged": user_stats.pull_requests.total_merged,
            "issues_opened": user_stats.issues.total_opened,
        }
        click.echo(json.dumps(output, indent=2))
        return

    console.print(Panel(
        f"[bold]{user_stats.name or user_stats.login}[/bold]\n"
        f"Followers: [cyan]{_format_number(user_stats.followers)}[/cyan] | "
        f"Following: [cyan]{_format_number(user_stats.following)}[/cyan] | "
        f"Repos: [cyan]{_format_number(user_stats.public_repos)}[/cyan]",
        title=f"@{user_stats.login}"
    ))

    # Activity summary
    table = Table(title="Activity Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Contributions", str(user_stats.contributions.total_contributions))
    table.add_row("PRs Opened", str(user_stats.pull_requests.total_opened))
    table.add_row("PRs Merged", str(user_stats.pull_requests.total_merged))
    table.add_row("Issues Opened", str(user_stats.issues.total_opened))

    console.print(table)

    # Recent activity heatmap (last 4 weeks)
    if user_stats.contributions.weeks:
        console.print("\n[bold]Recent Activity (last 4 weeks)[/bold]")
        weeks = user_stats.contributions.weeks[-4:]
        for week in weeks:
            days_str = ""
            for day in week:
                if day.count > 0:
                    days_str += "🟩"
                else:
                    days_str += "⬜"
            console.print(days_str)


@cli.command()
@click.argument("usernames", nargs=-1, required=True)
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
def compare(usernames, json_out):
    """Compare GitHub statistics for two to five users."""
    if not 2 <= len(usernames) <= 5:
        raise click.UsageError("compare requires between 2 and 5 usernames")

    stats_list = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching comparison stats...", total=len(usernames))
        for username in usernames:
            stats_list.append(StatsFetcher(username).fetch_user_stats())
            progress.advance(task)

    rows = _comparison_rows(stats_list)
    if json_out:
        payload = {
            "users": [stats.login for stats in stats_list],
            "metrics": [
                {
                    "name": metric_name,
                    "values": {
                        stats.login: value for stats, value in zip(stats_list, values)
                    },
                    "winners": winners,
                }
                for metric_name, values, winners in rows
            ],
        }
        click.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="GitHub User Comparison")
    table.add_column("Metric", style="cyan")
    for username in usernames:
        table.add_column(username, justify="right", no_wrap=True)
    table.add_column("Winner", style="green")

    for metric_name, values, winners in rows:
        highest = max(values)
        rendered_values = [
            f"[bold green]{value}[/bold green]" if value == highest else str(value)
            for value in values
        ]
        winner = ", ".join(winners) if len(winners) > 1 else (winners[0] if winners else "N/A")
        table.add_row(metric_name, *rendered_values, winner)

    console.print(table)


@cli.command()
@click.argument("username", default="yunaremaia")
@click.option("--limit", "-n", default=20, help="Max repos to show")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
def repos(username, limit, json_out):
    """List top repos for a user."""
    fetcher = StatsFetcher(username)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Fetching repos for {username}...", total=None)
        repos = fetcher.fetch_user_repos(limit=limit)
        progress.update(task, completed=True)

    if not repos:
        console.print(f"[yellow]No repos found for {username}.[/yellow]")
        return

    # Sort by stars
    repos.sort(key=lambda x: x.get("stars", 0), reverse=True)

    if json_out:
        click.echo(json.dumps(repos, indent=2, default=str))
        return

    console.print(Panel(
        f"[bold]Top Repos for @{username}[/bold]",
        title="Repos"
    ))

    table = Table()
    table.add_column("Repo", width=30)
    table.add_column("Stars", justify="right", width=8)
    table.add_column("Forks", justify="right", width=8)
    table.add_column("Lang", width=10)
    table.add_column("Description", width=40)

    for repo in repos:
        table.add_row(
            repo["name"],
            f"⭐ {repo['stars']}",
            str(repo["forks"]),
            repo["language"] or "—",
            (repo["description"] or "—")[:38],
        )

    console.print(table)


@cli.command()
@click.argument("username", default="yunaremaia")
@click.option("--days", "-d", default=30, help="Days of history")
@click.option("--json-output", "json_out", is_flag=True, help="Output as JSON")
def activity(username, days, json_out):
    """Show recent activity for a user."""
    fetcher = StatsFetcher(username)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Fetching activity for {username}...", total=None)
        activities = fetcher.fetch_contribution_history(days=days)
        progress.update(task, completed=True)

    if not activities:
        console.print(f"[yellow]No recent activity found for {username}.[/yellow]")
        return

    if json_out:
        click.echo(json.dumps(activities, indent=2, default=str))
        return

    console.print(Panel(
        f"[bold]Recent Activity[/bold] — {len(activities)} events",
        title=f"@{username}"
    ))

    table = Table(show_lines=False)
    table.add_column("Type", width=6)
    table.add_column("Title", width=50)
    table.add_column("Repo", width=25)
    table.add_column("Status", width=10)
    table.add_column("Date", width=12)

    for act in activities[:30]:
        type_icon = "🔀" if act["type"] == "pr" else "📝"
        status_color = {
            "merged": "green",
            "open": "blue",
            "closed": "red",
        }.get(act.get("state", ""), "white")
        status = act.get("state", "—")

        table.add_row(
            type_icon,
            (act["title"] or "—")[:48],
            (act["repo"] or "—")[:23],
            f"[{status_color}]{status}[/{status_color}]",
            _format_date(act.get("date", "")),
        )

    console.print(table)


@cli.command()
@click.argument("username", default="yunaremaia")
def badge(username):
    """Generate markdown badge for profile README."""
    fetcher = StatsFetcher(username)
    stats = fetcher.fetch_user_stats()

    # Generate badge URLs
    total = stats.contributions.total_contributions
    prs = stats.pull_requests.total_opened
    repos = stats.public_repos

    console.print("[bold]Markdown Badges:[/bold]\n")

    console.print(f"Total Contributions: `{total}`")
    console.print(f"PRs Opened: `{prs}`")
    console.print(f"Public Repos: `{repos}`")
    console.print()

    # Shields.io badges
    console.print("[bold]Shields.io:[/bold]")
    console.print(f"![Contributions](https://img.shields.io/badge/Contributions-{total}-blue)")
    console.print(f"![PRs](https://img.shields.io/badge/PRs-{prs}-green)")
    console.print(f"![Repos](https://img.shields.io/badge/Repos-{repos}-orange)")


@cli.command()
@click.argument("repo")
def repo(repo):
    """Show stats for a specific repo."""
    fetcher = StatsFetcher("")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Fetching stats for {repo}...", total=None)
        stats = fetcher.fetch_repo_stats(repo)
        progress.update(task, completed=True)

    if not stats:
        console.print(f"[yellow]Repo {repo} not found.[/yellow]")
        return

    console.print(Panel(
        f"[bold]{repo}[/bold]\n"
        f"⭐ {_format_number(stats['stars'])} | "
        f"🍴 {_format_number(stats['forks'])} | "
        f"🐛 {_format_number(stats['open_issues'])}\n"
        f"Lang: [cyan]{stats['language']}[/cyan]",
        title="Repo Stats"
    ))

    if stats.get("description"):
        console.print(f"\n[dim]{stats['description']}[/dim]")
