import os
import re
import pandas as pd
import leafmap.leafmap as leafmap
from matplotlib import pyplot as plt
import logging
import rioxarray as rxr

def view_random_label(catalog, label_dir, chip_dir, bands, interactive=False, 
                      seed=None, width=12, height=5): 
    """
    A leafmap-based viewer that enables comparison of a randomly selected
    label against of the image chip

    Params:
    -------
    catalog : pandas.DataFrame
        The processed label catalog
    label_dir : str
        The path to the label directory (not strings only, not Path)
    chip_dir : str
        The path to the image chip directory (not strings only, not Path)
    bands : list
        Specify band combination for the image chip
    interactive : bool, default = False
        Whether to plot with an interactive leafmap or matplotlib.        
    seed: int, default is None
        Use an integer seed to ensure the same chip can be selected again
    width : int, default is 12
        Width of plot
    height : int, default is 5
        Height of plot

    Returns:
    --------
    A leafmap viewer or matplotlib-based plots. The latter can be 
    needed for installs where localtileserver doesn't work correctly with 
    leafmap.
    """
    random_label = catalog.sample(n=1, random_state=seed)
    lbl_path = os.path.join(label_dir, random_label.label.iloc[0])
    chip_path = os.path.join(chip_dir, random_label.image.iloc[0])

    if interactive:
        lbl_name = re.sub(".tif", "", random_label.label.iloc[0])
        m = leafmap.Map(
            zoom=17, center=random_label[["y", "x"]].iloc[0].to_list()
        )
        m.add_basemap("SATELLITE")
        m.add_raster(chip_path, bands=bands, layer_name='Image', 
                     zoom_to_layer=False)
        m.add_raster(lbl_path, layer_name=lbl_name, zoom_to_layer=False)
        return m
    else:
        lbl = rxr.open_rasterio(lbl_path)
        img = rxr.open_rasterio(chip_path)
        fig, (ax1, ax2) = plt.subplots(1, 2)
        fig.set_size_inches(12, 5, forward=True)
        lbl.plot(ax=ax1, add_colorbar=False)
        ax2.set_title("Label")
        ax1.set_xlabel('')
        ax1.set_ylabel('')       
        img[bands].plot.imshow(ax=ax2, robust=True)
        ax2.set_xlabel('')
        ax2.set_ylabel('')
        ax2.set_title(f"Image for {random_label.name}")
        
def log_message(msg, verbose, logger=None):
    """Helps control print statements and log writes

    Parameters
    ----------
    msg : str
        Message to write out
    verbose : bool
        Prints or not to console
    logger : logging.logger
        logger (defaults to none)
      
    Returns:
    --------  
        Message to console and or log
    """
    
    if verbose:
        print(msg)

    if logger:
        logger.info(msg)

def setup_logger(logfile, use_date=False):
    """Create logger

    Parameters
    ----------
    logfile : Path or str
        Path to write log to, including name of file (without extension)
    use_date : bool
        Use today's date and time in file name

    Returns:
    --------  
    logger

    """
    if use_date:
        dt = datetime.now().strftime("%d%m%Y_%H%M")
        log = f"{logfile}_{dt}.log"
    else: 
        log = f"{logfile}.log"

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    log_format = (
        f"%(message)s  %(asctime)s::%(levelname)s::%(filename)s::"
        f"%(lineno)d"
    )
    level = logging.INFO
    logger = logging.getLogger()
    logger.setLevel(level)
    log_file = log
    ch = logging.FileHandler(log_file)
    ch.setLevel(level)
    
    formatter = logging.Formatter(log_format)
    # add formatter to ch
    ch.setFormatter(formatter)       

    logger.addHandler(ch)
    logger.info("Setup logger in PID {}".format(os.getpid()))
    return logger