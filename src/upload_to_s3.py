"""
upload_to_s3.py  --  Populate the AWS data lake
===============================================
Sync the local raw CSVs and the curated Parquet up to the project's S3 bucket,
recreating the two-zone data lake in the cloud:

    s3://<bucket>/raw/            <- monthly trip CSVs (landing zone)
    s3://<bucket>/curated/trips/  <- cleaned, partitioned Parquet

Uses the AWS CLI (which reads the same `aws configure` credentials), so the
upload is parallelized and resumable. Run after the local pipeline:

    python src/upload_to_s3.py
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def sync(local_dir: Path, s3_uri: str, *extra_args: str):
    """Run `aws s3 sync local_dir s3_uri` and stream the result."""
    # s3a:// is Spark's scheme; the AWS CLI wants s3://.
    s3_uri = s3_uri.replace("s3a://", "s3://")
    cmd = ["aws", "s3", "sync", str(local_dir), s3_uri, *extra_args]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main():
    print("=" * 70)
    print(f"UPLOAD TO S3  --  bucket: {config.S3_LAKE_BUCKET}")
    print("=" * 70)

    # Raw landing zone (skip the zip archives; we only keep the extracted CSVs).
    sync(config.RAW_DIR, config.S3_RAW_URI, "--exclude", "*.zip")

    # Curated zone (the partitioned Parquet).
    sync(config.PROCESSED_DIR / "trips", config.S3_CURATED_URI)

    print("-" * 70)
    print("Upload complete. Verify with:")
    print(f"  aws s3 ls s3://{config.S3_LAKE_BUCKET}/ --recursive --summarize | tail -2")


if __name__ == "__main__":
    main()
