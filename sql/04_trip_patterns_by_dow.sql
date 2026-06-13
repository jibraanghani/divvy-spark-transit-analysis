-- 04_trip_patterns_by_dow.sql
-- TRIP PATTERNS: demand and trip character by day of week. Weekends show
-- fewer but longer trips (leisure); weekdays show commute behavior.
SELECT
    day_of_week,
    is_weekend,
    COUNT(*)                              AS trips,
    ROUND(AVG(trip_duration_min), 2)      AS avg_duration_min,
    ROUND(AVG(trip_distance_km), 2)       AS avg_distance_km
FROM trips
GROUP BY day_of_week, is_weekend
ORDER BY CASE day_of_week
    WHEN 'Monday'    THEN 1
    WHEN 'Tuesday'   THEN 2
    WHEN 'Wednesday' THEN 3
    WHEN 'Thursday'  THEN 4
    WHEN 'Friday'    THEN 5
    WHEN 'Saturday'  THEN 6
    WHEN 'Sunday'    THEN 7
END
