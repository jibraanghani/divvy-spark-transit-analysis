-- 10_seasonal_demand.sql
-- TIME-OF-DAY / SEASONAL DEMAND: trips by meteorological season, with the
-- casual-rider share. Summer not only has far more trips but a higher share of
-- casual (visitor / leisure) riders, which shifts where demand concentrates.
SELECT
    season,
    COUNT(*)                                                          AS trips,
    ROUND(AVG(trip_duration_min), 2)                                 AS avg_duration_min,
    ROUND(AVG(trip_distance_km), 2)                                  AS avg_distance_km,
    ROUND(100.0 * AVG(CASE WHEN member_casual = 'casual' THEN 1 ELSE 0 END), 1) AS casual_pct
FROM trips
GROUP BY season
ORDER BY MIN(MONTH(started_at))
