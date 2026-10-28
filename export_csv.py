"""Download TAI data and decompress it into csv/. Set TAI_API_KEY first."""

import gzip
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    api_key = os.environ.get("TAI_API_KEY")
    if not api_key:
        raise SystemExit("Set TAI_API_KEY to your API key before running this script.")

    root = Path(__file__).resolve().parent
    request = Request(
        "https://aiso-water-data.vercel.app/files/tai/tai_all.tar",
        headers={"X-API-Key": api_key},
    )
    print("Downloading TAI data...")
    with tempfile.TemporaryFile() as download:
        with urlopen(request, timeout=120) as response:
            shutil.copyfileobj(response, download)
        download.seek(0)
        with tarfile.open(fileobj=download) as archive:
            archive.extractall(root, filter="data")

    source = root / "tai_all"
    files = sorted(source.rglob("*.csv.gz"))
    if not files:
        raise FileNotFoundError(f"No .csv.gz files found in {source}")

    for path in files:
        target = root / "csv" / path.relative_to(source).with_suffix("")
        target.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "rb") as compressed, target.open("wb") as output:
            shutil.copyfileobj(compressed, output)

    print(f"Exported {len(files)} CSV files to {root / 'csv'}")


if __name__ == "__main__":
    main()
