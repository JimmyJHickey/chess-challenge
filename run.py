import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from profile_scraper import ProfileScraper

json_path = "users.json"
with open(json_path, 'r') as file:
    users_data = json.load(file)

for user in users_data:

    my_scraper = ProfileScraper(
        profile_url = user["profile_url"],
        user_name = user["user_name"], 
        csv_path = f"elos.csv"
    )
    my_scraper.run()


# ---------- config ----------
START_DATE = pd.Timestamp("2026-11-10")   # left edge of the plots
END_DATE = pd.Timestamp("2026-12-31")     # right edge of the plots
TIMEZONE = "America/New_York"             # defines where one "day" ends
OUT_DIR = Path("../../jimmyjhickey.com/")                    # GitHub Pages can serve /docs
PLOTS_SUB_DIR = "img/chess"

# Hovering a legend entry highlights that line (Plotly has no built-in for this)
HIGHLIGHT_JS = """
var gd = document.getElementById('{plot_id}');
function setHL(idx) {
  var n = gd.data.length, op = [], w = [];
  for (var j = 0; j < n; j++) {
    op.push(idx === null || j === idx ? 1 : 0.12);
    w.push(idx !== null && j === idx ? 4 : 2);
  }
  Plotly.restyle(gd, {opacity: op, 'line.width': w});
}
function bindLegend() {
  gd.querySelectorAll('.legend .traces').forEach(function (el, i) {
    if (el.__hl) return;
    el.__hl = true;
    el.addEventListener('mouseenter', function () { setHL(i); });
    el.addEventListener('mouseleave', function () { setHL(null); });
  });
}
gd.on('plotly_afterplot', bindLegend);
bindLegend();
"""

# ---------- load ----------
users = json.load(open("users.json"))
names = [u["user_name"] for u in users]
starting = pd.Series({u["user_name"]: u["starting_elo"] for u in users})

df = pd.read_csv("elos.csv")
# map either Lichess handle or display name -> display name
alias = {}
for u in users:
    handle = u["profile_url"].rstrip("/").split("/")[-1]
    alias[handle.lower()] = u["user_name"]
    alias[u["user_name"].lower()] = u["user_name"]

df["user_name"] = (
    df["user_name"].str.strip().str.lower().map(alias).fillna(df["user_name"])
)

df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")

bad = df["scraped_at"].isna()
if bad.any():
    print("Dropping %d row(s) with unparseable timestamps:" % bad.sum())
    print(df[bad].to_string())
df = df[~bad]

unknown = ~df["user_name"].isin(names)
if unknown.any():
    print("Ignoring rows for users not in users.json:", df.loc[unknown, "user_name"].unique())
df = df[~unknown]

# Timestamps are assumed to be UTC (naive); convert so days roll over at local midnight
df["date"] = (
    df["scraped_at"].dt.tz_localize("UTC").dt.tz_convert(TIMEZONE)
    .dt.normalize().dt.tz_localize(None)
)

# ---------- per-day tables ----------
# End-of-day elo = last scrape of each day
eod = (
    df.sort_values("scraped_at")
    .groupby(["date", "user_name"])["elo"].last()
    .unstack("user_name")
    .reindex(columns=names)
)
days = pd.date_range(min(START_DATE, eod.index.min()), max(START_DATE, eod.index.max()))
eod = eod.reindex(days).ffill()
eod = eod.fillna(starting)            # players with no data yet sit at their starting elo

prev = eod.shift(1)
prev.iloc[0] = starting
daily_gain = eod - prev               # change vs. previous day's close
cum_gain = eod - starting

# ---------- summary stats ----------
current = eod.iloc[-1]
total_gain = int((current - starting).sum())

stacked = daily_gain.stack()
best_day, worst_day = stacked.idxmax(), stacked.idxmin()
best_amt, worst_amt = int(stacked.max()), int(stacked.min())

standings = pd.DataFrame({
    "name": names,
    "gain": [int(current[n] - starting[n]) for n in names],
    "current": [int(current[n]) for n in names],
}).sort_values("gain", ascending=False)
standings["rank"] = standings["gain"].rank(method="min", ascending=False).astype(int)

def fmt(n):
    return "%+d" % n

# piece for each rank, strongest first (falls back to a pawn past 6th)
PIECES = ["♔", "♕", "♖", "♗", "♘", "♙"]

def piece_for(rank):
    return PIECES[min(rank, len(PIECES)) - 1]

table = ["| Rank | Name | Gain | Current Elo |", "|---:|:---|---:|---:|"]
for r in standings.itertuples():
    table.append("| %s %d | %s | %s | %d |" % (piece_for(r.rank), r.rank, r.name, fmt(r.gain), r.current))

# ---------- plots ----------
colors = dict(zip(names, px.colors.qualitative.Plotly))

def make_plot(data, title, ytitle, path):
    fig = go.Figure()
    for n in names:
        fig.add_trace(go.Scatter(
            x=data.index, y=data[n], name=n, mode="lines+markers",
            line=dict(color=colors[n], width=2),
            hovertemplate="%{x|%b %d}: %{y:+d}<extra>" + n + "</extra>",
        ))
    fig.update_layout(
        title=title, xaxis_title="Date", yaxis_title=ytitle,
        xaxis=dict(range=[START_DATE, END_DATE]),
        hovermode="closest", template="plotly_white",
    )
    fig.write_html(str(path), include_plotlyjs="cdn", post_script=HIGHLIGHT_JS)

OUT_DIR.mkdir(exist_ok=True)
(OUT_DIR / PLOTS_SUB_DIR).mkdir(exist_ok=True)
make_plot(cum_gain, "", "Total Elo Change", OUT_DIR / PLOTS_SUB_DIR / "cumulative.html")
make_plot(daily_gain, "", "Daily Elo Change", OUT_DIR / PLOTS_SUB_DIR / "daily.html")

# ---------- markdown ----------
def day_str(ts):
    return ts.strftime("%b %d, %Y")

md = """---
layout: page
title: Chess
---

<style>
  /* This CSS only applies to this page */
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
    font-family: monospace;
  }

  th {
    border-bottom: 2px solid #4682B4;
    padding: 12px;
    text-align: left;
  }

  tr {
    border-bottom: 1px solid #4682B4;
  }

  td {
    padding: 12px;
    vertical-align: top;
  }

  /* Optional: removes the line from the very last row */
  tr:last-child {
    border-bottom: none;
  }

  .main-content img {
    max-width: 100%;
    height: auto;
  }
</style>

# Jimbo's All Level Chess Challenge 2026

_Last updated: @@UPDATED@@_

## Highlights

- **Total Elo gained (all players):** @@TOTAL@@
- **Best day:** @@BN@@ gained **@@BA@@** on @@BD@@
- **Worst day:** @@WN@@ lost **@@WA@@** on @@WD@@

## Standings

@@TABLE@@

## Total Elo Change

<iframe src="@@PLOTS_SUB_DIR@@/cumulative.html" width="100%" height="520" frameborder="0"></iframe>

## Daily Elo Change

<iframe src="@@PLOTS_SUB_DIR@@/daily.html" width="100%" height="520" frameborder="0"></iframe>
"""

values = {
    "@@UPDATED@@": pd.Timestamp.now(tz=TIMEZONE).strftime("%b %d, %Y %I:%M %p %Z"),
    "@@TOTAL@@": fmt(total_gain),
    "@@BN@@": str(best_day[1]),
    "@@BA@@": fmt(best_amt),
    "@@BD@@": day_str(best_day[0]),
    "@@WN@@": str(worst_day[1]),
    "@@WA@@": str(worst_amt),
    "@@WD@@": day_str(worst_day[0]),
    "@@TABLE@@": "\n".join(table),
    "@@PLOTS_SUB_DIR@@": PLOTS_SUB_DIR
}
for key, val in values.items():
    md = md.replace(key, val)

(OUT_DIR / "chess.md").write_text(md)
print(md)