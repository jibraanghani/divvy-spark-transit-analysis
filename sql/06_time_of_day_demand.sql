-- 06_time_of_day_demand.sql
-- TIME-OF-DAY DEMAND: trips grouped into named dayparts, split by rider type.
-- Shows when each segment rides, ordered chronologically across the day.
SELECT
    time_of_day,
    member_casual,
    COUNT(*)                          AS trips,
    ROUND(AVG(trip_duration_min), 2)  AS avg_duration_min
FROM trips
GROUP BY time_of_day, member_casual
ORDER BY MIN(hour), member_casual
