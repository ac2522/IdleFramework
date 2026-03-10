"""IdleFramework CLI — validate, analyze, report, compare, export."""
from __future__ import annotations

import html
import json
from pathlib import Path

import typer

from idleframework.model.game import GameDefinition

app = typer.Typer(name="idleframework", help="Idle game balance analysis framework.")


def _load_game(game_file: str) -> GameDefinition:
    path = Path(game_file)
    if not path.exists():
        typer.echo(f"Error: File not found: {game_file}")
        raise typer.Exit(code=1)

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        typer.echo(f"Error: Invalid JSON: {e}")
        raise typer.Exit(code=1)
    except (OSError, UnicodeDecodeError) as e:
        typer.echo(f"Error: Could not read file '{game_file}': {e}")
        raise typer.Exit(code=1)

    try:
        game = GameDefinition(**data)
    except (ValueError, TypeError) as e:
        typer.echo(f"Error: Validation failed: {e}")
        raise typer.Exit(code=1)

    return game


@app.command()
def validate(game_file: str) -> None:
    game = _load_game(game_file)
    typer.echo(f"Valid game definition: {game.name}")
    typer.echo(f"  Nodes: {len(game.nodes)}")
    typer.echo(f"  Edges: {len(game.edges)}")
    typer.echo(f"  Stacking groups: {len(game.stacking_groups)}")


@app.command()
def analyze(game_file: str, time: float = 300.0) -> None:
    game = _load_game(game_file)

    from idleframework.analysis.detectors import run_full_analysis

    typer.echo(f"Analyzing '{game.name}' for {time}s...")
    report = run_full_analysis(game, simulation_time=time)

    typer.echo(f"\n=== Analysis Report: {report.game_name} ===")
    typer.echo(f"Simulation time: {report.simulation_time}s")

    typer.echo(f"\nDead upgrades: {len(report.dead_upgrades)}")
    for du in report.dead_upgrades:
        typer.echo(f"  - {du['upgrade_id']}: {du['reason']}")

    typer.echo(f"\nProgression walls: {len(report.progression_walls)}")
    for pw in report.progression_walls:
        typer.echo(f"  - {pw['reason']}")

    if report.dominant_strategy and report.dominant_strategy.get("dominant_gen"):
        typer.echo(f"\nDominant strategy: {report.dominant_strategy['dominant_gen']} "
                   f"(ratio: {report.dominant_strategy['ratio']:.1f}x)")
    else:
        typer.echo("\nNo dominant strategy detected.")

    if report.optimizer_result:
        opt = report.optimizer_result
        typer.echo("\nOptimizer result:")
        typer.echo(f"  Purchases: {len(opt.purchases)}")
        typer.echo(f"  Final production: {opt.final_production:.2e}")
        typer.echo(f"  Final balance: {opt.final_balance:.2e}")


@app.command()
def report(
    game_file: str,
    output: str = "report.html",
    cdn: bool = True,
    time: float = 300.0,
) -> None:
    game = _load_game(game_file)

    from idleframework.analysis.detectors import run_full_analysis

    typer.echo(f"Analyzing '{game.name}'...")
    analysis = run_full_analysis(game, simulation_time=time)

    html = _generate_html_report(analysis, cdn=cdn)
    Path(output).write_text(html)
    typer.echo(f"Report written to {output}")


def _generate_html_report(report, cdn: bool = True) -> str:
    opt = report.optimizer_result

    purchases_html = ""
    if opt and opt.purchases:
        rows = []
        for p in opt.purchases:
            rows.append(f"<tr><td>{p.time:.1f}s</td><td>{html.escape(str(p.node_id))}</td><td>{p.cost:.2e}</td></tr>")
        purchases_html = f"""
        <h2>Purchase Timeline</h2>
        <table border="1" cellpadding="4" cellspacing="0">
            <tr><th>Time</th><th>Node</th><th>Cost</th></tr>
            {"".join(rows)}
        </table>
        """

    dead_html = ""
    if report.dead_upgrades:
        items = "".join(f"<li>{html.escape(str(d['upgrade_id']))}: {html.escape(str(d['reason']))}</li>" for d in report.dead_upgrades)
        dead_html = f"<h2>Dead Upgrades</h2><ul>{items}</ul>"

    walls_html = ""
    if report.progression_walls:
        items = "".join(f"<li>{html.escape(str(w['reason']))}</li>" for w in report.progression_walls)
        walls_html = f"<h2>Progression Walls</h2><ul>{items}</ul>"

    dominant_html = ""
    if report.dominant_strategy and report.dominant_strategy.get("dominant_gen"):
        ds = report.dominant_strategy
        dominant_html = (
            f"<h2>Dominant Strategy</h2>"
            f"<p>{html.escape(str(ds['dominant_gen']))} dominates by {ds['ratio']:.1f}x</p>"
        )

    final_stats = ""
    if opt:
        final_stats = f"""
        <h2>Final Stats</h2>
        <ul>
            <li>Production: {opt.final_production:.2e}/s</li>
            <li>Balance: {opt.final_balance:.2e}</li>
            <li>Purchases: {len(opt.purchases)}</li>
        </ul>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>IdleFramework Report: {html.escape(str(report.game_name))}</title>
    <style>
        body {{ font-family: sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th {{ background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>Analysis Report: {html.escape(str(report.game_name))}</h1>
    <p>Simulation time: {report.simulation_time}s</p>
    {dead_html}
    {walls_html}
    {dominant_html}
    {final_stats}
    {purchases_html}
</body>
</html>"""


@app.command()
def compare(
    game_file: str,
    strategies: str = "free,paid",
    time: float = 300.0,
) -> None:
    game = _load_game(game_file)

    from idleframework.analysis.detectors import run_full_analysis

    tags = [t.strip() for t in strategies.split(",")]

    typer.echo(f"Running baseline analysis for '{game.name}'...")
    baseline = run_full_analysis(game, simulation_time=time)
    baseline_prod = baseline.optimizer_result.final_production if baseline.optimizer_result else 0

    typer.echo(f"\n=== Strategy Comparison: {game.name} ===\n")
    typer.echo(f"Baseline (all upgrades): {baseline_prod:.2e}/s")

    for tag in tags:
        variant = _exclude_tag(game, tag)
        variant_report = run_full_analysis(variant, simulation_time=time)
        variant_prod = variant_report.optimizer_result.final_production if variant_report.optimizer_result else 0

        ratio = baseline_prod / variant_prod if variant_prod > 0 else float("inf")
        typer.echo(f"\nWithout '{tag}' upgrades: {variant_prod:.2e}/s (baseline is {ratio:.1f}x)")

    typer.echo("\nFree strategy: excludes paid upgrades")
    typer.echo("Paid strategy: includes all upgrades (baseline)")


def _exclude_tag(game: GameDefinition, tag: str) -> GameDefinition:
    game_copy = game.model_copy(deep=True)
    excluded_ids = set()

    filtered_nodes = []
    for node in game_copy.nodes:
        if hasattr(node, "tags") and tag in node.tags and getattr(node, "type", "") == "upgrade":
            excluded_ids.add(node.id)
        else:
            filtered_nodes.append(node)

    game_copy.nodes = filtered_nodes
    game_copy.edges = [e for e in game_copy.edges if e.source not in excluded_ids and e.target not in excluded_ids]

    return game_copy


@app.command(name="export")
def export_cmd(
    game_file: str,
    format: str = "yaml",
) -> None:
    game = _load_game(game_file)

    from idleframework.export import to_yaml, to_xml

    fmt = format.lower()
    if fmt == "yaml":
        typer.echo(to_yaml(game))
    elif fmt == "xml":
        typer.echo(to_xml(game))
    else:
        typer.echo(f"Error: Unsupported format '{format}'. Use 'yaml' or 'xml'.")
        raise typer.Exit(code=1)
