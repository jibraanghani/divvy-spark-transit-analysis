# Divvy Route Optimization — Findings & Recommendations

**Scope:** 4,168,072 cleaned Divvy trips, January–December 2024 (Chicago).
**Method:** Apache Spark cleaning pipeline + Spark SQL analysis (see `sql/`).

This memo translates the analysis in `output/` into operational recommendations
for the three levers a bike-share operator actually controls: where bikes are
positioned (rebalancing), when crews and capacity are deployed, and **how
the network is grown and marketed.

---

## 1. Key findings

### 1.1 Demand is highly seasonal — plan capacity as a curve, not a constant
| Season | Trips | Avg duration (min) | Casual share |
|--------|------:|-------------------:|-------------:|
| Winter | 422,992 | 12.6 | 19.6% |
| Spring | 953,283 | 17.0 | 33.4% |
| Summer | 1,566,740 | 18.8 | 42.4% |
| Fall   | 1,225,057 | 15.4 | 36.0% |

Summer carries 3.7× the volume of winter, and the rider mix shifts toward
casual (leisure/visitor) riders, who take longer trips concentrated on the
lakefront. Peak month (August, 537,903 trips) is 4.8× the trough (January,
110,874).

### 1.2 Weekday demand is a sharp double commute peak
Weekday usage is bimodal: a **7–9 AM** peak (8 AM ≈ 209K trips for the year) and
a larger **4–6 PM** peak (5 PM ≈ 348K trips). Weekends are unimodal — a broad
**11 AM–3 PM** plateau. (`output/figures/hourly_demand.png`)

### 1.3 Two distinct customer segments
| Segment | Share | Avg duration | Median duration | Round-trip % |
|---------|------:|-------------:|----------------:|-------------:|
| Member  | 63.9% | 12.6 min | 8.9 min | 2.4% |
| Casual  | 36.1% | 24.2 min | 13.6 min | 8.6% |

Members behave like commuters: short, direct, point-to-point trips that cluster
in the peaks. Casual riders take **~2× longer** trips, far more **round trips**,
and skew to midday and weekends.

### 1.4 Activity concentrates on a small set of stations
The top 15 stations account for a disproportionate share of all activity, led by
**Streeter Dr & Grand Ave** (124,917 events — Navy Pier), the **DuSable Lake
Shore Dr** corridor, and **Michigan Ave & Oak St**. (`output/figures/top_stations.png`)

### 1.5 Predictable structural imbalance — the core optimization opportunity
Net annual outflow (departures − arrivals) reveals systematic one-way flow:

**Stations that drain empty (need bikes trucked IN):**
| Station | Net outflow |
|---------|------------:|
| Buckingham Fountain | +3,027 |
| Columbus Dr & Randolph St | +2,856 |
| Desplaines St & Kinzie St | +2,236 |
| Field Museum | +2,114 |
| Adler Planetarium | +2,111 |

**Stations that pile up (need bikes trucked OUT):**
| Station | Net outflow |
|---------|------------:|
| DuSable Lake Shore Dr & North Blvd | −3,570 |
| Sheffield Ave & Waveland Ave | −3,400 |
| Streeter Dr & Grand Ave | −1,604 |
| Sangamon St & Lake St | −1,548 |

The pattern is geographic and intuitive: museum-campus and downtown-core
stations shed bikes; lakefront/neighborhood destinations (North Ave Beach,
Wrigleyville) absorb them. Because the imbalance is **stable and directional**,
it can be scheduled rather than chased reactively. (`output/figures/station_imbalance.png`)

---

## 2. Recommendations

### R1 — Run a scheduled, directional rebalancing route (not reactive top-ups)
Operate a fixed daily "trunk" rebalancing loop that moves bikes **from net-sink
stations to net-source stations** along the strongest flow corridors
(e.g., North Ave Beach / Wrigleyville → museum campus & downtown core).
Size the route from the net-outflow table in `output/09_station_imbalance.csv`;
the top ~20 imbalanced stations capture most of the correctable deficit.

### R2 — Pre-position before peaks, on a weekday vs. weekend split schedule
Complete the heaviest rebalancing **before 7 AM** (ahead of the AM commute) and
again **early afternoon** (ahead of the 4–6 PM peak). Run a **separate weekend
plan** centered on the 11 AM–3 PM lakefront leisure plateau, since weekend demand
geography and timing differ from weekday commuting.

### R3 — Add dock capacity at chronically saturated sinks
Stations that consistently fill up (North Ave Beach, Sheffield & Waveland) lose
rides when full ("dock blocking"). Expanding dock count or adding overflow
corrals at the top sink stations reduces failed returns and lowers the
rebalancing burden created by R1.

### R4 — Protect commuter reliability on the top member routes
The highest member-share routes (e.g., the University of Chicago corridor,
Calumet/State at 33rd St, >90% members) are commute-critical. Guarantee
AM/PM bike-and-dock availability on these origin→destination pairs
(`output/07_top_routes.csv`); commuters churn fastest when reliability slips.

### R5 — Convert lakefront casual demand into memberships
Casual demand is concentrated, seasonal, and lakefront-anchored (Streeter Dr,
museum campus). Target **summer weekend day-pass riders at these specific
stations** with membership upsell — the data pinpoints exactly where and when
the convertible audience is riding.

### R6 — Scale operations to the seasonal curve
Staff, fleet deployment, and maintenance throughput should track the 3.7×
summer-to-winter swing rather than an annual average — over-provisioning in
winter wastes cost, under-provisioning in summer caps revenue and degrades
service during the highest-demand months.

---

## 3. Limitations & next steps
- **Dockless e-bike trips without a named station (~28% of raw records) were
  excluded** to keep station/route analysis consistent; a follow-up using the
  raw GPS could map demand for those trips to virtual zones.
- Imbalance here is **annual net flow**; the same query partitioned by
  `time_of_day` would yield an intraday rebalancing schedule (a natural next
  iteration of R2).
- Weather and special-event data (Cubs games near Sheffield & Waveland; festival
  days on the lakefront) would sharpen day-level forecasts.
