"""
03_analyze.py  --  Stage 3: ANALYZE  (Spark SQL)
================================================
Load the curated Parquet, register it as the SQL view `trips`, then run every
query in the sql/ folder against it. Each query's full result is written to
output/<query_name>.csv and a short preview is printed to the console.

Run it with:
    python src/03_analyze.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# How many rows of each result to print to the console (full result still
# goes to CSV).
PREVIEW_ROWS = 12


def load_query(sql_path: Path) -> str:
    """Read a .sql file and strip any trailing semicolon (Spark runs one
    statement per call and rejects a trailing ';')."""
    text = sql_path.read_text().strip()
    return text.rstrip(";").strip()


def main():
    spark = config.get_spark("divvy-analyze")

    print("=" * 70)
    print("STAGE 3: ANALYZE  --  Spark SQL")
    print("=" * 70)

    # Register the curated data as a SQL view so the .sql files can query it.
    trips = spark.read.parquet(str(config.PROCESSED_DIR / "trips"))
    trips.createOrReplaceTempView("trips")
    print(f"Registered view `trips` with {trips.count():,} rows.\n")

    # Run each .sql file in filename order (01_, 02_, ...).
    sql_files = sorted(config.SQL_DIR.glob("*.sql"))
    if not sql_files:
        raise SystemExit("No .sql files found in sql/")

    for sql_path in sql_files:
        name = sql_path.stem  # e.g. "05_hourly_demand"
        query = load_query(sql_path)

        print("-" * 70)
        print(f"[{name}]")

        result = spark.sql(query)

        # Print a readable preview.
        result.show(PREVIEW_ROWS, truncate=45)

        # Export the FULL result to a single CSV via pandas (results are small
        # aggregates, so collecting to the driver is fine and gives us one tidy
        # file instead of Spark's multi-part folder).
        out_csv = config.OUTPUT_DIR / f"{name}.csv"
        result.toPandas().to_csv(out_csv, index=False)
        print(f"  -> wrote {out_csv.relative_to(config.BASE_DIR)} "
              f"({result.count():,} rows)")

    spark.stop()
    print("-" * 70)
    print(f"Stage 3 complete. {len(sql_files)} result files in output/")


if __name__ == "__main__":
    main()
