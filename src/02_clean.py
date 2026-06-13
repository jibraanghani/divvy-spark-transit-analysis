"""
02_clean.py  --  Stage 2: CLEAN  (Apache Spark)
===============================================
Read every monthly CSV from the raw zone, apply data-quality rules, derive the
analytical columns we need downstream, and write the result to the curated zone
as partitioned Parquet.

Run it with:
    python src/02_clean.py

Design notes
------------
* We declare an explicit schema instead of letting Spark infer it. Inference
  requires an extra full pass over the data and can guess types wrong; an
  explicit schema is faster and deterministic.
* Each filter step prints how many rows it removed, producing a small
  data-quality report that documents exactly how the dataset was cleaned.
* Output is written as Parquet partitioned by `trip_month`, so the analysis
  stage only scans the partitions it needs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
)

# ---------------------------------------------------------------------------
# Raw Divvy schema. Station ids are alphanumeric, so they are strings. We read
# the timestamps as strings and parse them explicitly below for full control.
# ---------------------------------------------------------------------------
RAW_SCHEMA = StructType([
    StructField("ride_id", StringType()),
    StructField("rideable_type", StringType()),
    StructField("started_at", StringType()),
    StructField("ended_at", StringType()),
    StructField("start_station_name", StringType()),
    StructField("start_station_id", StringType()),
    StructField("end_station_name", StringType()),
    StructField("end_station_id", StringType()),
    StructField("start_lat", DoubleType()),
    StructField("start_lng", DoubleType()),
    StructField("end_lat", DoubleType()),
    StructField("end_lng", DoubleType()),
    StructField("member_casual", StringType()),
])

# Geographic bounding box for the Chicago service area. Anything outside this is
# a GPS error and gets dropped.
CHI_LAT_MIN, CHI_LAT_MAX = 41.60, 42.10
CHI_LNG_MIN, CHI_LNG_MAX = -87.95, -87.50

TS_FORMAT = "yyyy-MM-dd HH:mm:ss"


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance (km) between two points, as a Spark column expr.

    Accepts either column names (str) or Column objects for each coordinate.
    """
    # Promote any string arguments to Spark Columns so arithmetic works.
    lat1, lng1, lat2, lng2 = (
        F.col(c) if isinstance(c, str) else c for c in (lat1, lng1, lat2, lng2)
    )
    r = 6371.0  # Earth radius in km
    dlat = F.radians(lat2 - lat1)
    dlng = F.radians(lng2 - lng1)
    a = (F.sin(dlat / 2) ** 2
         + F.cos(F.radians(lat1)) * F.cos(F.radians(lat2)) * F.sin(dlng / 2) ** 2)
    return r * 2 * F.asin(F.sqrt(a))


def main():
    spark = config.get_spark("divvy-clean")

    print("=" * 70)
    print("STAGE 2: CLEAN  --  Spark data-quality pipeline")
    print("=" * 70)

    # Read all monthly CSVs in one shot. Spark treats the folder of CSVs as a
    # single logical table and parallelizes the read across CPU cores.
    raw = (
        spark.read
        .option("header", True)
        .schema(RAW_SCHEMA)
        .csv(str(config.RAW_DIR / "*-divvy-tripdata.csv"))
    )

    n_raw = raw.count()
    print(f"Rows read from raw zone: {n_raw:,}")

    # --- Parse timestamps and derive duration ------------------------------
    # Most rows look like "2024-01-12 15:30:27", but a subset carries
    # fractional seconds ("...:27.403"). We don't need sub-second precision, so
    # we trim every value to its first 19 characters before parsing. This makes
    # the parse deterministic regardless of which format a given row uses.
    df = (
        raw
        .withColumn("started_at",
                    F.to_timestamp(F.substring("started_at", 1, 19), TS_FORMAT))
        .withColumn("ended_at",
                    F.to_timestamp(F.substring("ended_at", 1, 19), TS_FORMAT))
    )
    df = df.withColumn(
        "trip_duration_min",
        (F.col("ended_at").cast("long") - F.col("started_at").cast("long")) / 60.0,
    )

    # --- Sequential cleaning rules; report the row count after each ---------
    def step(frame, label):
        n = frame.count()
        print(f"  after {label:<32} {n:>10,} rows "
              f"({n_raw - n:,} removed so far)")
        return frame

    # 1. Drop rows missing any field essential to the analysis.
    df = df.dropna(subset=[
        "ride_id", "started_at", "ended_at",
        "start_station_name", "end_station_name",
        "start_lat", "start_lng", "end_lat", "end_lng",
        "member_casual", "rideable_type",
    ])
    df = step(df, "drop missing essentials")

    # 2. Remove duplicate ride_ids (keep the first occurrence).
    df = df.dropDuplicates(["ride_id"])
    df = step(df, "drop duplicate ride_ids")

    # 3. Keep only realistic trip durations: > 1 minute and < 24 hours.
    #    Sub-minute trips are false starts; multi-day trips are undocked bikes.
    df = df.filter((F.col("trip_duration_min") > 1) &
                   (F.col("trip_duration_min") < 1440))
    df = step(df, "filter trip duration 1min-24h")

    # 4. Keep only GPS coordinates inside the Chicago service area.
    df = df.filter(
        (F.col("start_lat").between(CHI_LAT_MIN, CHI_LAT_MAX)) &
        (F.col("end_lat").between(CHI_LAT_MIN, CHI_LAT_MAX)) &
        (F.col("start_lng").between(CHI_LNG_MIN, CHI_LNG_MAX)) &
        (F.col("end_lng").between(CHI_LNG_MIN, CHI_LNG_MAX))
    )
    df = step(df, "filter GPS to Chicago bbox")

    # 5. Normalize categorical text so grouping is consistent.
    df = (
        df
        .withColumn("member_casual", F.lower(F.trim(F.col("member_casual"))))
        .withColumn("rideable_type", F.lower(F.trim(F.col("rideable_type"))))
        .withColumn("start_station_name", F.trim(F.col("start_station_name")))
        .withColumn("end_station_name", F.trim(F.col("end_station_name")))
    )

    # --- Derive analytical columns -----------------------------------------
    df = (
        df
        .withColumn("trip_date", F.to_date("started_at"))
        .withColumn("trip_month", F.date_format("started_at", "yyyy-MM"))
        .withColumn("trip_year", F.year("started_at"))
        .withColumn("hour", F.hour("started_at"))
        # Spark dayofweek: 1=Sun..7=Sat. Convert to a readable name + weekend flag.
        .withColumn("dow_num", F.dayofweek("started_at"))
        .withColumn("day_of_week", F.date_format("started_at", "EEEE"))
        .withColumn("is_weekend",
                    F.when(F.col("dow_num").isin(1, 7), True).otherwise(False))
        # Meteorological seasons.
        .withColumn(
            "season",
            F.when(F.month("started_at").isin(12, 1, 2), "Winter")
             .when(F.month("started_at").isin(3, 4, 5), "Spring")
             .when(F.month("started_at").isin(6, 7, 8), "Summer")
             .otherwise("Fall"),
        )
        # Time-of-day buckets used by the demand analysis.
        .withColumn(
            "time_of_day",
            F.when(F.col("hour").between(6, 9), "Morning Peak (6-9)")
             .when(F.col("hour").between(10, 15), "Midday (10-15)")
             .when(F.col("hour").between(16, 19), "Evening Peak (16-19)")
             .when(F.col("hour").between(20, 23), "Evening (20-23)")
             .otherwise("Overnight (0-5)"),
        )
        # Straight-line trip distance and a directional route label.
        .withColumn("trip_distance_km",
                    F.round(haversine_km("start_lat", "start_lng",
                                         "end_lat", "end_lng"), 3))
        .withColumn("route",
                    F.concat_ws(" -> ", "start_station_name", "end_station_name"))
        .withColumn("is_round_trip",
                    F.col("start_station_name") == F.col("end_station_name"))
    )

    # Drop the helper column.
    df = df.drop("dow_num")

    n_clean = df.count()
    pct = 100.0 * n_clean / n_raw
    print("-" * 70)
    print(f"Clean rows: {n_clean:,}  ({pct:.1f}% of raw; "
          f"{n_raw - n_clean:,} rows removed)")

    # --- Write curated Parquet, partitioned by month -----------------------
    out_path = config.PROCESSED_DIR / "trips"
    (
        df.write
        .mode("overwrite")
        .partitionBy("trip_month")
        .parquet(str(out_path))
    )
    print(f"Wrote curated Parquet to: {out_path}")

    spark.stop()
    print("Stage 2 complete.")


if __name__ == "__main__":
    main()
