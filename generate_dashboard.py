#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_HTML = ROOT / "dashboard.html"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_date(value: str) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_month(value: str) -> date:
    return datetime.strptime(value, "%Y-%m").date()


def currency(value: float) -> str:
    return f"${value:,.0f}"


def signed_currency(value: float) -> str:
    """Currency with an explicit sign, e.g. +$1,205,000 / -$3,615,000."""
    sign = "+" if value > 0 else ("-" if value < 0 else "")
    return f"{sign}${abs(value):,.0f}"


def pct(value: float, digits: int = 0) -> str:
    return f"{value:.{digits}f}%"


def days_text(value: int) -> str:
    if value == 0:
        return "On time"
    noun = "day" if abs(value) == 1 else "days"
    if value > 0:
        return f"{value} {noun} late"
    return f"{abs(value)} {noun} early"


def nice_max(value: float, ticks: int = 4) -> float:
    """Round the axis maximum up so each of the `ticks` gridlines lands on a clean number."""
    if value <= 0:
        return 1
    raw = value / ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for step in (1, 2, 2.5, 5, 10):
        if step * magnitude >= raw:
            return step * magnitude * ticks
    return 10 * magnitude * ticks


def metric_card(label: str, value: str, sublabel: str, tone: str = "default") -> str:
    return f"""
    <div class="metric-card {tone}">
      <div class="metric-label">{escape(label)}</div>
      <div class="metric-value">{escape(value)}</div>
      <div class="metric-sub">{escape(sublabel)}</div>
    </div>
    """


def status_pill(text: str, tone: str = "default") -> str:
    return f'<span class="pill {tone}">{escape(text)}</span>'


def section(title: str, subtitle: str, body: str) -> str:
    return f"""
    <section class="panel section">
      <div class="section-head">
        <div>
          <h2>{escape(title)}</h2>
          <p>{escape(subtitle)}</p>
        </div>
      </div>
      {body}
    </section>
    """


def svg_bar_chart(
    items: list[tuple[str, float]],
    width: int = 720,
    height: int = 280,
    color: str = "#0f766e",
    value_formatter=lambda v: f"{v:.0f}",
) -> str:
    if not items:
        return '<div class="empty-state">No data available.</div>'

    margin = {"top": 28, "right": 20, "bottom": 44, "left": 56}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    max_value = nice_max(max(v for _, v in items))
    bar_w = plot_w / max(len(items), 1) * 0.62
    gap = plot_w / max(len(items), 1) * 0.38

    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Bar chart">'
    ]

    for tick in range(5):
        y = margin["top"] + plot_h - (plot_h * tick / 4)
        value = max_value * tick / 4
        parts.append(
            f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width - margin["right"]}" y2="{y:.1f}" '
            'stroke="rgba(15,23,42,0.10)" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{margin["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis-label">'
            f"{escape(value_formatter(value))}</text>"
        )

    for idx, (label, value) in enumerate(items):
        x = margin["left"] + idx * (bar_w + gap) + gap / 2
        h = 0 if max_value == 0 else plot_h * (value / max_value)
        y = margin["top"] + plot_h - h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="8" fill="{color}" />'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="value-label">'
            f"{escape(value_formatter(value))}</text>"
        )
        # Horizontal category labels (the rotated version ran off the bottom of the SVG)
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{margin["top"] + plot_h + 22}" text-anchor="middle" '
            f'class="axis-label">{escape(label)}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def svg_multi_line_chart(
    series: list[tuple[str, list[float], str]],
    labels: list[str],
    width: int = 760,
    height: int = 300,
    value_formatter=lambda v: f"{v:.0f}",
) -> str:
    if not labels or not series:
        return '<div class="empty-state">No data available.</div>'

    margin = {"top": 24, "right": 24, "bottom": 56, "left": 64}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    all_values = [v for _, values, _ in series for v in values if v is not None]
    max_value = max(all_values) if all_values else 1
    max_value = nice_max(max_value)
    step_x = plot_w / max(len(labels) - 1, 1)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="chart-svg" role="img" aria-label="Line chart">'
    ]

    for tick in range(5):
        y = margin["top"] + plot_h - (plot_h * tick / 4)
        value = max_value * tick / 4
        parts.append(
            f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width - margin["right"]}" y2="{y:.1f}" '
            'stroke="rgba(15,23,42,0.10)" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{margin["left"] - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis-label">'
            f"{escape(value_formatter(value))}</text>"
        )

    for idx, label in enumerate(labels):
        x = margin["left"] + idx * step_x
        parts.append(
            f'<text x="{x:.1f}" y="{height - 18}" text-anchor="middle" class="axis-label">{escape(label)}</text>'
        )

    for name, values, color in series:
        # Months with no data (None) are skipped, so actuals stop at the status date
        # instead of dropping to zero.
        points = []
        for idx, value in enumerate(values):
            if value is None:
                continue
            x = margin["left"] + idx * step_x
            y = margin["top"] + plot_h - (plot_h * value / max_value)
            points.append((x, y, value, labels[idx]))
        path = " ".join(
            ("M" if idx == 0 else "L") + f" {x:.1f} {y:.1f}" for idx, (x, y, _, _) in enumerate(points)
        )
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />'
        )
        for x, y, value, label in points:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{color}">'
                f"<title>{escape(name)} · {escape(label)}: {escape(value_formatter(value))}</title></circle>"
            )

    legend = "".join(
        f'<div class="legend-item"><span class="legend-dot" style="background:{color}"></span>{escape(name)}</div>'
        for name, _, color in series
    )
    parts.append("</svg>")
    return f'<div class="chart-wrap">{"".join(parts)}<div class="legend">{legend}</div></div>'


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = []
        for cell in row:
            # keep ISO dates and short numeric values on one line
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}|[-+$\d,.%]+( (days|pts|hrs))?( late| early)?", str(cell)):
                cell = f'<span class="nowrap">{cell}</span>'
            cells.append(f"<td>{cell}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    if not body_rows:
        body_rows.append('<tr><td colspan="99" class="muted">No rows to display.</td></tr>')
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    """


def render() -> str:
    metadata = read_json(DATA_DIR / "project_metadata.json")
    schedule = read_csv(DATA_DIR / "schedule.csv")
    cash_flow = read_csv(DATA_DIR / "cash_flow.csv")
    progress = read_csv(DATA_DIR / "progress.csv")
    risks = read_csv(DATA_DIR / "risks.csv")
    changes = read_csv(DATA_DIR / "change_orders.csv")
    weather = read_csv(DATA_DIR / "weather_delays.csv")

    status_date = parse_date(metadata["status_date"])
    baseline_finish = parse_date(metadata["baseline_finish"])

    for row in schedule:
        row["baseline_start_dt"] = parse_date(row["baseline_start"])
        row["baseline_finish_dt"] = parse_date(row["baseline_finish"])
        row["actual_start_dt"] = parse_date(row["actual_start"])
        row["forecast_finish_dt"] = parse_date(row["forecast_finish"])
        row["budget"] = float(row["budget_usd"])
        row["percent"] = float(row["percent_complete"])
        row["baseline_percent"] = float(row["baseline_percent_complete"])
        row["is_critical"] = row["critical_flag"].strip().lower() == "yes"
        row["slip_days"] = (
            (row["forecast_finish_dt"] - row["baseline_finish_dt"]).days
            if row["forecast_finish_dt"] and row["baseline_finish_dt"]
            else 0
        )
        row["progress_delta"] = row["percent"] - row["baseline_percent"]

    total_budget = sum(row["budget"] for row in schedule) or 1
    weighted_complete = sum(row["budget"] * row["percent"] for row in schedule) / total_budget
    weighted_plan = sum(row["budget"] * row["baseline_percent"] for row in schedule) / total_budget
    forecast_project_finish = max(row["forecast_finish_dt"] for row in schedule if row["forecast_finish_dt"])
    project_slip_days = (forecast_project_finish - baseline_finish).days if baseline_finish else 0

    # FIX: compare like with like. Planned, actual and paid are summed only through the
    # status month. (The first version summed planned cost for all 12 months against
    # 8 months of actuals, which made an over-budget project look 17% under budget.)
    status_month = status_date.replace(day=1)
    to_date = [row for row in cash_flow if parse_month(row["month"]) <= status_month]
    actual_cost_to_date = sum(float(row["actual_cost_usd"]) for row in to_date)
    planned_cost_to_date = sum(float(row["planned_cost_usd"]) for row in to_date)
    invoice_paid_to_date = sum(float(row["invoice_paid_usd"]) for row in to_date)
    # Commitments and total plan cover the full cash flow horizon (budget at completion).
    planned_cost_total = sum(float(row["planned_cost_usd"]) for row in cash_flow)
    committed_cost_to_date = sum(float(row["committed_cost_usd"]) for row in cash_flow)

    approved_changes = [row for row in changes if row["status"].strip().lower() == "approved"]
    pending_changes = [row for row in changes if row["status"].strip().lower() == "pending"]
    approved_change_value = sum(float(row["value_usd"]) for row in approved_changes)
    pending_change_value = sum(float(row["value_usd"]) for row in pending_changes)

    high_risks = [row for row in risks if row["severity"].strip().lower() == "high"]
    open_high_risks = [row for row in high_risks if row["status"].strip().lower() in {"open", "mitigating"}]
    severity_counts = Counter(row["severity"] for row in risks)
    risk_owner_counts = Counter(row["owner"] for row in risks)

    weather_rows = []
    weather_hours_by_month = defaultdict(float)
    for row in weather:
        dt = parse_date(row["date"])
        lost_hours = float(row["lost_hours"])
        weather_rows.append((dt, row["event"], lost_hours, row["notes"]))
        weather_hours_by_month[dt.strftime("%b")] += lost_hours

    critical_tasks = [row for row in schedule if row["is_critical"]]
    delayed_tasks = sorted(
        [row for row in schedule if row["slip_days"] > 0],
        key=lambda r: (r["slip_days"], r["forecast_finish_dt"]),
        reverse=True,
    )
    late_critical = [row for row in critical_tasks if row["slip_days"] > 0]
    severe_delays = [row for row in delayed_tasks if row["slip_days"] >= 14]
    cost_overrun = actual_cost_to_date - planned_cost_to_date
    cost_overrun_pct = (cost_overrun / planned_cost_to_date * 100) if planned_cost_to_date else 0
    committed_overrun = committed_cost_to_date - planned_cost_total
    committed_overrun_pct = (committed_overrun / planned_cost_total * 100) if planned_cost_total else 0
    over_budget = cost_overrun > 0 or committed_overrun > 0
    log_change_total = approved_change_value
    metadata_change_total = float(metadata["approved_change_orders_usd"])
    change_mismatch = metadata_change_total - log_change_total

    milestones = sorted(
        [row for row in schedule if row["is_critical"]],
        key=lambda r: r["baseline_finish_dt"] or date.min,
    )[-5:]

    latest_progress_date = max(parse_date(row["reporting_date"]) for row in progress)
    latest_progress = [row for row in progress if parse_date(row["reporting_date"]) == latest_progress_date]
    latest_progress.sort(key=lambda r: float(r["actual_progress_pct"]) - float(r["planned_progress_pct"]))

    cost_labels = [parse_month(row["month"]).strftime("%b") for row in cash_flow]
    planned_series = [float(row["planned_cost_usd"]) / 1_000_000 for row in cash_flow]
    def upto_status(row, key):
        return float(row[key]) / 1_000_000 if parse_month(row["month"]) <= status_month else None

    actual_series = [upto_status(row, "actual_cost_usd") for row in cash_flow]
    committed_series = [float(row["committed_cost_usd"]) / 1_000_000 for row in cash_flow]
    paid_series = [upto_status(row, "invoice_paid_usd") for row in cash_flow]

    pending_age_rows = []
    for row in pending_changes:
        submitted = parse_date(row["submitted_date"])
        age_days = (status_date - submitted).days if status_date and submitted else None
        pending_age_rows.append((age_days or 0, row, submitted))
    pending_age_rows.sort(reverse=True, key=lambda item: item[0])

    section_intro = f"""
    <div class="hero panel">
      <div class="hero-copy">
        <div class="eyebrow">Static Local Dashboard</div>
        <h1>{escape(metadata['project_name'])}</h1>
        <p>{escape(metadata['project_type'])}</p>
        <div class="hero-meta">
          <span><strong>Owner:</strong> {escape(metadata['owner'])}</span>
          <span><strong>Contractor:</strong> {escape(metadata['contractor'])}</span>
          <span><strong>Location:</strong> {escape(metadata['location'])}</span>
          <span><strong>Status Date:</strong> {status_date.strftime('%b %d, %Y')}</span>
        </div>
      </div>
      <div class="hero-side">
        <div class="hero-stat">
          <div class="hero-stat-label">Current Contract</div>
          <div class="hero-stat-value">{currency(metadata['contract_value_usd'] + approved_change_value)}</div>
        </div>
        <div class="hero-stat">
          <div class="hero-stat-label">Remaining Contingency</div>
          <div class="hero-stat-value">{currency(metadata['contingency_usd'])}</div>
        </div>
      </div>
    </div>
    """

    summary_section = f"""
    <section class="panel summary-band">
      <div class="summary-intro">
        <div class="eyebrow">Summary</div>
        <h2>Project Snapshot</h2>
        <p>
          The project is currently at <strong>{pct(weighted_complete, 1)}</strong> complete against a planned
          <strong>{pct(weighted_plan, 1)}</strong>. The latest forecast finish is
          <strong>{forecast_project_finish.strftime("%b %d, %Y")}</strong>, which is
          <strong>{days_text(project_slip_days)}</strong> relative to baseline.
          Actual spend through the status date is <strong>{currency(actual_cost_to_date)}</strong>, or
          <strong>{currency(abs(cost_overrun))}</strong> ({pct(abs(cost_overrun_pct), 1)})
          {"over" if cost_overrun > 0 else "under"} the planned {currency(planned_cost_to_date)}.
          Total commitments of <strong>{currency(committed_cost_to_date)}</strong> are
          {currency(abs(committed_overrun))} {"above" if committed_overrun > 0 else "below"} the total planned budget.
        </p>
      </div>
      <div class="summary-alerts">
        <div class="alert-card {'alert-warn' if severe_delays else 'alert-good'}">
          <div class="alert-title">Delayed Activities</div>
          <div class="alert-value">{len(delayed_tasks)}</div>
          <div class="alert-sub">{len(severe_delays)} with slips of 14 days or more</div>
        </div>
        <div class="alert-card {'alert-danger' if over_budget else 'alert-good'}">
          <div class="alert-title">Cost Position (to date)</div>
          <div class="alert-value">{signed_currency(cost_overrun)}</div>
          <div class="alert-sub">{pct(abs(cost_overrun_pct), 1)} {"over" if cost_overrun > 0 else "under"} plan through {status_date.strftime("%b %Y")}</div>
        </div>
      </div>
    </section>
    """

    executive_cards = "".join(
        [
            metric_card(
                "Percent Complete",
                pct(weighted_complete, 1),
                f"Plan was {pct(weighted_plan, 1)}",
                "accent",
            ),
            metric_card(
                "Forecast Finish",
                forecast_project_finish.strftime("%b %d, %Y"),
                f"{days_text(project_slip_days)} vs baseline",
                "warn" if project_slip_days > 0 else "good",
            ),
            metric_card(
                "Cost To Date",
                currency(actual_cost_to_date),
                f"{currency(committed_cost_to_date)} committed",
            ),
            metric_card(
                "Approved Changes",
                currency(approved_change_value),
                f"{len(approved_changes)} approved items",
            ),
            metric_card(
                "Open High Risks",
                str(len(open_high_risks)),
                f"{len(high_risks)} high-severity risks total",
                "warn" if open_high_risks else "good",
            ),
        ]
    )

    critical_status = f"""
    <div class="metrics-grid tight">
      {metric_card("Critical Tasks", str(len(critical_tasks)), f"{len(late_critical)} currently slipping")}
      {metric_card("Delayed Tasks", str(len(delayed_tasks)), "Forecast later than baseline", "warn" if delayed_tasks else "good")}
      {metric_card("Longest Task Slip", days_text(max((row['slip_days'] for row in delayed_tasks), default=0)), f"{len(severe_delays)} severe delays highlighted", "warn" if severe_delays else "default")}
    </div>
    """

    delayed_rows = [
        [
            escape(row["task_id"]),
            escape(row["task_name"]),
            escape(row["discipline"]),
            status_pill(row["status"], "danger" if row["slip_days"] >= 14 else "warn"),
            escape(row["baseline_finish"]),
            escape(row["forecast_finish"]),
            status_pill(days_text(row["slip_days"]), "danger" if row["slip_days"] >= 14 else "warn"),
        ]
        for row in delayed_tasks[:8]
    ]

    milestone_rows = [
        [
            escape(row["task_id"]),
            escape(row["task_name"]),
            escape(row["baseline_finish"]),
            escape(row["forecast_finish"]),
            escape(days_text(row["slip_days"])),
        ]
        for row in milestones
    ]

    discipline_rows = [
        [
            escape(row["discipline"]),
            pct(float(row["planned_progress_pct"]), 0),
            pct(float(row["actual_progress_pct"]), 0),
            f"{float(row['actual_progress_pct']) - float(row['planned_progress_pct']):+.0f} pts",
        ]
        for row in latest_progress
    ]
    discipline_chart = svg_bar_chart(
        [(row["discipline"], float(row["actual_progress_pct"])) for row in latest_progress],
        color="#0f766e",
        value_formatter=lambda v: f"{v:.0f}%",
    )

    cost_cards = f"""
    <div class="metrics-grid tight four">
      {metric_card("Planned To Date", currency(planned_cost_to_date), f"Through {status_date.strftime('%b %Y')} · {currency(planned_cost_total)} total plan")}
      {metric_card("Actual To Date", currency(actual_cost_to_date), f"{signed_currency(cost_overrun)} vs plan", "warn" if cost_overrun > 0 else "good")}
      {metric_card("Total Committed", currency(committed_cost_to_date), f"{signed_currency(committed_overrun)} vs total plan", "warn" if committed_overrun > 0 else "good")}
      {metric_card("Invoices Paid", currency(invoice_paid_to_date), f"{currency(actual_cost_to_date - invoice_paid_to_date)} incurred, not yet paid")}
    </div>
    """
    cost_chart = svg_multi_line_chart(
        [
            ("Planned", planned_series, "#2563eb"),
            ("Actual", actual_series, "#dc2626"),
            ("Committed", committed_series, "#0f766e"),
            ("Paid", paid_series, "#ca8a04"),
        ],
        cost_labels,
        value_formatter=lambda v: f"${v:.1f}M",
    )

    overspend_callout = f"""
    <div class="overspend-callout {'danger' if over_budget else 'good'}">
      <div>
        <div class="overspend-label">Budget Status</div>
        <div class="overspend-value">{currency(abs(cost_overrun))} {"Over" if cost_overrun > 0 else "Under"} Plan To Date</div>
      </div>
      <div class="overspend-sub">
        Actual spend is {pct(abs(cost_overrun_pct), 1)} {"above" if cost_overrun > 0 else "below"} plan through the status date, and total commitments are {pct(abs(committed_overrun_pct), 1)} {"above" if committed_overrun > 0 else "below"} the total planned budget.
      </div>
    </div>
    """

    change_cards = f"""
    <div class="metrics-grid tight">
      {metric_card("Approved COs", str(len(approved_changes)), currency(approved_change_value))}
      {metric_card("Pending COs", str(len(pending_changes)), currency(pending_change_value), "warn" if pending_changes else "good")}
      {metric_card("Metadata Check", "Mismatch" if change_mismatch else "Reconciled", f"Metadata {currency(metadata_change_total)} vs CO log {currency(log_change_total)}" + (f" ({signed_currency(change_mismatch)})" if change_mismatch else ""), "warn" if change_mismatch else "good")}
    </div>
    """
    change_status_chart = svg_bar_chart(
        [("Approved", approved_change_value), ("Pending", pending_change_value)],
        color="#b45309",
        value_formatter=lambda v: f"${v/1_000_000:.2f}M",
    )

    pending_rows = [
        [
            escape(row["co_id"]),
            escape(row["description"]),
            currency(float(row["value_usd"])),
            submitted.strftime("%b %d, %Y") if submitted else "",
            f"{age_days} days" if age_days is not None else "",
        ]
        for age_days, row, submitted in pending_age_rows
    ]

    risk_cards = f"""
    <div class="metrics-grid tight">
      {metric_card("Open Risks", str(sum(1 for row in risks if row['status'].strip().lower() in {'open', 'mitigating'})), "Items needing active management")}
      {metric_card("High Severity", str(severity_counts.get('High', 0)), "Across the full risk register", "warn" if severity_counts.get('High', 0) else "good")}
      {metric_card("Weather Lost Hours", f"{sum(hours for _, _, hours, _ in weather_rows):.0f} hrs", f"{len(weather_rows)} logged events")}
    </div>
    """
    severity_chart = svg_bar_chart(
        [(label, count) for label, count in severity_counts.items()],
        color="#7c3aed",
        value_formatter=lambda v: f"{v:.0f}",
    )
    weather_chart = svg_bar_chart(
        list(weather_hours_by_month.items()),
        color="#0369a1",
        value_formatter=lambda v: f"{v:.0f}h",
    )

    owner_rows = [
        [escape(owner), str(count)]
        for owner, count in risk_owner_counts.most_common()
    ]
    risk_rows = [
        [
            escape(row["risk_id"]),
            escape(row["category"]),
            escape(row["severity"]),
            escape(row["owner"]),
            escape(row["status"]),
            escape(row["mitigation"]),
        ]
        for row in risks
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(metadata['project_name'])} Dashboard</title>
  <style>
    :root {{
      --bg: #f6f3ed;
      --panel: rgba(255,255,255,0.86);
      --panel-border: rgba(15, 23, 42, 0.08);
      --text: #0f172a;
      --muted: #475569;
      --accent: #0f766e;
      --accent-soft: #ccfbf1;
      --warn: #b45309;
      --warn-soft: #ffedd5;
      --good: #166534;
      --good-soft: #dcfce7;
      --shadow: 0 24px 70px rgba(15, 23, 42, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(15,118,110,0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(180,83,9,0.12), transparent 28%),
        linear-gradient(180deg, #f4efe6 0%, #f8f7f3 52%, #eef5f4 100%);
    }}
    .page {{
      width: min(1380px, calc(100% - 40px));
      margin: 28px auto 56px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--panel-border);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.7fr 0.9fr;
      gap: 24px;
      padding: 28px;
      overflow: hidden;
      position: relative;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -40px -60px auto;
      width: 220px;
      height: 220px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(15,118,110,0.18), rgba(15,118,110,0));
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.76rem;
      color: var(--accent);
      font-weight: 700;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 3vw, 3.6rem);
      line-height: 0.98;
    }}
    h2 {{
      margin: 0 0 6px;
      font-size: 1.45rem;
    }}
    p {{
      margin: 0;
      color: var(--muted);
    }}
    .hero-copy p {{
      margin-top: 12px;
      font-size: 1.05rem;
      max-width: 60ch;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px 18px;
      margin-top: 22px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .hero-side {{
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .hero-stat {{
      padding: 18px 20px;
      border-radius: 20px;
      background: rgba(255,255,255,0.82);
      border: 1px solid rgba(15, 23, 42, 0.08);
    }}
    .hero-stat-label {{
      font-size: 0.86rem;
      color: var(--muted);
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .hero-stat-value {{
      font-size: 1.8rem;
      font-weight: 700;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 20px;
      margin-top: 24px;
    }}
    .metrics-grid.tight {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
      margin-top: 0;
    }}
    .metrics-grid.tight.four {{
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }}
    .metric-card {{
      padding: 22px 20px 18px;
      border-radius: 20px;
      background: rgba(255,255,255,0.78);
      border: 1px solid rgba(15, 23, 42, 0.08);
    }}
    .metric-card.accent {{
      background: linear-gradient(180deg, rgba(204,251,241,0.88), rgba(255,255,255,0.86));
    }}
    .metric-card.warn {{
      background: linear-gradient(180deg, rgba(255,237,213,0.96), rgba(255,255,255,0.88));
    }}
    .metric-card.good {{
      background: linear-gradient(180deg, rgba(220,252,231,0.96), rgba(255,255,255,0.88));
    }}
    .metric-label {{
      color: var(--muted);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }}
    .metric-value {{
      font-size: 1.8rem;
      font-weight: 800;
      line-height: 1;
      margin-bottom: 10px;
    }}
    .metric-sub {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .section {{
      margin-top: 24px;
      padding: 30px;
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      margin-bottom: 24px;
      gap: 12px;
    }}
    .summary-band {{
      margin-top: 24px;
      padding: 28px 30px;
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 24px;
      align-items: start;
    }}
    .summary-intro p {{
      margin-top: 12px;
      max-width: 70ch;
      line-height: 1.65;
      font-size: 1rem;
    }}
    .summary-alerts {{
      display: grid;
      gap: 16px;
    }}
    .alert-card {{
      padding: 18px 20px;
      border-radius: 20px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      background: rgba(255,255,255,0.78);
    }}
    .alert-warn {{
      background: linear-gradient(180deg, rgba(255,237,213,0.96), rgba(255,255,255,0.88));
    }}
    .alert-danger {{
      background: linear-gradient(180deg, rgba(254,226,226,0.96), rgba(255,255,255,0.88));
      border-color: rgba(220,38,38,0.16);
    }}
    .alert-good {{
      background: linear-gradient(180deg, rgba(220,252,231,0.96), rgba(255,255,255,0.88));
    }}
    .alert-title {{
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .alert-value {{
      font-size: 2rem;
      font-weight: 800;
      line-height: 1;
    }}
    .alert-sub {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 22px;
      align-items: start;
    }}
    .split.wide-left {{
      grid-template-columns: 1fr;
      margin-top: 18px;
    }}
    .subpanel {{
      padding: 22px;
      border-radius: 20px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(15, 23, 42, 0.08);
    }}
    .subpanel h3 {{
      margin: 0 0 14px;
      font-size: 1.05rem;
    }}
    .split > *, .metrics-grid > *, .summary-band > * {{
      min-width: 0;
    }}
    .chart-svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .axis-label {{
      font-size: 11px;
      fill: #64748b;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }}
    .value-label {{
      font-size: 11px;
      fill: #0f172a;
      font-weight: 600;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 16px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      display: inline-block;
    }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 18px;
      border: 1px solid rgba(15, 23, 42, 0.08);
      background: rgba(255,255,255,0.84);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 0;
    }}
    .nowrap {{
      white-space: nowrap;
    }}
    th, td {{
      padding: 11px 12px;
      font-size: 0.92rem;
      text-align: left;
      border-bottom: 1px solid rgba(15, 23, 42, 0.08);
      vertical-align: top;
    }}
    th {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      background: rgba(248,250,252,0.95);
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    .caption {{
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 0.94rem;
    }}
    .footer {{
      margin-top: 24px;
      padding: 20px 22px;
      color: var(--muted);
      font-size: 0.92rem;
      text-align: center;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.84rem;
      font-weight: 700;
      line-height: 1;
      white-space: nowrap;
    }}
    .pill.warn {{
      background: #ffedd5;
      color: #9a3412;
    }}
    .pill.danger {{
      background: #fee2e2;
      color: #b91c1c;
    }}
    .pill.default {{
      background: #e2e8f0;
      color: #334155;
    }}
    .overspend-callout {{
      margin-top: 22px;
      padding: 20px 22px;
      border-radius: 22px;
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: center;
      border: 1px solid rgba(15, 23, 42, 0.08);
    }}
    .overspend-callout.danger {{
      background: linear-gradient(90deg, rgba(220,38,38,0.12), rgba(255,255,255,0.90));
      border-color: rgba(220,38,38,0.18);
    }}
    .overspend-callout.good {{
      background: linear-gradient(90deg, rgba(22,163,74,0.12), rgba(255,255,255,0.90));
      border-color: rgba(22,163,74,0.16);
    }}
    .overspend-label {{
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 6px;
    }}
    .overspend-value {{
      font-size: 1.6rem;
      font-weight: 800;
    }}
    .overspend-sub {{
      color: var(--muted);
      max-width: 34ch;
      line-height: 1.5;
    }}
    .muted, .empty-state {{
      color: var(--muted);
    }}
    .empty-state {{
      padding: 20px;
    }}
    @media (max-width: 1100px) {{
      .metrics-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .metrics-grid.tight,
      .metrics-grid.tight.four,
      .split,
      .split.wide-left,
      .summary-band,
      .hero {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 700px) {{
      .page {{
        width: min(100% - 24px, 1380px);
      }}
      .metrics-grid {{
        grid-template-columns: 1fr;
      }}
      .section {{
        padding: 20px;
      }}
      .hero {{
        padding: 20px;
      }}
      .summary-band {{
        padding: 22px 20px;
      }}
      .overspend-callout {{
        flex-direction: column;
        align-items: start;
      }}
      .hero-stat-value, .metric-value {{
        font-size: 1.45rem;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    {section_intro}
    {summary_section}
    <section class="panel section">
      <div class="section-head">
        <div>
          <h2>Executive KPIs</h2>
          <p>Top-level schedule, cost, change, and risk indicators for the current reporting cut.</p>
        </div>
      </div>
      <div class="metrics-grid">{executive_cards}</div>
    </section>
    {section(
        "Schedule View",
        "Critical path health, delayed work, milestone movement, and discipline-level progress.",
        critical_status
        + '<div class="split wide-left">'
        + f'<div class="subpanel"><h3>Delayed Tasks</h3><div class="caption">Tasks where forecast finish is later than baseline finish.</div>{table(["Task", "Activity", "Discipline", "Status", "Baseline Finish", "Forecast Finish", "Slip"], delayed_rows)}</div>'
        + f'<div class="subpanel"><h3>Milestone Slippage</h3><div class="caption">Latest critical-path milestones and their current finish movement.</div>{table(["Task", "Milestone", "Baseline Finish", "Forecast Finish", "Slip"], milestone_rows)}</div>'
        + '</div>'
        + '<div class="split" style="margin-top:18px">'
        + f'<div class="subpanel"><h3>Discipline Progress</h3><div class="caption">Latest reported actual progress by discipline.</div>{discipline_chart}</div>'
        + f'<div class="subpanel"><h3>Progress Snapshot</h3><div class="caption">Planned versus actual discipline progress at {latest_progress_date.strftime("%b %d, %Y")}.</div>{table(["Discipline", "Planned", "Actual", "Variance"], discipline_rows)}</div>'
        + '</div>'
    )}
    {section(
        "Cost View",
        "Monthly spend, commitment exposure, and payment progress from the loaded cash flow file.",
        cost_cards
        + overspend_callout
        + f'<div class="subpanel" style="margin-top:22px"><h3>Monthly Cost Trend</h3><div class="caption">Monthly values in millions of dollars. Actual and paid lines stop at the status date; hover a point for its value.</div>{cost_chart}</div>'
    )}
    {section(
        "Change View",
        "Approved and pending change order activity with value and cycle-time visibility.",
        change_cards
        + '<div class="split" style="margin-top:18px">'
        + f'<div class="subpanel"><h3>Change Order Value By Status</h3><div class="caption">Dollar exposure by current change order status.</div>{change_status_chart}</div>'
        + f'<div class="subpanel"><h3>Pending Change Aging</h3><div class="caption">Age measured from submitted date to project status date.</div>{table(["CO ID", "Description", "Value", "Submitted", "Age"], pending_rows)}</div>'
        + '</div>'
    )}
    {section(
        "Risk And Delay View",
        "Open issues, severity distribution, weather delay impact, and mitigation accountability.",
        risk_cards
        + '<div class="split" style="margin-top:18px">'
        + f'<div class="subpanel"><h3>Risk Severity Mix</h3><div class="caption">Count of risks by overall severity rating.</div>{severity_chart}</div>'
        + f'<div class="subpanel"><h3>Weather Lost Hours</h3><div class="caption">Logged productive hours lost by month.</div>{weather_chart}</div>'
        + '</div>'
        + '<div class="split wide-left">'
        + f'<div class="subpanel"><h3>Mitigation Ownership</h3><div class="caption">Risk counts by assigned owner.</div>{table(["Owner", "Assigned Risks"], owner_rows)}</div>'
        + f'<div class="subpanel"><h3>Risk Register Snapshot</h3><div class="caption">Current risk details from the source register.</div>{table(["Risk", "Category", "Severity", "Owner", "Status", "Mitigation"], risk_rows)}</div>'
        + '</div>'
    )}
    <div class="panel footer">
      Generated locally from files in <code>./data</code> on {datetime.now().strftime("%b %d, %Y at %I:%M %p")}.
      No external services or remote assets are required.
    </div>
  </main>
</body>
</html>
"""
    return html


def main() -> None:
    OUTPUT_HTML.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
