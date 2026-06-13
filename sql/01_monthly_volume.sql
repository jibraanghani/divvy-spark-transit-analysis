-- 01_monthly_volume.sql
-- BIKE USAGE: total trips per month, split by rider type, with average trip
-- length. Reveals the strong seasonal demand curve across the year.
SELECT
    trip_month,
    COUNT(*)                                                   AS trips,
    SUM(CASE WHEN member_casual = 'member' THEN 1 ELSE 0 END)  AS member_trips,
    SUM(CASE WHEN member_casual = 'casual' THEN 1 ELSE 0 END)  AS casual_trips,
    ROUND(AVG(trip_duration_min), 2)                           AS avg_duration_min
FROM trips
GROUP BY trip_month
ORDER BY trip_month
