"""
05_analyze_on_s3.py  --  Run Spark SQL directly against Amazon S3
=================================================================
Demonstrates the cloud path: instead of reading the curated Parquet from the
local disk, Spark reads it straight from the project's S3 bucket over the
s3a:// connector and runs the same SQL analytics.

This is the exact code that would run on an Amazon EMR / Glue cluster; the only
difference there is that the driver runs in AWS instead of on a laptop.

Prerequisites:
    * AWS credentials configured locally (`aws configure`), and
    * the curated Parquet already uploaded (see src/upload_to_s3.py).

Run it with:
    python src/05_analyze_on_s3.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def main():
    print("=" * 70)
    print("ANALYZE ON S3  --  Spark SQL over s3a://")
    print(f"  reading: {config.S3_CURATED_URI}")
    print("=" * 70)

    spark = config.get_spark_s3("divvy-analyze-on-s3")

    # Read the curated Parquet directly from Amazon S3.
    trips = spark.read.parquet(config.S3_CURATED_URI)
    trips.createOrReplaceTempView("trips")
    print(f"Rows read from S3: {trips.count():,}\n")

    print("- Monthly trip volume (from S3):")
    spark.sql("""
        SELECT trip_month, COUNT(*) AS trips
        FROM trips
        GROUP BY trip_month
        ORDER BY trip_month
    """).show(12, truncate=False)

    print("- Top 5 stations that drain empty (need bikes trucked in):")
    spark.sql("""
        WITH dep AS (
            SELECT start_station_name AS station, COUNT(*) AS departures
            FROM trips GROUP BY start_station_name
        ),
        arr AS (
            SELECT end_station_name AS station, COUNT(*) AS arrivals
            FROM trips GROUP BY end_station_name
        )
        SELECT d.station,
               departures - arrivals AS net_outflow
        FROM dep d JOIN arr a ON d.station = a.station
        WHERE departures + arrivals >= 5000
        ORDER BY net_outflow DESC
        LIMIT 5
    """).show(truncate=False)

    spark.stop()
    print("Done — analytics ran against data stored in Amazon S3.")


if __name__ == "__main__":
    main()
