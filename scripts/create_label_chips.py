import os
import pandas as pd
import geopandas as gpd
import rioxarray as rxr
from pathlib import Path
from datetime import datetime as dt
from my_makelabels import MakeLabels

def set_up_directories(root_data_dir):
    """
    Set up the necessary directory paths.
    """
    raw_dir = Path(root_data_dir) / "raw"
    interim_dir = Path(root_data_dir) / "interim"
    processed_dir = Path(root_data_dir) / "processed"
    logs_dir = Path(root_data_dir) / "logs"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    interim_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return raw_dir, interim_dir, processed_dir, logs_dir

def load_catalogs(interim_dir):
    """
    Load the label catalog and chip catalog from the interim directory.
    """
    catalog_path = interim_dir / "label_catalog_allclasses.csv"
    chip_catalog_path = interim_dir / "label_catalog_int.csv"

    catalog = pd.read_csv(catalog_path)
    chip_catalog = pd.read_csv(chip_catalog_path)

    keep = ["name", "Class", "assignment_id", "Labeller", "status", "Score", 
            "N", "Area", "Qscore", "Rscore", "x", "y", "farea", "nflds", "image", "chip"]
    
    catalog = pd.merge(catalog, chip_catalog.drop(columns="image_date"))[keep]
    
    return catalog

def filter_label_catalog(catalog):
    """
    Apply the filtering logic to select the best assignments.
    """
    keep = ["name", "Class", "assignment_id", "Labeller", "status", "Score", 
            "N", "Area", "Qscore", "Rscore", "x", "y", "farea", "nflds", "image", "chip"]

    catalog = catalog.query("status not in ['Untrusted', 'Rejected']")

    groups = [
        {"whole": ["1a", "2"]},  # preserve all assignments in these groups
        {"best": ["1b", "1d"]},  # select best assignment for each site from these
        {"best": "4"}  # best assignment from this group
    ]
    
    mkl = MakeLabels(logfile=None)
    label_catalog = mkl.filter_catalog(catalog, groups, "Rscore", keep)

    label_catalog.drop_duplicates("name", inplace=True)
    
    return label_catalog

def load_fields_data(raw_dir):
    """
    Check if the fields data is already present. If so, load it.
    """
    fields_path = raw_dir / "mapped_fields_final.parquet"
    
    if not fields_path.exists():
        raise FileNotFoundError(f"Fields data not found at {fields_path}. Please ensure it is downloaded.")
    
    print(f"Loading fields data from {fields_path}...")
    fields = gpd.read_parquet(fields_path)
    
    return fields

def create_labels(fields, label_catalog, chip_dir, label_dir):
    """
    Create labels based on the field data and the label catalog.
    """
    kwargs = {
        "fields": fields,
        "label_dir": label_dir, 
        "chip_dir": chip_dir, 
        "src_col": "image",
        "verbose": False,
        "overwrite": False
    }

    mkl = MakeLabels(logfile=None)
    
    # Run the label-making function in parallel
    print("making labels started")
    catalogf = mkl.run_parallel_threads(
        label_catalog, mkl.threeclass_label, kwargs, 4
    )
    
    label_catalog_final = pd.DataFrame(catalogf).reset_index(drop=True)
    
    return label_catalog_final

def save_label_catalog(label_catalog_final, processed_dir):
    """
    Save the final label catalog to CSV.
    """
    label_catalog_final.to_csv(processed_dir / "label-catalog-filtered.csv", index=False)
    print(f"Final label catalog saved to {processed_dir / 'label-catalog-filtered.csv'}")

def main():
    root_data_dir = "/data" # update the path your data root.
    
    raw_dir, interim_dir, processed_dir, logs_dir = set_up_directories(root_data_dir)
    
    catalog = load_catalogs(interim_dir)
    
    label_catalog = filter_label_catalog(catalog)
    
    fields = load_fields_data(raw_dir)
    
    label_catalog_final = create_labels(fields, label_catalog, os.path.join(raw_dir,"images"), os.path.join(processed_dir,"masks")) # ensure the image and mask folders exists

    save_label_catalog(label_catalog_final, processed_dir)
    
    print("Label creation completed successfully.")

if __name__ == "__main__":
    main()