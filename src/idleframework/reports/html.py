"""HTML report generator using Plotly for idle game analysis results."""
from __future__ import annotations

from collections import defaultdict
from html import escape

import plotly.graph_objects as go
import plotly.io as pio

from idleframework.analysis.detectors import AnalysisReport


def generate_report(
    report: AnalysisReport,
    *,
    use_cdn: bool = True,
    title: str | None = None,
) -> str:
    display_title = title or f"{report.game_name} Analysis Report"

    figures: list[str] = []

    opt = report.optimizer_result
    if opt is not None and opt.timeline:
        figures.append(_build_production_chart(opt.timeline))

    if opt is not None and opt.purchases:
        figures.append(_build_purchase_cost_chart(opt.purchases))
        gen_chart = _build_generator_count_chart(opt.purchases)
        if gen_chart:
            figures.append(gen_chart)

    plotlyjs_mode: str | bool = "cdn" if use_cdn else True

    chart_html_parts: list[str] = []
    for i, fig in enumerate(figures):
        include = plotlyjs_mode if i == 0 else False
        html_fragment = pio.to_html(fig, full_html=False, include_plotlyjs=include)
        chart_html_parts.append(html_fragment)

    charts_html = "\n".join(chart_html_parts)

    summary_html = _build_summary(report)

    return _wrap_html(display_title, report.game_name, summary_html, charts_html)


def _build_production_chart(timeline: list[dict]) -> go.Figure:
    times = [entry["time"] for entry in timeline]
    rates = [entry["production_rate"] for entry in timeline]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times,
        y=rates,
        mode="lines+markers",
        name="Production Rate",
    ))
    fig.update_layout(
        title="Production Rate Over Time",
        xaxis_title="Time (s)",
        yaxis_title="Rate",
    )
    return fig


def _build_purchase_cost_chart(purchases: list) -> go.Figure:
    cost_by_node: dict[str, float] = defaultdict(float)
    for p in purchases:
        cost_by_node[p.node_id] += p.cost

    nodes = list(cost_by_node.keys())
    costs = [cost_by_node[n] for n in nodes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=nodes,
        y=costs,
        name="Total Cost",
    ))
    fig.update_layout(
        title="Purchase Cost Distribution",
        xaxis_title="Node",
        yaxis_title="Total Cost",
    )
    return fig


def _build_generator_count_chart(purchases: list) -> go.Figure | None:
    count_by_node: dict[str, int] = defaultdict(int)
    for p in purchases:
        count_by_node[p.node_id] += p.count

    if not count_by_node:
        return None

    nodes = list(count_by_node.keys())
    counts = [count_by_node[n] for n in nodes]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=nodes,
        y=counts,
        name="Purchase Count",
    ))
    fig.update_layout(
        title="Generator Purchase Breakdown",
        xaxis_title="Node",
        yaxis_title="Count",
    )
    return fig


def _build_summary(report: AnalysisReport) -> str:
    parts: list[str] = []

    parts.append(f"<p><strong>Simulation time:</strong> {report.simulation_time:.1f}s</p>")
    parts.append(
        "<p><strong>Approximation level:</strong> greedy (single-pass heuristic, "
        "not guaranteed optimal)</p>"
    )

    opt = report.optimizer_result
    if opt is not None:
        parts.append(f"<p><strong>Final production rate:</strong> {opt.final_production:.2f}</p>")
        parts.append(f"<p><strong>Final balance:</strong> {opt.final_balance:.2f}</p>")
        parts.append(f"<p><strong>Total purchases:</strong> {len(opt.purchases)}</p>")

    if report.dead_upgrades:
        parts.append(f"<p><strong>Dead upgrades found:</strong> {len(report.dead_upgrades)}</p>")
        parts.append("<ul>")
        for du in report.dead_upgrades:
            parts.append(
                f"<li>{escape(du['upgrade_id'])}: "
                f"{escape(du.get('reason', 'N/A'))}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p><strong>Dead upgrades:</strong> None detected</p>")

    if report.progression_walls:
        wall_count = len(report.progression_walls)
        parts.append(
            f"<p><strong>Progression walls found:</strong> {wall_count}</p>"
        )
        parts.append("<ul>")
        for pw in report.progression_walls:
            parts.append(f"<li>{escape(pw.get('reason', 'N/A'))}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p><strong>Progression walls:</strong> None detected</p>")

    dom = report.dominant_strategy
    if dom and dom.get("dominant_gen"):
        parts.append(
            f"<p><strong>Dominant strategy:</strong> {escape(dom['dominant_gen'])} "
            f"(ratio: {dom['ratio']:.1f}x)</p>"
        )

    return "\n".join(parts)


def _wrap_html(title: str, game_name: str, summary_html: str, charts_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #fafafa;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{
            background: #fff; padding: 20px; border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 30px;
        }}
        .chart {{ margin-bottom: 30px; }}
        footer {{ text-align: center; color: #999; margin-top: 40px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{escape(title)}</h1>
    <p>Game: <strong>{escape(game_name)}</strong></p>

    <h2>Summary</h2>
    <div class="summary">
        {summary_html}
    </div>

    <h2>Charts</h2>
    <div class="chart">
        {charts_html}
    </div>

    <footer>
        Generated by IdleFramework Report Generator
    </footer>
</body>
</html>"""
