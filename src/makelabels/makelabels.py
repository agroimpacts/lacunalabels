import os
import rasterio
from rasterio.enums import Resampling
from rasterio import features
import xarray as xr
import rioxarray as rxr
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, box
from datetime import datetime as dt
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool
from .utils import *

class MakeLabels:
    def __init__(self, logfile=None):
        """
        Code for chipping images and rasterizing labels
        
        Params:
        -------
        logfile : Path of str, default None
            Provide a path and name for a log file
        
        """
        self.logfile = logfile
        if self.logfile:
            self.logger = setup_logger(self.logfile, use_date=False)
        else: 
            self.logger = None
        
        msg = f"Started dataset creation"
        log_message(msg, verbose=True, logger=self.logger)
        
    def target_poly(self, x, y, w=0.0025, crs="epsg:4326") -> gpd.GeoDataFrame:
        """
        Creates a target polygon from an x, y coordinate of a specific width
        
        Parameters:
        ----------
        x : float
            Longitude
        y : float
            Latitude
        w : float
            Width in units of CRS (defaults to 0.0025 decimal degrees)
        crs : str
            CRS code string, defaults as "epsg:4326"
        
        Returns:
        --------
        A polygon in a GeoDataFrame 
        """
         
        poly = box(x-w, y-w, x+w, y+w)
        gdf = gpd.GeoDataFrame({"geometry": [poly]}, crs=crs)
        return gdf

    def template(self, bounds, rows, cols, decimals=4,
                 crs="epsg:4326") -> xr.DataArray: 
        """
        Creates a template raster to use for a rasterization 
        target
        
        Parameters:
        ----------
        bounds : tuple
            Bounding box coordinates for output image
        rows : int
            Height in pixels of output label/image
        cols : int
            Width in pixels of output label/image
        decimals : int
            Number of decimals to round width to
        crs : str
            CRS code string, defaults as "epsg:4326"
        
        Returns:
        --------
        An xarray.DataArray with specified shape
        """
        
        width = np.round(bounds[2] - bounds[0], decimals)
        trans = rasterio.transform.from_bounds(*bounds, width=cols, height=rows)
        x, y = rasterio.transform.xy(trans, np.arange(cols), np.arange(rows))

        rast = xr.DataArray(
            np.full((rows, cols), 0), 
            dims=["y", "x"], coords={"y": y, "x": x}, 
            attrs={"transform": trans, "crs": crs}
        )
        return rast

    def image_chipper(self, catrow, src_dir, dst_dir, src_col, date_col, w,
                      rows, cols, crs, decimals=4, overwrite=True, 
                      verbose=True, resample_method=None) -> pd.Series:
        """
        Creates image chip from larger image within specified target location 
        and dimensions, and writes it to disk
        
        Parameters:
        ----------
        catrow : pandas.Series
            A row of the catalog containing name, x, y, date, and src image names
        src_dir : Path or str 
            Path to input image directory
        dst_dir : Path or str
            Path to output chip directory
        src_col : str
            Name of column in row that contains the source image name
        date_col : str
            Name of column in row that contains the name of the image date 
        w : float, default 0.0025
            Width in units of CRS 
        rows : int
            Height in pixels of output label/image
        cols : int
            Width in pixels of output label/image
        crs : str
            CRS code string, e.g. "epsg:4326"
        decimals : int
            Number of decimal places to round bounding box
        overwrite : bool, default True
            Overwrite existing chips if they exist?
         verbose : bool, default True
            Whether to print messages or not
        resample_method : Resampling, default None
            Which method of resampling to use. Will use cubic if None provided
    
        Returns:
        --------
        The input pandas.Series with the name of the chipped image added
        """
        
        image = f"{catrow['name']}_{catrow[date_col][:-3]}.tif"
        dst = str(Path(dst_dir) / image)
        catrow["image"] = image
        
        if not resample_method:
            resample_method=Resampling.cubic 

        if not overwrite and os.path.exists(dst):
            msg = f"{os.path.basename(dst)} exists, skipping"
            log_message(msg, verbose, logger=self.logger)

        else: 
            bnds = np.round(
                (self.target_poly(catrow['x'], catrow['y'], w)
                 .bounds
                 .iloc[0]
                 .tolist()), 
                decimals
            )
            r = self.template(bnds, rows, cols, decimals, crs)
            
            image = rxr.open_rasterio(Path(src_dir) / catrow[src_col])
            chip = image.rio.reproject_match(r, resampling=resample_method)
 
            # checks
            try:
                assert chip.rio.bounds() == r.rio.bounds()
            except AssertionError as err:
                msg = f"{os.path.basename(dst)}: wrong bounds"
                log_message(msg, verbose, logger=self.logger)
                raise err
            try:    
                assert chip.shape[1:3] == (rows, cols)
            except AssertionError as err:
                msg = f"{os.path.basename(dst)}: wrong shape"
                log_message(msg, verbose, logger=self.logger)
                raise err

            chip.rio.to_raster(dst)   
            msg = f"Created {os.path.basename(dst)}"
            log_message(msg, verbose, logger=self.logger)

        return catrow
    
    def threeclass_label(self, catrow, label_dir, chip_dir, src_col, fields, 
                         verbose=True, overwrite=True) -> pd.Series:
        """
        Create a three class label (0: non-field, 1: field interior, 
        2: field boundary) with the same dimensions as the corresponding 
        image chip

        Parameters:
        -----------
        catrow: pandas.Series
            A series representing one row (assignment) from the label catalog
        fields: geopandas.GeoDataFrame
            The fields polygons, read in from the provided geoparquet file
        label_dir: str
            Directory to write rasterized labels to
        chip_dir : str
            Directory containing image chips
        src_col : str
            Name of column in row that contains the source image name
        verbose : bool, default True
            Whether to print messages or not
        overwrite: bool
            Overwrite label if it exists on disk or not (default = True)
         
        Returns: 
        --------
        A pandas.Series containing details of the written labels
        """

        name_parts = catrow[src_col].split("_")
        lbl_name = f"{name_parts[0]}_{catrow['assignment_id']}_{name_parts[1]}"
        dst = Path(label_dir) / lbl_name

        if not overwrite and os.path.exists(dst):
            msg = f"{os.path.basename(dst)} exists, skipping"
            log_message(msg, verbose, logger=self.logger)

        else: 
            chip = rxr.open_rasterio(Path(chip_dir) / catrow[src_col])

            transform = chip.rio.transform()
            _, r, c = chip.shape
            res = np.mean([abs(transform[0]), abs(transform[4])])

            grid = gpd.GeoDataFrame(geometry=[box(*chip.rio.bounds())], 
                                    crs=chip.rio.crs)

            out_arr = np.zeros((r, c)).astype('int16')
            if catrow["nflds"] > 0:

                shp = fields[fields['assignment_id'] == \
                             catrow['assignment_id']].copy()

                shp["category"] = 1
                shp['buffer_in'] = shp.geometry.buffer(-res)
                shp['buffer_out'] = shp.geometry.buffer(res)
                shp = gpd.overlay(grid, shp, how='intersection')
                out_arr = np.zeros((r, c)).astype('uint8')

                shapes = ((geom, value) 
                          for geom, value in zip(shp['geometry'], shp['category']))
                burned = features.rasterize(shapes=shapes, fill=0, 
                                            out=out_arr.copy(), 
                                            transform=transform)

                try:
                    shapes_shrink = (
                        (geom, value) 
                        for geom, value in zip(shp['buffer_in'], shp['category'])
                    )
                    shrunk = features.rasterize(
                        shapes=shapes_shrink, fill=0, out=out_arr.copy(), 
                        transform=transform
                    )
                    shapes_explode = (
                        (geom, value) 
                        for geom, value in zip(shp['buffer_out'], shp['category'])
                    )
                    exploded = features.rasterize(
                        shapes=shapes_explode, fill=0, out=out_arr.copy(), 
                        transform=transform
                    )
                except:
                    shp['buffer'] = shp.geometry.buffer(-res)
                    shapes_shrink = (
                        (geom, value) 
                        for geom, value in zip(shp['buffer'], shp['category'])
                    )
                    shrunk = features.rasterize(
                        shapes=shapes_shrink, fill=0, out=out_arr.copy(), 
                        transform=transform
                    )

                lbl = (
                    burned * 2 - shrunk + \
                    np.where((exploded*2-burned)==1, 0, exploded*2-burned)
                    .astype(np.uint8)
                )
            else: 
                lbl = out_arr

            lbl_raster = xr.DataArray(
                lbl,
                dims=["y", "x"],
                coords={"y": chip["y"], "x": chip["x"]},
                attrs={"transform": transform, "crs": chip.rio.crs}
            )

            # check dimensions
            try:
                assert chip.rio.bounds() == lbl_raster.rio.bounds()
            except AssertionError as err:
                msg = f"{os.path.basename(dst)} has incorrect bounds"
                log_message(msg, verbose, logger=self.logger)
                raise err
            try:    
                assert chip.shape[1:3] == lbl_raster.shape
            except AssertionError as err:
                msg = f"{os.path.basename(dst)} incorrect output shape"
                log_message(msg, verbose, logger=self.logger)
                raise err

            # write to disk
            lbl_raster.rio.to_raster(dst)
            msg = f"Created {os.path.basename(dst)}"
            log_message(msg, verbose, logger=self.logger)

        catrow_out = catrow.copy()
        catrow_out["label"] = lbl_name

        return catrow_out
    
    def filter_catalog(self, catalog, groups, metric, keep) -> pd.DataFrame:
        """
        Function to filter the full catalog by class and quality metric

        Params:
        -------
        catalog: pandas.DataFrame
            The full catalog, read in
        groups: list
            A list of key-value pairs providing with possible keys of "whole" and 
            "best", with the values providing one or more of the label classes. 
            Classes corresponding to "whole" will have all assignments in the class
            selected. "Best" will result in the best assignment 
            corresponding to the provided metric selected/
        metric: str
            One of the quality metrics in the catalog, e.g. Rscore, Qscore. Must be 
            provided if a key in groups is not "whole"
        keep: list
            Names of columns in the full catalog that should be kept in the 
            filtered catalog

        Returns:
        --------
        A DataFrame containing the filtered assignments, possibly with 
        duplicates. If so, you may wish to remove them by following up with a 
        `drop_duplicates()`
        """
        out_catalog = []
        for g in groups:
            cls = list(g.values())[0]
            cat = catalog.query("Class in @cls")
            if list(g.keys())[0] == "whole":
                print(f"Extracting all of Class {' and '.join(cls)}")
                out_catalog.append(cat)
            elif list(g.keys())[0] == "best": 
                print(f"Extracting best of Class {' and '.join(cls)}")
                out_catalog.append(
                    cat.groupby("name")
                    .apply(lambda x: x.loc[[x[metric].idxmax()]] 
                           if not x[metric].isna().all() else x, 
                           include_groups=False)
                    .reset_index(level=["name"])
                )
            else: 
                print("Use either 'whole' or 'best' as group keys")
                break 

        out_catalog = (
            pd.concat(out_catalog, axis=0)[keep]
            .reset_index(drop=True)
        )
        return out_catalog
   
    def run_parallel_pool(self, catalog, function, args, nworkers=None): 
        """
        Runs one of the class functions in parallel, using CPUs
        
        Params:
        -------
        catalog : pandas.DataFrame
            The full catalog to run over
        function : function
            The name of the function to run in parallel
        args : dict
            A dictionary of keyword arguments required by the named function
        nworkers : integer, default None
            Number of 
        """
        rows = catalog.to_dict(orient='records')
        
        with Pool(nworkers) as pool:
            results = pool.map(self.parallelize, 
                               [(row, function, args) for row in rows])

        log_message("Completed run", verbose=True, logger=self.logger)
        
        return results

    def run_parallel_threads(self, catalog, function, args, nworkers=None): 
        """
        Runs one of the class functions concurrently, using threads
        
        Params:
        -------
        catalog : pandas.DataFrame
            The full catalog to run over
        function : function
            The name of the function to run in parallel
        args : dict
            A dictionary of keyword arguments required by the named function
        nworkers : integer, default None
            Number of 
        """
        rows = catalog.to_dict(orient='records')
                    
        with ThreadPoolExecutor(max_workers=nworkers) as executor:
            futures = [executor.submit(self.parallelize, (row, function, args)) 
                       for row in rows]
            results = [future.result() for future in futures]
            
        log_message("Completed run", verbose=True, logger=self.logger)
        
        return results

    @staticmethod
    def parallelize(params):
        """
        Generic function to enable parallelization
        """
        row, function, args = params
        try:
            result = function(row, **args)
            return result
        except Exception as e:
            return None, str(e)