"""
01_ingest.py  --  Stage 1: COLLECT
==================================
Download monthly Divvy trip files from the public S3 bucket into the raw
landing zone (data/raw/), unzipping each month's CSV.

Run it with:
    python src/01_ingest.py

The job is idempotent: months that are already present are skipped, so it is
safe to re-run after an interruption.
"""

import sys
import zipfile
from pathlib import Path

import requests

# Allow "import config" whether the script is launched from the project root
# or from inside src/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def download_month(month: str) -> Path:
    """Download one month's ZIP from S3 into data/raw/ and return its path."""
    zip_name = config.FILE_TEMPLATE.format(month=month)
    url = f"{config.S3_BASE_URL}/{zip_name}"
    dest = config.RAW_DIR / zip_name

    if dest.exists():
        print(f"  [skip]     {zip_name} already downloaded")
        return dest

    print(f"  [download] {url}")
    # stream=True so we don't load the whole file into memory at once.
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                fh.write(chunk)

    mb = dest.stat().st_size / (1024 * 1024)
    print(f"             saved {dest.name} ({mb:.1f} MB)")
    return dest


def unzip_month(zip_path: Path) -> Path:
    """Extract the single trip CSV from a month's ZIP into data/raw/."""
    with zipfile.ZipFile(zip_path) as zf:
        # The archive contains one real CSV (plus Mac metadata we ignore).
        csv_members = [
            m for m in zf.namelist()
            if m.lower().endswith(".csv") and "__MACOSX" not in m
        ]
        if not csv_members:
            raise RuntimeError(f"No CSV found inside {zip_path.name}")

        member = csv_members[0]
        out_path = config.RAW_DIR / Path(member).name
        if out_path.exists():
            print(f"  [skip]     {out_path.name} already extracted")
            return out_path

        # Extract to a flat path (drop any folder structure inside the zip).
        with zf.open(member) as src, open(out_path, "wb") as dst:
            dst.write(src.read())
        print(f"  [unzip]    {out_path.name}")
        return out_path


def main():
    print("=" * 70)
    print("STAGE 1: INGEST  --  downloading Divvy trips from S3")
    print(f"  source : {config.S3_BASE_URL}")
    print(f"  target : {config.RAW_DIR}")
    print(f"  months : {len(config.MONTHS)}  ({config.MONTHS[0]}..{config.MONTHS[-1]})")
    print("=" * 70)

    csv_paths = []
    for month in config.MONTHS:
        print(f"- {month}")
        zip_path = download_month(month)
        csv_paths.append(unzip_month(zip_path))

    total_mb = sum(p.stat().st_size for p in csv_paths) / (1024 * 1024)
    print("-" * 70)
    print(f"Done. {len(csv_paths)} monthly CSV files in raw zone "
          f"({total_mb:.0f} MB uncompressed).")


if __name__ == "__main__":
    main()
