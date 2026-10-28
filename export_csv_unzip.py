"""Combine each folder of TAI .csv.gz files into one CSV in csv/."""

import gzip
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


def download_data(root):
    api_key = os.environ.get("TAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "No local .csv.gz folders found. Set TAI_API_KEY to download the data."
        )
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

def combine_folder(folder, target):
    files = sorted(folder.glob("*.csv.gz"))
    header = None
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as output:
        for path in files:
            with gzip.open(path, "rb") as compressed:
                file_header = compressed.readline()
                if not file_header:
                    continue
                if header is None:
                    header = file_header
                    output.write(header)
                elif file_header != header:
                    raise ValueError(f"CSV header mismatch in {path}")
                shutil.copyfileobj(compressed, output)
    return len(files)


def main():
    root = Path(__file__).resolve().parent
    folders = sorted(
        path for path in root.iterdir()
        if path.is_dir() and any(path.glob("*.csv.gz"))
    )
    if not folders:
        download_data(root)
        folders = sorted(
            path for path in root.iterdir()
            if path.is_dir() and any(path.glob("*.csv.gz"))
        )
    if not folders:
        raise FileNotFoundError(f"No folders containing .csv.gz files found in {root}")

    for folder in folders:
        target = root / "csv" / f"{folder.name}.csv"
        count = combine_folder(folder, target)
        print(f"Combined {count} files from {folder.name} -> {target}")

    print(f"Exported {len(folders)} CSV files to {root / 'csv'}")


if __name__ == "__main__":
    main()
