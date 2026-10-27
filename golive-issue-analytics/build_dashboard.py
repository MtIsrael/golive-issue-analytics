"""
Build dashboard/index.html, a self-contained go-live command center dashboard,
from golive.db. Open the file in any browser (charts load Chart.js from a CDN).

Usage:
    python build_dashboard.py
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent
CATEGORIES = ["Printing", "Login / Access", "Hardware / Device",
              "Workflow / Training", "Application / Build", "Interface"]


def q(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    con = sqlite3.connect(ROOT / "golive.db")
    live = "go_live_day >= 1"

    kpi = q(con, f"""
        SELECT COUNT(*) AS total,
               ROUND(100.0 * SUM(resolved_at_elbow) / COUNT(*), 1) AS elbow_pct,
               (SELECT ROUND(100.0 * SUM(CASE WHEN (julianday(resolved_dt) - julianday(created_dt)) * 24 <= s.target_hours THEN 1 ELSE 0 END) / COUNT(*), 1)
                  FROM tickets t JOIN sla_targets s ON s.priority = t.priority
                 WHERE t.status = 'Resolved' AND t.{live} AND t.priority IN ('P1', 'P2')) AS p1p2_sla_pct,
               (SELECT MAX(c) FROM (SELECT COUNT(*) c FROM tickets WHERE {live} GROUP BY go_live_day)) AS peak_day
        FROM tickets WHERE {live}""")[0]

    days = [r["go_live_day"] for r in q(con, "SELECT DISTINCT go_live_day FROM tickets ORDER BY go_live_day")]
    volume = {c: [] for c in CATEGORIES}
    for c in CATEGORIES:
        counts = {r["go_live_day"]: r["n"] for r in q(con, f"""
            SELECT go_live_day, COUNT(*) n FROM tickets WHERE category = '{c}' GROUP BY go_live_day""")}
        volume[c] = [counts.get(d, 0) for d in days]

    tdr = q(con, (ROOT / "queries" / "05_tdr_vs_golive_tickets.sql").read_text(encoding="utf-8"))
    elbow = q(con, (ROOT / "queries" / "04_at_elbow_resolution.sql").read_text(encoding="utf-8"))
    backlog = q(con, (ROOT / "queries" / "08_open_backlog_by_day.sql").read_text(encoding="utf-8"))
    shift = q(con, (ROOT / "queries" / "07_day_vs_night_shift.sql").read_text(encoding="utf-8"))
    offenders = q(con, (ROOT / "queries" / "06_repeat_offender_devices.sql").read_text(encoding="utf-8"))[:10]
    con.close()

    data = {
        "kpi": kpi, "days": days, "volume": volume, "tdr": tdr, "elbow": elbow,
        "backlog": backlog, "shift": shift, "offenders": offenders,
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(data))
    out = ROOT / "dashboard" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written: {out.relative_to(ROOT)}")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Go-Live Command Center</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root {
  color-scheme: light;
  --bg: #f4f3f0; --surface: #fcfcfb; --border: #e3e1dc;
  --text: #0b0b0b; --text-2: #52514e; --muted: #7a7974; --grid: #ebe9e4;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a; --s4: #eda100; --s5: #e87ba4; --s6: #008300;
  --good: #0ca30c; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --bg: #111110; --surface: #1a1a19; --border: #2e2e2b;
    --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86; --grid: #2a2a27;
    --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #111110; --surface: #1a1a19; --border: #2e2e2b;
  --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86; --grid: #2a2a27;
  --s1: #3987e5; --s2: #d95926; --s3: #199e70; --s4: #c98500; --s5: #d55181; --s6: #008300;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.45 "IBM Plex Sans", system-ui, sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 28px 16px 48px; }
header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
h1 { font-size: 22px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }
.sub { color: var(--text-2); margin: 4px 0 0; }
.tag { font: 500 12px "IBM Plex Mono", monospace; color: var(--muted); border: 1px solid var(--border); border-radius: 999px; padding: 4px 10px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px; }
.kpi, .card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; }
.kpi { padding: 16px; }
.kpi .label { color: var(--text-2); font-size: 12.5px; }
.kpi .value { font: 500 30px/1.15 "IBM Plex Mono", monospace; margin-top: 6px; letter-spacing: -0.02em; }
.kpi .note { color: var(--muted); font-size: 12px; margin-top: 2px; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.card { padding: 16px 16px 12px; min-width: 0; }
.card.wide { grid-column: 1 / -1; }
.card h2 { font-size: 14.5px; font-weight: 600; margin: 0; }
.card p.take { color: var(--text-2); margin: 3px 0 12px; font-size: 13px; }
.chart { position: relative; height: 260px; }
.card.wide .chart { height: 300px; }
details { margin-top: 10px; color: var(--text-2); font-size: 12.5px; }
summary { cursor: pointer; }
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; margin-top: 8px; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { color: var(--text-2); font-weight: 500; }
td.num, th.num { text-align: right; font-family: "IBM Plex Mono", monospace; }
.status { display: inline-flex; align-items: center; gap: 5px; }
.status svg { flex: none; }
footer { color: var(--muted); font-size: 12px; margin-top: 18px; }
@media (max-width: 760px) {
  .kpis { grid-template-columns: repeat(2, 1fr); }
  .grid { grid-template-columns: 1fr; }
  .kpi .value { font-size: 24px; }
}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Go-Live Command Center</h1>
      <p class="sub">Northbridge Regional Medical Center · Epic go-live support tickets</p>
    </div>
    <span class="tag">Synthetic data · Day −7 to Day 14</span>
  </header>

  <section class="kpis" id="kpis"></section>

  <section class="grid">
    <div class="card wide">
      <h2>Tickets by go-live day and category</h2>
      <p class="take" id="take-volume"></p>
      <div class="chart"><canvas id="volume" role="img" aria-label="Stacked bar chart of tickets per go-live day by category"></canvas></div>
      <details><summary>Show data table</summary><div class="tbl-wrap" id="volume-table"></div></details>
    </div>
    <div class="card">
      <h2>Tickets per device by TDR result</h2>
      <p class="take" id="take-tdr"></p>
      <div class="chart"><canvas id="tdr" role="img" aria-label="Bar chart of go-live tickets per device by TDR status"></canvas></div>
    </div>
    <div class="card">
      <h2>Share resolved at the elbow</h2>
      <p class="take" id="take-elbow"></p>
      <div class="chart"><canvas id="elbow" role="img" aria-label="Bar chart of percent of tickets fixed at the elbow by category"></canvas></div>
    </div>
    <div class="card">
      <h2>Open backlog at end of day</h2>
      <p class="take" id="take-backlog"></p>
      <div class="chart"><canvas id="backlog" role="img" aria-label="Line chart of open tickets at the end of each go-live day"></canvas></div>
    </div>
    <div class="card">
      <h2>Hours to resolve, day vs night shift</h2>
      <p class="take" id="take-shift"></p>
      <div class="chart"><canvas id="shift" role="img" aria-label="Grouped bar chart of average resolution hours by priority and shift"></canvas></div>
    </div>
    <div class="card wide">
      <h2>Repeat-offender devices</h2>
      <p class="take">Devices with the most go-live tickets: candidates for swap-out or re-mapping.</p>
      <div class="tbl-wrap" id="offenders"></div>
    </div>
  </section>
  <footer>All data is synthetic, generated for a portfolio project. Built with SQLite, Python, and Chart.js.</footer>
</main>

<script>
const D = __DATA__;
const CATS = ["Printing", "Login / Access", "Hardware / Device", "Workflow / Training", "Application / Build", "Interface"];
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt = n => Number(n).toLocaleString();
const charts = [];

// ---- KPI tiles ----
const k = D.kpi;
const live = D.backlog;
document.getElementById("kpis").innerHTML = [
  ["Go-live tickets", fmt(k.total), "Days 1–14"],
  ["Peak day", fmt(k.peak_day), "Go-live day 1"],
  ["Fixed at the elbow", k.elbow_pct + "%", "No escalation needed"],
  ["P1/P2 met SLA", k.p1p2_sla_pct + "%", "Targets: P1 1h · P2 4h"],
].map(([l, v, n]) => `<div class="kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="note">${n}</div></div>`).join("");

// ---- takeaways (computed from the data, not hard-coded) ----
const dayIdx = D.days.indexOf(1);
const tech = ["Printing", "Login / Access", "Hardware / Device"];
const sumRange = (cats, from, to) => cats.reduce((s, c) => s + D.volume[c].slice(from, to).reduce((a, b) => a + b, 0), 0);
const techShare = (from, to) => Math.round(100 * sumRange(tech, from, to) / sumRange(CATS, from, to));
document.getElementById("take-volume").textContent =
  `Printing, login, and hardware made up ${techShare(dayIdx, dayIdx + 3)}% of tickets in days 1–3, falling to ${techShare(dayIdx + 7, D.days.length)}% in week 2 as workflow questions took over.`;
const tdrPass = D.tdr.find(r => r.tdr_status === "Pass"), tdrNot = D.tdr.find(r => r.tdr_status === "Not retested");
document.getElementById("take-tdr").textContent =
  `Devices never retested after failing TDR averaged ${tdrNot.tickets_per_device} tickets each, ${(tdrNot.tickets_per_device / tdrPass.tickets_per_device).toFixed(1)}× the rate of devices that passed.`;
const wf = D.elbow.find(r => r.category === "Workflow / Training");
document.getElementById("take-elbow").textContent =
  `ATE resolved ${wf.at_elbow_pct}% of workflow issues on the spot in about ${Math.round(wf.elbow_avg_minutes)} minutes; escalated tickets took hours.`;
const peak = live.reduce((a, b) => b.open_at_end_of_day > a.open_at_end_of_day ? b : a);
document.getElementById("take-backlog").textContent =
  `Backlog peaked at ${peak.open_at_end_of_day} open tickets on day ${peak.go_live_day} and fell to ${live[live.length - 1].open_at_end_of_day} by day ${live[live.length - 1].go_live_day}; build requests are the slowest to clear.`;
const p2d = D.shift.find(r => r.shift === "Day" && r.priority === "P2"), p2n = D.shift.find(r => r.shift === "Night" && r.priority === "P2");
document.getElementById("take-shift").textContent =
  `Night tickets take longer at every priority: P2s averaged ${p2n.avg_hours_to_resolve}h overnight vs ${p2d.avg_hours_to_resolve}h on days.`;

// ---- data table for the stacked chart (contrast relief) ----
document.getElementById("volume-table").innerHTML =
  `<table><thead><tr><th>Day</th>${CATS.map(c => `<th class="num">${c}</th>`).join("")}<th class="num">Total</th></tr></thead><tbody>` +
  D.days.map((d, i) => `<tr><td>${d}</td>${CATS.map(c => `<td class="num">${D.volume[c][i]}</td>`).join("")}<td class="num">${CATS.reduce((s, c) => s + D.volume[c][i], 0)}</td></tr>`).join("") +
  `</tbody></table>`;

// ---- repeat offenders table with TDR status icon + label ----
const statusCell = s => {
  const bad = s === "Not retested" || s === "Failed retest";
  const color = bad ? "var(--critical)" : "var(--good)";
  const icon = bad
    ? `<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 1 11 10H1z" fill="${color}"/></svg>`
    : `<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="5" fill="${color}"/></svg>`;
  return `<span class="status">${icon}${s}</span>`;
};
document.getElementById("offenders").innerHTML =
  `<table><thead><tr><th>Device</th><th>Type</th><th>Department</th><th>TDR result</th><th class="num">Tickets</th><th>Issues reported</th></tr></thead><tbody>` +
  D.offenders.map(o => `<tr><td>${o.device_name}</td><td>${o.device_type}</td><td>${o.department}</td><td>${statusCell(o.tdr_status)}</td><td class="num">${o.golive_tickets}</td><td>${o.issues_reported.split(",").join(", ")}</td></tr>`).join("") +
  `</tbody></table>`;

// ---- charts ----
function base(extra = {}) {
  return {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "top", align: "start", labels: { color: css("--text-2"), boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: 2, font: { size: 12 } } },
      tooltip: { backgroundColor: css("--text"), titleColor: css("--surface"), bodyColor: css("--surface"), padding: 10, cornerRadius: 6, titleFont: { weight: "600" } },
    },
    scales: {
      x: { grid: { display: false }, border: { color: css("--border") }, ticks: { color: css("--muted"), font: { size: 11 } } },
      y: { beginAtZero: true, grid: { color: css("--grid") }, border: { display: false }, ticks: { color: css("--muted"), font: { size: 11 } } },
    },
    ...extra,
  };
}
const series = i => css(`--s${i + 1}`);

function draw() {
  Chart.defaults.font.family = '"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif';
  charts.splice(0).forEach(c => c.destroy());
  const surface = css("--surface");

  const vol = base();
  vol.scales.x.stacked = true; vol.scales.y.stacked = true;
  vol.scales.x.ticks.maxRotation = 0;
  vol.scales.x.title = { display: true, text: "Go-live day (negative = days before go-live)", color: css("--muted"), font: { size: 11 } };
  charts.push(new Chart(document.getElementById("volume"), {
    type: "bar",
    data: { labels: D.days, datasets: CATS.map((c, i) => ({ label: c, data: D.volume[c], backgroundColor: series(i), borderColor: surface, borderWidth: { top: 2 }, borderSkipped: false, borderRadius: 0, maxBarThickness: 34 })) },
    options: vol,
  }));

  const one = (id, labels, values, opts = {}, unit = "") => {
    const o = base(); o.plugins.legend.display = false;
    if (opts.horizontal) { o.indexAxis = "y"; o.scales.x.grid = { color: css("--grid") }; o.scales.y.grid = { display: false }; }
    if (opts.max) (opts.horizontal ? o.scales.x : o.scales.y).max = opts.max;
    if (unit.startsWith("%")) (opts.horizontal ? o.scales.x : o.scales.y).ticks.callback = v => v + "%";
    o.plugins.tooltip.callbacks = { label: c => ` ${c.formattedValue}${unit}` };
    charts.push(new Chart(document.getElementById(id), {
      type: "bar",
      data: { labels, datasets: [{ data: values, backgroundColor: series(0), borderRadius: 4, maxBarThickness: 28 }] },
      options: o,
    }));
  };
  one("tdr", D.tdr.map(r => r.tdr_status), D.tdr.map(r => r.tickets_per_device), { horizontal: true }, " tickets / device");
  one("elbow", D.elbow.map(r => r.category), D.elbow.map(r => r.at_elbow_pct), { horizontal: true, max: 100 }, "% at elbow");

  const bl = base(); bl.plugins.legend.display = false;
  bl.scales.x.title = { display: true, text: "Go-live day", color: css("--muted"), font: { size: 11 } };
  charts.push(new Chart(document.getElementById("backlog"), {
    type: "line",
    data: { labels: D.backlog.map(r => r.go_live_day), datasets: [{ label: "Open tickets", data: D.backlog.map(r => r.open_at_end_of_day), borderColor: series(0), backgroundColor: series(0), borderWidth: 2, pointRadius: 3, pointHoverRadius: 6, pointBorderColor: surface, pointBorderWidth: 2, tension: 0.25 }] },
    options: bl,
  }));

  const pr = ["P1", "P2", "P3", "P4"];
  const sh = base();
  charts.push(new Chart(document.getElementById("shift"), {
    type: "bar",
    data: { labels: pr, datasets: ["Day", "Night"].map((s, i) => ({ label: s + " shift", data: pr.map(p => (D.shift.find(r => r.shift === s && r.priority === p) || {}).avg_hours_to_resolve), backgroundColor: series(i), borderRadius: 4, borderColor: surface, borderWidth: 1, maxBarThickness: 28 })) },
    options: { ...sh, plugins: { ...sh.plugins, tooltip: { ...sh.plugins.tooltip, callbacks: { label: c => ` ${c.dataset.label}: ${c.formattedValue} h` } } } },
  }));
}
draw();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
new MutationObserver(draw).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
