-- 03_member_vs_casual.sql
-- TRIP PATTERNS: contrast the two rider segments. Members take many short,
-- direct (commute-like) trips; casual riders take fewer, longer, more
-- leisure-oriented trips. Drives audience-specific recommendations.
SELECT
    member_casual,
    COUNT(*)                                                       AS trips,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)             AS pct_share,
    ROUND(AVG(trip_duration_min), 2)                              AS avg_duration_min,
    ROUND(percentile_approx(trip_duration_min, 0.5), 2)          AS median_duration_min,
    ROUND(AVG(trip_distance_km), 2)                              AS avg_distance_km,
    ROUND(100.0 * AVG(CASE WHEN is_round_trip THEN 1 ELSE 0 END), 2) AS round_trip_pct
FROM trips
GROUP BY member_casual
ORDER BY trips DESC
