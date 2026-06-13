-- 07_top_routes.sql
-- ROUTE ACTIVITY: the 25 busiest origin->destination station pairs, with how
-- commute-oriented each is (member share). High-volume routes are candidates
-- for guaranteed bike/dock availability.
SELECT
    route,
    start_station_name,
    end_station_name,
    COUNT(*)                                                          AS trips,
    ROUND(AVG(trip_duration_min), 2)                                 AS avg_duration_min,
    ROUND(AVG(trip_distance_km), 2)                                  AS avg_distance_km,
    ROUND(100.0 * AVG(CASE WHEN member_casual = 'member' THEN 1 ELSE 0 END), 1) AS member_pct
FROM trips
GROUP BY route, start_station_name, end_station_name
ORDER BY trips DESC
LIMIT 25
