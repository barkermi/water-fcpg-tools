import xarray as xr
import geopandas as gpd

from typing import Union
from typing import Tuple 

from geoengine.protocols import Raster

def find_cell_downstream(d8_fdr: Raster, coords: Tuple) -> Tuple:
    """
    Uses a D8 FDR to find the cell center coordinates downstream from any cell (specified
    Note: this replaces py:func:FindDownstreamCellTauDir(d, x, y, w) in the V1.1 repo.
    :param d8_fdr: (xr.DataArray or str raster path) a D8 Flow Direction Raster (dtype=Int).
    :param coords: (tuple) the input (lat:float, lon:float) to find the next cell downstream from.
    :returns: (tuple) an output (lat:float, lon:float) representing the cell center coorindates
        downstream from the cell defined via :param:coords.
    """

# raster masking function
def spatial_mask(in_raster: Raster,
        mask_shp: Union[gpd.GeoDataFrame,str] = None,
        out_path: str = None,
        mask_cell_value: int = None,
        inverse: bool = False,
    ) -> xr.DataArray:
    """
    Primarily for masking rasters (i.e., FAC) by basin shapefiles, converting out-of-mask raster
    values to NoData. A cell value can also be used to create a mask for integer rasters. 
    Note: default behavior (inverse=False) will make it so cells NOT COVERED by mask_shp -> NoData.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param mask_shp: (geopandas.GeoDataFrame or a str shapefile path) shapefile used for masking.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param mask_cell_value: (int, optional) if mask_shp == None this parameter can be used to mask
        cells (i.e., change to NoData) if they equal mask_cell_value.
    :param inverse: (bool, default=False) if True, cells that ARE COVERED by mask_shp -> NoData.
    :returns: (xr.DataArray) the output binary mask raster.
    """


def value_mask(in_raster: Raster,
        thresh: Union[int,float] = None,
        greater_than: bool = True,
        equals: int = None,
        out_mask_value: int = None,
        out_path: str = None,
        inverse: bool = False,
    ) -> xr.DataArray:
    """"
    Mask a raster via a value threshold. Primary use case is to identify high acumulation zones / stream cells.
    Cells included in the mask are given a value of 1, all other cells are given a value of 0 (unless out_mask_value!=None).
    Note: this function generalizes V1:pyfunc:makeStreams() functionality.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param thresh: (int or float, default=None) 
    :param greater_than: (bool, default=True) if False, only values less than param:thresh are included in the mask.
    :param equals: (int, default=None) if not None, only cells matching the value of param:equals are included in the mask.
    :param out_mask_value: (int, default=None) allows non-included cells to be given a non-zero integer value.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param inverse: (bool, default=False) if True, the inverse of the mask is made.
    :returns: (xr.DataArray) the output binary mask raster.
    """


def nodata_mask(
        in_raster: Raster, 
        inverse: bool = False,
        nodata_value: Union[float,int] = None,
        out_path: str = None,
    ) -> xr.DataArray:
    """
    Creates an output binary raster based on an input where nodata values -> 1, and valued cells -> 0.
    Note: while param:inverse=True this can be used with pyfunc:apply_mask() to match nodata cells between rasters.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param inverse: (bool, default=False) if True, values that are NOT nodata -> 1, and nodata values -> 0.
    :param nodata_value: (float->np.nan or int) if the nodata value for param:in_raster is not in the metadata,
        set this parameter to equal the cell value storing nodata (i.e., np.nan or -999).
    :param out_path: (str, default=None) defines a path to save the output raster.
    :returns: (xr.DataArray) the output binary mask raster.
    """


def apply_mask(
        in_raster: Raster, 
        mask_raster: Raster, 
        inverse: bool = False, 
        out_path: str = None,
    ) -> xr.DataArray:
    """
    Converts all values NOT included within a mask (i.e., value=0 while inverse=False) param:in_raster's nodata value.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param mask_raster: (xr.DataArray or str raster path) a binary "mask" raster where value=0 -> nodata in param:in_raster.
    :param inverse: (bool, default=False) if True param:mask_raster cells with a value of 1 are converted to nodata.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :returns: (xr.DataArray) the output raster with nodata cells.
    """


def binarize_categorical_rasters(
        cat_raster: Raster, 
        ignore_caregories: list = None,
        out_path: str = None,
        split_rasters: bool = False,
    ) -> xr.DataArray:
    """
    :param cat_raster: (xr.DataArray or str raster path) a categorical (dtype=int) raster with N
        unique categories (i.e., land cover classes).
    :param ignore_categories: (list of integers, default=None) category cell values not include
        in the output raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param split_rasters: (bool, default=False) if True AND out_path != None, the directory
        in out_path is used to store N separate .tif files for each unique cat_raster value.
        Note that this is the behavior in V1.1 of FCPGTools.
    :returns: (xr.DataArray) a N-band multi-dimensional raster as a xarray DataArray object.
    """


def find_pour_points(
        fac_raster: Raster, 
        basins_shp: str = None, 
        basin_id_field: str = None,
    ) -> dict:
    """
    Find pour points (aka outflow cells) in a FAC raster by basin using a shapefile.
    :param fac_raster: (xr.DataArray or str raster path) a Flow Accumulation Cell raster (FAC).
    :param basins_shp: (str path) a .shp shapefile containing basin geometries.
    :basin_id_field: default behavior is for each GeoDataFrame row to be a unique basin.s
        However, if one wants to use a higher level basin id that is shared acrcoss rows,
        this should be set to the column header storing the higher level basin id.
    :returns: (dict) a dictionary with keys (i.e., basin IDs) storing coordinates as a tuple(lat, lon).
    """
    # check extents of shapefile bbox and make sure all overlap the FAC raster extent


# make FCPG raster
def create_fcpg(param_accum_raster: Raster, fac_raster: Raster,
                ignore_nodata: bool = False, out_path: str = None) -> xr.DataArray:
    """
    Creates a Flow Conditioned Parameter Grid raster by dividing a paramater accumulation
    raster by a Flow Accumulation Cell (FAC) raster. FCPG = param_accum / fac.
    :param param_accum_raster: (xr.DataArray or str raster path)
    :param fac_raster: (xr.DataArray or str raster path) input FAC raster.
    :param ignore_nodata: (bool, default=False) by default param_accum_raster cells with nodata
        are kept as nodata. If True, the lack of parameter accumulation is ignores, and the FAC value
        if given to the cell without adjustment.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :returns: (xr.DataArray) the output FCPG raster as a xarray DataArray object.
    """

#TODO: Evaluate feasibility of implementing 
#These are extra add ons that would be nice to implement budget permitting 
#Prepare flow direction raster (FDR)
def fix_pits(dem: Raster, out_path: str = None, fix: bool = True) -> xr.DataArray:
    """
    Detect and fills single cell "pits" in a DEM raster using pysheds: .detect_pits()/.fill_pits().
    :param dem: (xr.DataArray or str raster path) the input DEM raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param fix: (bool, default=True) if False, a print statement warns of the # of single cell pits
        without fixing them. The input raster is returned as is.
    :returns: (xr.DataArray) the filled DEM an xarray DataArray object (while fix=True).
    """


def fix_depressions(dem: Raster, out_path: str = None, fix: bool = True) -> xr.DataArray:
    """
    Detect and fills multi-cell "depressions" in a DEM raster using pysheds: .detect_depressions()/.fill_depressions().
    :param dem: (xr.DataArray or str raster path) the input DEM raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param fix: (bool, default=True) if False, a print statement warns of the # of dpressions
        without fixing them. The input raster is returned as is.
    :returns: (xr.DataArray) the filled DEM an xarray DataArray object (while fix=True).
    """


def fix_flats(dem: Raster, out_path: str = None, fix: bool = True) -> xr.DataArray:
    """
    Detect and resolves "flats" in a DEM using pysheds: .detect_flats()/.resolve_flats().
    :param dem: (xr.DataArray or str raster path) the input DEM raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param fix: (bool, default=True) if False, a print statement warns of the # flats
        without fixing them. The input raster is returned as is.
    :returns: (xr.DataArray) the resolved DEM an xarray DataArray object (while fix=True).
    """


def d8_fdr(dem: Raster, out_path: str = None, out_format: str = 'TauDEM') -> xr.DataArray:
    """
    Creates a flow direction raster from a DEM. Can either save the raster or keep in memory.
    :param dem: (xr.DataArray or str raster path) the DEM from which to make the FDR.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param out_format: (str, default=TauDEM) type of D8 flow direction encoding for output.
    :returns: the FDR as a xarray DataArray object.
    """

##Possibly gets moved to a utilities.py file
def clip(
        in_raster: Raster, 
        match_raster: Raster,
        out_path: str = None, 
        custom_shp: Union[str,gpd.GeoDataFrame] = None,
        custom_bbox: list = None,
    ) -> xr.DataArray:
    """
    Clips a raster to the rectangular extent (aka bounding box) of another raster (or shapefile).
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param match_raster: (xr.DataArray or str raster path) if defined, in_raster is
        clipped to match the extent of match_raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param custom_shp: (str path or GeoDataFame, default=None) a shapefile that is used to define
        the output extent if match_raster == None.
    :param custom_bbox: (list, default=None) a list with bounding box coordinates that define the output
        extent if match_raster == None. Coordinates must be of the form [minX, minY, maxX, maxY].
    :returns: (xr.DataArray) the clipped raster as a xarray DataArray object.
    """

def reproject(
        in_raster: Raster, 
        match_raster: Raster,
        out_path: str = None,
        custom_crs: str = None,
    ) -> xr.DataArray:
    """
    Reprojects a raster to match another rasters Coordinate Reference System (CRS), or a custom CRS.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param match_raster: (xr.DataArray or str raster path) if defined, in_raster is
        reprojected to match the Coordinate Reference System (CRS) of match_raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param custom_crs: (str) custom CRS string, only used if match_raster == None.
    :returns: (xr.DataArray) the reprojected raster as a xarray DataArray object.
    """
    # figure out what types of CRS strings exist / can be read by whatever library we use.

def resample(
        in_raster: Raster, 
        match_raster: Raster,
        out_path: str = None, 
        custom_cell_size: Union[float,int] = None,
    ) -> xr.DataArray:
    """
    Resamples a raster to match another raster's cell size, or a custom cell size.
    :param in_raster: (xr.DataArray or str raster path) input raster.
    :param match_raster: (xr.DataArray or str raster path) if defined, in_raster is
        resampled to match the cell size of match_raster.
    :param out_path: (str, default=None) defines a path to save the output raster.
    :param custom_cell_size: (float or int) custom cell size, only used if match_raster == None.
    :returns: (xr.DataArray) the resampled raster as a xarray DataArray object.
    """


