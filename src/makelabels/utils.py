import os
import re
import pandas as pd
import leafmap.leafmap as leafmap
import logging

def view_random_label(catalog, label_dir, chip_dir, bands=[1,2,3], 
                      seed=None): 
    """
    A leafmap-based viewer that enables comparison of a randomly selected
    label against of the image chip

    Args: 
    catalog: pandas.DataFrame
        The processed label catalog
    label_dir: str
        The path to the label directory (not strings only, not Path)
    chip_dir: str
        The path to the image chip directory (not strings only, not Path)
    bands: list
        Specify band combination for the image chip. Defaults to [1,2,3] for 
        true color
    seed: int
        Defaults to None, but the same chip can be selected again if an integer
        is provided

    Returns: 
        A leafmap viewer
    """
    random_label = catalog.sample(n=1, random_state=seed)
    lbl_path = os.path.join(label_dir, random_label.label.iloc[0])
    chip_path = os.path.join(chip_dir, random_label.chip.iloc[0])
    lbl_name = re.sub(".tif", "", random_label.label.iloc[0])
    m = leafmap.Map(
        zoom=17, center=random_label[["y", "x"]].iloc[0].to_list()
    )
    m.add_basemap("SATELLITE")
    m.add_raster(chip_path, bands=[1,2,3], layer_name='Image', 
                 zoom_to_layer=False)
    m.add_raster(lbl_path, layer_name=lbl_name,zoom_to_layer=False)
    return m

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