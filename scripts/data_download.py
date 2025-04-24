import os
import urllib.request
from pathlib import Path

def download_file(url, dest_path):
    """
    Download a file if it doesn't already exist.
    """
    if not dest_path.exists():
        print(f"Downloading {url} to {dest_path}...")
        urllib.request.urlretrieve(url, dest_path)
        print(f"Downloaded {url} to {dest_path}")
    else:
        print(f"File already exists: {dest_path}")

def check_and_download_data(root_data_dir):
    """
    Checks if the necessary files exist, if not, downloads them.
    """
    
    raw_dir = Path(root_data_dir) / "raw"
    interim_dir = Path(root_data_dir) / "interim"
    processed_dir = Path(root_data_dir) / "processed"
    logs_dir = Path(root_data_dir) / "logs"

    raw_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Files to be downloaded, check if ensure the file links are up to date
    files_to_download = [
        {
            "url": "https://github.com/agroimpacts/lacunalabels/raw/main/data/interim/label_catalog_allclasses.csv",
            "dest": interim_dir / "label_catalog_allclasses.csv"
        },
        {
            "url": "https://github.com/agroimpacts/lacunalabels/raw/main/data/interim/label_catalog_int.csv",
            "dest": interim_dir / "label_catalog_int.csv"
        },
        {
            "url": "https://zenodo.org/record/11060871/files/images.tgz",
            "dest": raw_dir / "images.tgz"
        },
        {
            "url": "https://zenodo.org/record/11060871/files/mapped_fields_final.parquet", 
            "dest": raw_dir / "mapped_fields_final.parquet"
        }
    ]

    for file in files_to_download:
        download_file(file["url"], file["dest"])

if __name__ == "__main__":
    root_data_dir = "/data" # update the path to desired destination folder.
    check_and_download_data(root_data_dir)