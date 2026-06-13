-- 02_usage_by_bike_type.sql
-- BIKE USAGE: how classic vs. electric bikes are used, broken out by rider
-- type, with each segment's share of all trips.
SELECT
    rideable_type,
    member_casual,
    COUNT(*)                                              AS trips,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)    AS pct_of_all_trips,
    ROUND(AVG(trip_duration_min), 2)                      AS avg_duration_min,
    ROUND(AVG(trip_distance_km), 2)                       AS avg_distance_km
FROM trips
GROUP BY rideable_type, member_casual
ORDER BY trips DESC
