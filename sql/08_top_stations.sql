-- 08_top_stations.sql
-- ROUTE ACTIVITY: the 25 busiest stations by total activity (departures plus
-- arrivals). These are the network's high-traffic hubs.
SELECT
    station,
    SUM(departures)               AS departures,
    SUM(arrivals)                 AS arrivals,
    SUM(departures + arrivals)    AS total_activity
FROM (
    SELECT start_station_name AS station, COUNT(*) AS departures, 0 AS arrivals
    FROM trips GROUP BY start_station_name
    UNION ALL
    SELECT end_station_name   AS station, 0 AS departures, COUNT(*) AS arrivals
    FROM trips GROUP BY end_station_name
)
GROUP BY station
ORDER BY total_activity DESC
LIMIT 25
