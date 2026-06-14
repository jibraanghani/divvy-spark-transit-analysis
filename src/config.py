"""
config.py
=========
Central configuration for the Divvy transit-analytics pipeline.

Every other script imports from this file so that paths, the list of months to
process, the data-lake layout, and the Spark/Java setup live in exactly one
place. This mirrors how a production pipeline keeps environment configuration
separate from business logic.
"""

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# 1. Project paths
# ---------------------------------------------------------------------------
# BASE_DIR resolves to the project root (the folder that contains src/, data/,
# sql/, output/), no matter where a script is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent

# Our local "data lake" mirrors a cloud layout (e.g. an S3 bucket):
#   raw/        -> landing zone: untouched source files exactly as downloaded
#   processed/  -> curated zone: cleaned, columnar Parquet ready for analytics
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Analysis results (CSV summaries) and rendered charts.
OUTPUT_DIR = BASE_DIR / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"

# SQL query files used by the analysis stage.
SQL_DIR = BASE_DIR / "sql"

# Make sure the folders exist whenever any script imports this module.
for _d in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, FIGURES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 2. Data source (Divvy public dataset, hosted on Amazon S3)
# ---------------------------------------------------------------------------
# Divvy publishes one ZIP of trip records per calendar month in a public,
# anonymously readable S3 bucket. The production ("AWS") path would read these
# straight from S3 with boto3; locally we download over the bucket's HTTPS
# endpoint, which serves the exact same objects.
S3_BUCKET = "divvy-tripdata"
S3_BASE_URL = f"https://{S3_BUCKET}.s3.amazonaws.com"

# File name pattern on S3, e.g. "202401-divvy-tripdata.zip".
FILE_TEMPLATE = "{month}-divvy-tripdata.zip"

# ---------------------------------------------------------------------------
# Our own AWS data lake (created for this project). The curated Parquet is
# uploaded here so Spark can read it straight from S3 via the s3a:// connector,
# exactly as it would on an EMR/Glue cluster in production.
# Override with the DIVVY_S3_BUCKET env var to point at a different bucket.
# ---------------------------------------------------------------------------
S3_LAKE_BUCKET = os.environ.get("DIVVY_S3_BUCKET", "divvy-transit-lake-821269906059")
S3_LAKE_REGION = os.environ.get("DIVVY_S3_REGION", "us-east-2")
S3_RAW_URI = f"s3a://{S3_LAKE_BUCKET}/raw"
S3_CURATED_URI = f"s3a://{S3_LAKE_BUCKET}/curated/trips"

# Hadoop-AWS connector versions that match the Hadoop bundled with PySpark 3.5.
_HADOOP_AWS_PACKAGES = (
    "org.apache.hadoop:hadoop-aws:3.3.4,"
    "com.amazonaws:aws-java-sdk-bundle:1.12.262"
)

# Months to process. Default: all of 2024 (~5.9 million trips). To run a quick
# smoke test, shorten this list (e.g. ["202401", "202402"]).
MONTHS = [
    "202401", "202402", "202403", "202404",
    "202405", "202406", "202407", "202408",
    "202409", "202410", "202411", "202412",
]


# ---------------------------------------------------------------------------
# 3. Java / Spark environment
# ---------------------------------------------------------------------------
# Spark 3.5 runs on Java 8/11/17. Newer JDKs (21+) break Spark's security
# internals, so we pin Spark to a Java 17 install if one is present, while
# leaving the system default Java untouched for everything else.
def _detect_java17_home():
    """Return a Java 17 home directory if we can find one, else None."""
    candidates = [
        os.environ.get("SPARK_JAVA_HOME"),          # explicit override
        "/opt/homebrew/opt/openjdk@17",              # Homebrew, Apple Silicon
        "/usr/local/opt/openjdk@17",                 # Homebrew, Intel Mac
        "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
    ]
    for path in candidates:
        if path and Path(path, "bin", "java").exists():
            return path
    return None


JAVA17_HOME = _detect_java17_home()
if JAVA17_HOME:
    # Point Spark's JVM at Java 17 for this process only.
    os.environ["JAVA_HOME"] = JAVA17_HOME


def get_spark(app_name: str):
    """
    Build (or reuse) a local SparkSession tuned for a single laptop.

    Returns a ready-to-use SparkSession. Import this everywhere instead of
    constructing a session by hand, so every stage gets identical settings.
    """
    # Imported here (not at module top) so that scripts which only need paths
    # don't pay the cost of importing PySpark.
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder
        .appName(app_name)
        # local[*] = run Spark in-process using every CPU core on this machine.
        .master("local[*]")
        # Give the driver room to hold a year of trips in memory during shuffles.
        .config("spark.driver.memory", "4g")
        # 5.9M rows is small for Spark; fewer shuffle partitions = less overhead.
        .config("spark.sql.shuffle.partitions", "16")
        # Quieter, prettier timestamp parsing.
        .config("spark.sql.session.timeZone", "America/Chicago")
    )
    spark = builder.getOrCreate()
    # Keep the console focused on our output, not Spark's internal logging.
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def get_spark_s3(app_name: str):
    """
    Build a SparkSession that can read/write Amazon S3 via the s3a:// scheme.

    Adds the hadoop-aws connector and tells it to authenticate with the AWS
    credentials already configured on this machine (the `aws configure` profile
    in ~/.aws/credentials, or standard AWS_* environment variables). Credentials
    are never hard-coded here.
    """
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "16")
        .config("spark.sql.session.timeZone", "America/Chicago")
        # Pull the S3 connector jars from Maven on first run (cached afterwards).
        .config("spark.jars.packages", _HADOOP_AWS_PACKAGES)
        # Use the standard AWS credential chain (env vars -> ~/.aws/credentials).
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
        .config("spark.hadoop.fs.s3a.endpoint",
                f"s3.{S3_LAKE_REGION}.amazonaws.com")
        .config("spark.hadoop.fs.s3a.impl",
                "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark
