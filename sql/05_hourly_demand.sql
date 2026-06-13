-- 05_hourly_demand.sql
-- TIME-OF-DAY DEMAND: trips by hour of day, split weekday vs. weekend.
-- Weekday demand is bimodal (AM + PM commute peaks); weekend demand is a
-- single midday hump. This is the backbone of the rebalancing schedule.
SELECT
    hour,
    SUM(CASE WHEN is_weekend = false THEN 1 ELSE 0 END) AS weekday_trips,
    SUM(CASE WHEN is_weekend = true  THEN 1 ELSE 0 END) AS weekend_trips,
    COUNT(*)                                            AS total_trips
FROM trips
GROUP BY hour
ORDER BY hour
