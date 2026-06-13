"""
04_visualize.py  --  Stage 4: VISUALIZE
========================================
Read the CSV summaries produced by Stage 3 and render charts into
output/figures/. These figures are embedded in the README and the
recommendations report.

Run it with:
    python src/04_visualize.py
"""

import sys
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # render to files, no interactive window needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

plt.rcParams.update({
    "figure.dpi": 120,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
})

OUT = config.OUTPUT_DIR
FIG = config.FIGURES_DIR

# Brand-ish palette
BLUE, ORANGE, GREEN, RED = "#2b6cb0", "#dd6b20", "#2f855a", "#c53030"


def _read(name):
    return pd.read_csv(OUT / f"{name}.csv")


def _save(fig, name):
    path = FIG / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path.relative_to(config.BASE_DIR)}")


def chart_monthly_volume():
    df = _read("01_monthly_volume")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df["trip_month"], df["member_trips"], label="Member", color=BLUE)
    ax.bar(df["trip_month"], df["casual_trips"], bottom=df["member_trips"],
           label="Casual", color=ORANGE)
    ax.set_title("Monthly Divvy Trips by Rider Type (2024)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Trips")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    _save(fig, "monthly_volume")


def chart_hourly_demand():
    df = _read("05_hourly_demand").sort_values("hour")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["hour"], df["weekday_trips"], marker="o", label="Weekday",
            color=BLUE)
    ax.plot(df["hour"], df["weekend_trips"], marker="o", label="Weekend",
            color=ORANGE)
    ax.axvspan(6, 9, alpha=0.08, color=BLUE)
    ax.axvspan(16, 19, alpha=0.08, color=BLUE)
    ax.set_title("Demand by Hour of Day: Weekday vs. Weekend")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Trips")
    ax.set_xticks(range(0, 24, 2))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    ax.legend()
    _save(fig, "hourly_demand")


def chart_seasonal():
    df = _read("10_seasonal_demand")
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(df["season"], df["trips"], color=[BLUE, GREEN, ORANGE, RED])
    ax.set_title("Trips by Season (2024)")
    ax.set_ylabel("Trips")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    for b, v, c in zip(bars, df["trips"], df["casual_pct"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{c:.0f}% casual",
                ha="center", va="bottom", fontsize=9)
    _save(fig, "seasonal_demand")


def chart_member_vs_casual():
    df = _read("03_member_vs_casual").set_index("member_casual")
    metrics = ["avg_duration_min", "median_duration_min", "avg_distance_km",
               "round_trip_pct"]
    labels = ["Avg duration\n(min)", "Median duration\n(min)",
              "Avg distance\n(km)", "Round-trip\n(%)"]
    x = range(len(metrics))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - w/2 for i in x], df.loc["member", metrics], width=w,
           label="Member", color=BLUE)
    ax.bar([i + w/2 for i in x], df.loc["casual", metrics], width=w,
           label="Casual", color=ORANGE)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_title("Trip Patterns: Member vs. Casual Riders")
    ax.legend()
    _save(fig, "member_vs_casual")


def chart_top_stations():
    df = _read("08_top_stations").head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(df["station"], df["total_activity"], color=BLUE)
    ax.set_title("Top 15 Stations by Total Activity (departures + arrivals)")
    ax.set_xlabel("Total trips")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    _save(fig, "top_stations")


def chart_station_imbalance():
    df = _read("09_station_imbalance")
    sources = df.head(10)                      # most positive net_outflow
    sinks = df.tail(10).iloc[::-1]             # most negative net_outflow
    combo = pd.concat([sinks, sources])
    colors = [RED if v > 0 else GREEN for v in combo["net_outflow"]]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(combo["station"], combo["net_outflow"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Station Imbalance: Net Bike Outflow over 2024\n"
                 "(red = drains empty, needs bikes IN; "
                 "green = fills up, needs bikes OUT)")
    ax.set_xlabel("Net outflow  (departures − arrivals)")
    _save(fig, "station_imbalance")


def main():
    print("=" * 70)
    print("STAGE 4: VISUALIZE  --  rendering charts to output/figures/")
    print("=" * 70)
    chart_monthly_volume()
    chart_hourly_demand()
    chart_seasonal()
    chart_member_vs_casual()
    chart_top_stations()
    chart_station_imbalance()
    print("-" * 70)
    print("Stage 4 complete.")


if __name__ == "__main__":
    main()
