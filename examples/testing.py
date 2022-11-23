# import base dependencies
import xarray as xr
import geopandas as gpd
import pydaymet
from pathlib import Path
import os

# import pydaymet to test multi-dimensional report
try:
    import pydaymet
    MULTI_DIMENSIONAL_TEST = True
except ImportError as e:
    print(f'WARNING: Please install pydaymet to test multi-dimensional support.')
    MULTI_DIMENSIONAL_TEST = False

# import fcpgtools!
import src.fcpgtools.tools as tools
import src.fcpgtools.utilities as utilities
import src.fcpgtools.terrainengine as terrainengine
from src.fcpgtools.terrainengine import taudem_engine
from src.fcpgtools.terrainengine import pysheds_engine

def main(
    multi_dimensional_test: bool = MULTI_DIMENSIONAL_TEST,
    test_pysheds: bool = True,
    test_taudem: bool = True,
    ) -> bool:
    
    # get all necessary paths for in/out data
    examples_dir = str(Path.cwd())
    if 'FCPGtools' in examples_dir:
        examples_dir = Path(examples_dir.split('FCPGtools', 2)[0]) / Path('FCPGtools/examples')
        print(f'var:examples_dir = {examples_dir}')
    else:
        del examples_dir
        print('ERROR: Cant find /FCPGtools/examples!')

    # get all necessary paths for in/out data
    in_data_dir = examples_dir / Path('in_data')
    print(f'Variable in_data_dir accesses {in_data_dir}')
    out_data_dir = examples_dir / Path('out_data')
    print(f'Variable in_data_dir accesses {out_data_dir}')

    # get tif data paths
    us_fdr_tif = in_data_dir / Path('validation_upstream_fdr.tif')
    ds_fdr_tif = in_data_dir / Path('validation_downstream_fdr.tif')
    landcover_tif = in_data_dir / Path('NALCMS_2015.tif')

    # get upstream basin shapefile path
    us_basin_shp_path = in_data_dir / Path('upstream_wbd.shp')

    # pull data into DataArrays and GeoPandas
    us_fdr = utilities.intake_raster(us_fdr_tif)
    landcover = utilities.intake_raster(landcover_tif)
    us_basin_shp = gpd.read_file(us_basin_shp_path)

    # pull in precipitation data
    if multi_dimensional_test:
        print('Pulling in multi-dimensional DAYMET precipitation data')
        bounding_box = list(us_basin_shp.geometry.total_bounds)
        print(f'Boudning box: {bounding_box}')

        precip = pydaymet.get_bygeom(
            bounding_box,
            crs=us_basin_shp.crs.to_wkt(),
            dates=("2021-01-01", "2021-12-30"),
            variables='prcp',
            time_scale="monthly",
            )['prcp']
    else:
        print('Using one dimensional precipitation data')
        precip_tif = Path(os.path.join(in_data_dir, 'validation_daymet_an_P_2017.tif'))
        precip = utilities.intake_raster(precip_tif)
    print('Done\n')

    # align precipitation raster
    print('Aligning precipitation raster to the upstream fdr')
    us_precip = tools.align_raster(
        precip,
        us_fdr,
        resample_method='bilinear', 
        out_path=Path(os.path.join(out_data_dir, 'us_fdr_daymet.tif')),
        )
    print('Done\n')
    
    # binarize and align landcover raster
    landcover_classes = {
        1: 'evergreen forest',
        7: 'tropical shrubland',
        8: 'temperate shrubland',
        9: 'tropical grassland',
        10: 'temperate grassland',
        14: 'wetland',
        15: 'cropland',
        16: 'barren',
        17: 'urban',
        18: 'open water',
        }

    print('Aligning landcover raster to the upstream fdr')
    us_landcover = tools.align_raster(
        landcover,
        us_fdr,
        resample_method='nearest', 
        out_path=None
        )

    us_binary_landcover = tools.binarize_categorical_raster(
        us_landcover,
        categories_dict=landcover_classes,
        ignore_categories=[18] # ignoring open water
        )
    print('Done\n')
    
    # use the pysheds engine
    if test_pysheds:
        print('Converting the FDR format to ESRI encoding')
        us_fdr_esri = tools.convert_fdr_formats(
            us_fdr,
            out_format='esri',
            )
        print('Done\n')


        print('PySheds: Making a FAC from us_fdr')
        fac_pysheds = terrainengine.pysheds_engine.fac_from_fdr(
            us_fdr_esri,
            upstream_pour_points=None,
            out_path=None,
            )
        print('Done\n')

        print('Testing getting pour points (HUC12 and HUC4 levels)')
        huc4_pour_points = tools.find_pour_points(
            fac_pysheds,
            us_basin_shp,
            basin_id_field='HUC12',
            use_huc4=True,
            )

        huc12_pour_points = tools.find_pour_points(
            fac_pysheds,
            us_basin_shp,
            basin_id_field='HUC12',
            use_huc4=False,
            )

        print('PySheds: Making a daymet accumulation grid')
        daymet_acc_pysheds = terrainengine.pysheds_engine.parameter_accumulate(
            us_fdr_esri,
            us_precip[0],
            out_path=Path(out_data_dir / Path('test_accum1.tif')),
            )
        print('Done\n')

        print('PySheds: Making a landcover accumulation grid')
        landcover_acc_pysheds = terrainengine.pysheds_engine.parameter_accumulate(
            us_fdr_esri,
            us_binary_landcover,
            out_path=Path(out_data_dir / Path('test_accum2.tif')),
            )
        print('Done\n')

    if test_taudem:
        # convert D8 encoding
        print('Converting the FDR format to taudem encoding')
        us_fdr_taudem = tools.convert_fdr_formats(
            us_fdr,
            out_format='taudem',
            )
        print('Done\n')

        print('TauDEM: Making a FAC from us_fdr')
        fac_taudem = taudem_engine.fac_from_fdr(
            d8_fdr=us_fdr_taudem, 
            upstream_pour_points=None,
            out_path=None,
            )
        print('Done\n')
        
        print('TauDEM: Making a daymet accumulation grid')
        daymet_acc_taudem = terrainengine.taudem_engine.parameter_accumulate(
            us_fdr_taudem,
            us_precip[0],
            out_path=Path(out_data_dir / Path('test_accum1.tif')),
            )
        print('Done\n')

        print('TauDEM: Making a landcover accumulation grid w/ engine')
        landcover_acc_taudem = terrainengine.taudem_engine.parameter_accumulate(
            us_fdr_taudem,
            us_binary_landcover,
            out_path=Path(out_data_dir / Path('test_accum2.tif')),
            )
        print('Done\n')

if __name__ == '__main__':
    main(
        MULTI_DIMENSIONAL_TEST,
        test_taudem=False,
        test_pysheds=True,
        )