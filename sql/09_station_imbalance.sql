-- 09_station_imbalance.sql
-- ROUTE OPTIMIZATION: net bike flow per station over the year.
--   net_outflow = departures - arrivals
--   * Large POSITIVE  -> more rides leave than arrive: the station tends to run
--     EMPTY and needs bikes trucked IN (a "source").
--   * Large NEGATIVE  -> more rides arrive than leave: the station tends to
--     fill up and needs bikes trucked OUT (a "sink").
-- net_outflow_pct normalizes the imbalance against the station's own volume so
-- small and large stations are comparable. Restricted to stations with enough
-- activity (>= 5,000 events) to be operationally meaningful.
WITH dep AS (
    SELECT start_station_name AS station, COUNT(*) AS departures
    FROM trips GROUP BY start_station_name
),
arr AS (
    SELECT end_station_name AS station, COUNT(*) AS arrivals
    FROM trips GROUP BY end_station_name
)
SELECT
    COALESCE(d.station, a.station)                          AS station,
    COALESCE(departures, 0)                                 AS departures,
    COALESCE(arrivals, 0)                                   AS arrivals,
    COALESCE(departures, 0) - COALESCE(arrivals, 0)         AS net_outflow,
    ROUND(
        100.0 * (COALESCE(departures, 0) - COALESCE(arrivals, 0))
        / NULLIF(COALESCE(departures, 0) + COALESCE(arrivals, 0), 0), 1
    )                                                       AS net_outflow_pct
FROM dep d
FULL OUTER JOIN arr a ON d.station = a.station
WHERE COALESCE(departures, 0) + COALESCE(arrivals, 0) >= 5000
ORDER BY net_outflow DESC
