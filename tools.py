import rasterio as rs
import numpy as np
import sys
import os
import pandas as pd
import gdal
import subprocess
import glob
import shutil
import traceback
import urllib.request
import datetime
from multiprocessing import Pool as processPool
from osgeo import osr

def tauDrainDir(inRast, outRast):
    """
    Inputs:
        inRast - Flow direction raster from NHDPlus

    Outputs:
        outRast - Flow direction raster for tauDEM
    """

    print('Reclassifying Flow Directions...')

    # load input data
    with rs.open(inRast) as ds:
        dat = ds.read(1)
        inNoData = ds.nodata
        profile = ds.profile.copy() # save the metadata for output later

    tauDir = dat.copy()
    # remap NHDplus flow direction to TauDEM flow Direction
    # east is ok
    
    tauDir[dat == 2] = 8 # southeast
    tauDir[dat == 4] = 7 # south
    tauDir[dat == 8] = 6 # southwest
    tauDir[dat == 16] = 5 # west
    tauDir[dat == 32] = 4 # northwest
    tauDir[dat == 64] = 3 # north
    tauDir[dat == 128] = 2 # northeast
    tauDir[dat == inNoData] = 0 # no data
    tauDir = tauDir.astype('uint8')#8 bit integer is sufficient for flow directions

    # edit the metadata
    profile.update({
                'dtype':'uint8',
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':0,
                'bigtiff':'IF_SAFER',
                'driver' : "GTiff"})

    with rs.open(outRast,'w',**profile) as dst:
        dst.write(tauDir,1)
        print("TauDEM drainage direction written to: {0}".format(outRast))

def accumulateParam(paramRast, fdr, accumRast, outNoDataRast = None, outNoDataAccum = None, zeroNoDataRast = None, multiplier = None, multNoDataRast = None, cores = 1):
    """
    Inputs:
        paramRast - Raster of parameter values to acumulate, this file is modified by the function
        fdr - flow direction raster in tauDEM format
        accumRast - file location to store accumulated parameter values
        outNoDataRast - file location to store parameter no data raster
        outNoDataAccum - file location to store accumulated no data raster
        cores - number of cores to use parameter accumulation

    Outputs:
        accumRast - raster of accumulated parameter values
        outNoDataRast - raster of no data values
        outNoDataRast - raster of accumulated no data values
    """

    if not os.path.isfile(paramRast):
        print("Error - Parameter raster file is missing!")
        return #Function will fail, so end it now
    if not os.path.isfile(fdr):
        print("Error - Flow direction file is missing!")
        return #Function will fail, so end it now

    with rs.open(paramRast) as ds: # load parameter raster
        data = ds.read(1)
        profile = ds.profile
        paramNoData = ds.nodata

    with rs.open(fdr) as ds: # load flow direction raster
        direction = ds.read(1)
        directionNoData = ds.nodata # pull the accumulated area no data value

    print(paramNoData)
    if paramNoData == None:
        print("Warning: Parameter raster no data value not specified, results may be invalid")


    #Deal with no data values
    basinNoDataCount = len(data[(data == paramNoData) & (direction != directionNoData)]) # Count number of cells with flow direction but no parameter value
    
    if basinNoDataCount > 0:
        print('Warning: No data parameter values exist in basin')

        #If a no data file path is given, accumulate no data values
        if (outNoDataRast != None) & (outNoDataAccum != None):
            noDataArray = data.copy()
            noDataArray[(data == paramNoData) & (direction != directionNoData)] = 1 #Set no data values in basin to 1
            noDataArray[(data != paramNoData)] = 0 #Set values with data to 0
            noDataArray[(direction == directionNoData)] = -1 #Set all values outside of basin to -1
            noDataArray = noDataArray.astype(np.int8)

            # Update profile for no data raster
            profile.update({
                    'dtype':'int8',
                    'compress':'LZW',
                    'profile':'GeoTIFF',
                    'tiled':True,
                    'sparse_ok':True,
                    'num_threads':'ALL_CPUS',
                    'nodata':-1,
                    'bigtiff':'IF_SAFER'})
            
            # Save no data raster
            with rs.open(outNoDataRast, 'w', **profile) as dst:
                dst.write(noDataArray,1)
                print("Parameter No Data raster written to: {0}".format(outNoDataRast))
        

        #Set no data values in the basin to zero so tauDEM accumulates them correctly
        noDataZero = data.copy()
        noDataZero[(data == paramNoData) & (direction != directionNoData)] = 0 #Set no data values in basin to 0

        # Update profile for no data raster
        profile.update({
            'compress':'LZW',
            'profile':'GeoTIFF',
            'tiled':True,
            'sparse_ok':True,
            'num_threads':'ALL_CPUS',
            'bigtiff':'IF_SAFER'})
            
        # Save no data raster
        with rs.open(zeroNoDataRast, 'w', **profile) as dst:
            dst.write(noDataArray,1)
            print("Parameter No Data raster written to: {0}".format(zeroNoDataRast))
            
        tauDEMweight = zeroNoDataRast #Set file to use as weight in tauDEM accumulation

            
        # Use tauDEM to accumulate no data values
        try:
            print('Accumulating No Data Values')
            
            outFl = outNoDataRast
                
            tauParams = {
            'fdr':fdr,
            'cores':cores, 
            'outFl':outFl,
            'weight':outNoDataRast
            }
            
            cmd = 'mpiexec -bind-to rr -n {cores} aread8 -p {fdr} -ad8 {outFl} -wg {weight} -nc'.format(**tauParams) # Create string of tauDEM shell command
            print(cmd)
            result = subprocess.run(cmd, shell = True) # Run shell command
            result.stdout
            print("Parameter no data accumulation written to: {0}".format(outNoDataRast))
            
        except:
            print('Error Accumulating Data')
            traceback.print_exc()



    else:
        tauDEMweight = paramRast #Set file to use as weight in tauDEM accumulation


    #Use tauDEM to accumulate the parameter
    try:
        print('Accumulating Data...')
        tauParams = {
        'fdr':fdr,
        'cores':cores, 
        'outFl':accumRast, 
        'weight':tauDEMweight
        }
        
        cmd = 'mpiexec -bind-to rr -n {cores} aread8 -p {fdr} -ad8 {outFl} -wg {weight} -nc'.format(**tauParams) # Create string of tauDEM shell command
        print(cmd)
        result = subprocess.run(cmd, shell = True) # Run shell command
        
        result.stdout
        

    except:
        print('Error Accumulating Data')
        traceback.print_exc()

    
def make_cpg(accumParam, fac, outRast, noDataRast = None, minAccum = None):
    '''
    Inputs:
        
        accumParam - path to the accumulated parameter data raster
        fac - flow accumulation grid path
        outRast - output CPG file location
        noDataRast - raster of accumulated parameter no data values
        minAccum - Value of flow accumulation below which the CPG values will be set to no data
        

    Outputs:
        outRast - Parameter CPG 
    '''
    outNoData = -9999
    

    if not os.path.isfile(accumParam):
        print("Error - Accumulated parameter raster file is missing!")
        return #Function will fail, so end it now
    if not os.path.isfile(fac):
        print("Error - Flow accumulation file is missing!")
        return #Function will fail, so end it now


    print("Reading accumulated parameter file {0}".format(datetime.datetime.now()))
    with rs.open(accumParam) as ds: # load accumulated data and no data rasters
        data = ds.read(1)
        profile = ds.profile
        inNoData = ds.nodata

    data = data.astype(np.float32) #Convert to 32 bit float
    data[data == inNoData] = np.NaN # fill with no data values where appropriate

    print("Reading basin flow accumulation file {0}".format(datetime.datetime.now()))
    with rs.open(fac) as ds: # flow accumulation raster
        accum = ds.read(1)
        facNoData = ds.nodata # pull the accumulated area no data value


    if noDataRast != None:
        print("Correcting CPG for no data values")
        with rs.open(noDataRast) as ds: # accumulated no data raster
            accumNoData = ds.read(1)
            noDataNoData = ds.nodata # pull the accumulated no data no data value
            
        accumNoData[accumNoData == noDataNoData] = 0 #Set no data values to zero

        corrAccum = accum - accumNoData # Compute corrected accumulation
        corrAccum = corrAccum.astype(np.float32) # Convert to 32 bit float
        corrAccum[accum == facNoData] = np.NaN # fill with no data values where appropriate
        
    else:
        accum2 = accum.astype(np.float32)
        accum2[accum == facNoData] = np.NaN # fill this with no data values where appropriate
        corrAccum = accum2 # No correction required
        

    
    
    # Throw warning if there is a negative accumulation
    if np.nanmin(corrAccum) < 0:
        print("Warning: Negative accumulation value")
        print("Minimum value:{0}".format(np.nanmin(corrAccum)))
 
    print("Computing CPG values {0}".format(datetime.datetime.now()))
    dataCPG = data / (corrAccum + 1) # make data CPG

    print("Replacing numpy nan values {0}".format(datetime.datetime.now()))
    dataCPG[np.isnan(dataCPG)] = outNoData # Replace numpy NaNs with no data value

    # Replace values in cells with small flow accumulation with no data
    if minAccum != None:
        print("Replacing small flow accumulations {0}".format(datetime.datetime.now()))
        dataCPG[corrAccum < minAccum] = outNoData #Set values smaller than threshold to no data

    # Update raster profile
    profile.update({'dtype':dataCPG.dtype,
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':outNoData,
                'bigtiff':'IF_SAFER'})

    print("Saving CPG raster {0}".format(datetime.datetime.now()))
    with rs.open(outRast, 'w', **profile) as dst:
        dst.write(dataCPG,1)
        print("CPG file written to: {0}".format(outRast))
    
    

def resampleParam(inParam, fdr, outParam, resampleMethod="bilinear", cores=1):
    '''
    Inputs:
        
        inParam - input parameter data raster
        fdr - flow direction raster
        outParam - output file for resampled parameter raster
        resampleMethod (str)- resampling method, either bilinear or nearest neighbor
        cores - number of cores to use

    Outputs:
        outParam - resampled, reprojected, and clipped parameter raster
    '''

    with rs.open(fdr) as ds: # load flow direction raster in Rasterio
        fdrcrs = ds.crs #Get flow direction coordinate system
        xsize, ysize = ds.res #Get flow direction cell size
        #Get bounding coordinates of the flow direction raster
        fdrXmin = ds.transform[2]
        fdrYmax = ds.transform[5]
        fdrXmax = fdrXmin + xsize*ds.width
        fdrYmin = fdrYmax - ysize*ds.height

    with rs.open(inParam) as ds: # load parameter raster in Rasterio
        paramNoData = ds.nodata
        paramType = ds.dtypes[0] #Get datatype of first band


    # Convert flow direction spatial reference from wkt to proj4 
    print("Flow Direction WKT: " + str(fdrcrs))

    
    #Over ride the output coordinate system to make it work with USGS Albers projection
    fdrcrs = "\"+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs\""
    #print("Flow Direction proj4: " + str(fdrcrs))
    
    # Choose an appropriate gdal data type for the parameter
    if paramType == 'int8':
        outType = 'Int16' # Convert 8 bit integers to 16 bit in gdal
        print("Warning: 8 bit inputs are unsupported and may not be reprojected correctly") #Print warning that gdal may cause problems with 8 bit rasters
    elif paramType == 'int16':
        outType = 'Int16' 
    elif paramType == 'int32':
        outType = 'Int32'
    elif paramType == 'int64':
        outType = 'Int64'
    elif paramType == 'float32':
        outType = 'Float32'
    elif paramType == 'float64':
        outType = 'Float64'
    else:
        print("Warning: Unsupported data type {0}".format(paramType))
        print("Defaulting to Float64")
        outType = 'Float64' # Try a 64 bit complex floating point if all else fails

    

    # Resample, reproject, and clip the parameter raster with GDAL
    try:
        print('Resampling and Reprojecting Parameter Raster...')
        warpParams = {
        'inParam': inParam,
        'outParam': outParam,
        'fdr':fdr,
        'cores':cores, 
        'resampleMethod': resampleMethod,
        'xsize': xsize, 
        'ysize': ysize, 
        'fdrXmin': fdrXmin,
        'fdrXmax': fdrXmax,
        'fdrYmin': fdrYmin,
        'fdrYmax': fdrYmax,
        'fdrcrs': fdrcrs, 
        'nodata': paramNoData,
        'datatype': outType
        }
        
        cmd = 'gdalwarp -overwrite -tr {xsize} {ysize} -t_srs {fdrcrs} -te {fdrXmin} {fdrYmin} {fdrXmax} {fdrYmax} -co "PROFILE=GeoTIFF" -co "TILED=YES" -co "SPARSE_OK=TRUE" -co "COMPRESS=LZW" -co "NUM_THREADS=ALL_CPUS" -co "BIGTIFF=IF_SAFER" -r {resampleMethod} -dstnodata {nodata} -ot {datatype} {inParam} {outParam}'.format(**warpParams)
        print(cmd)
        result = subprocess.run(cmd, shell = True)
        result.stdout
        
    except:
        print('Error Reprojecting Parameter Raster')
        traceback.print_exc()
    




#Tools for decayed accumulation CPGs

def makeDecayGrid(d2strm, k, outRast):
    '''
    Inputs:
        
        d2strm - Raster of flow distances from each grid cell to the nearest stream
        k - constant applied to decay factor denominator
        outRast - output file path for decay grid

    Outputs:
        outRast - decay raster computed as the inverse number of grid cells (1/number) from each grid cell to the nearest stream
    '''
    if not os.path.isfile(d2strm):
        print("Error - Stream distance raster file is missing!")
        return #Function will fail, so end it now


    with rs.open(d2strm) as ds: # load flow direction data
        data = ds.read(1)
        profile = ds.profile
        inNoData = ds.nodata
        xsize, ysize = ds.res #Get flow direction cell size
    
    if xsize != ysize:
        print("Warning - grid cells are not square, results may be incorrect")


    outNoData = 0 #Set no data value for output raster

    print("Building decay grid {0}".format(datetime.datetime.now()))
    decayGrid = data.astype(np.float32) #Convert to float
    decayGrid[data == inNoData] = np.NaN # fill with no data values where appropriate
    decayGrid = xsize/(decayGrid + k*xsize) #Compute decay function

    decayGrid[np.isnan(decayGrid)] = outNoData # Replace numpy NaNs with no data value

    # Update raster profile
    profile.update({
                'dtype': decayGrid.dtype,
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':inNoData,
                'bigtiff':'IF_SAFER'})

    print("Saving decay raster {0}".format(datetime.datetime.now()))
    
    with rs.open(outRast, 'w', **profile) as dst:
        dst.write(decayGrid,1)
        print("Decay raster written to: {0}".format(outRast))

def applyMult(inRast, mult, outRast):
    '''
    Inputs:
        inRast- Input parameter raster
        mult - multiplier raster

    Outputs:
        outRast - parameter raster multiplied by the multiplier raster
    '''  

    if not os.path.isfile(inRast):
        print("Error - Input parameter raster file is missing!")
        return #Function will fail, so end it now

    if not os.path.isfile(mult):
        print("Error - Multiplier file is missing!")
        return #Function will fail, so end it now


    print("Reading input rasters {0}".format(datetime.datetime.now()))
    with rs.open(inRast) as ds: # load input rasters
        data = ds.read(1)
        profile = ds.profile
        inNoData = ds.nodata
    
    with rs.open(mult) as ds: # load input rasters
        m = ds.read(1)
        mNoData = ds.nodata

    data = data.astype(np.float32) #Convert to 32 bit float
    data[data == inNoData] = np.NaN # fill with no data values where appropriate
    m[m == mNoData] = np.NaN # fill with no data values where appropriate
    outData = data * multiplier #Multiply the parameter values by the multiplier

    outNoData = -9999
    outData[np.isnan(outData)] = outNoData # Replace numpy NaNs with no data value

    # Update raster profile
    profile.update({'dtype':outData.dtype,
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':outNoData,
                'bigtiff':'IF_SAFER'})

    print("Saving raster {0}".format(datetime.datetime.now()))
    with rs.open(outRast, 'w', **profile) as dst:
        dst.write(outData,1)
        print("Raster written to: {0}".format(outRast))


def decayAccum(ang, mult, outRast, paramRast = None, cores=1) :
    '''
    Inputs:
        
        ang - Flow angle from tauDEM Dinfinity flow direction tool
        mult - grid of multiplier values applied to upstream accumulations, 1 corresponds to no decay, 0 corresponds to complete decay
        outRast - output file path for decayed accumulation raster
        paramRast - raster of parameter values to accumulate, no parameter raster will result in area being accumulated
        cores - number of cores to use

    Outputs:
        outRast - decayed accumulation raster
    '''

    if paramRast != None:
        try:
            print('Accumulating parameter')
            tauParams = {
            'ang':ang,
            'cores':cores, 
            'dm':mult,
            'dsca': outRast,
            'weight':paramRast
            }
                    
            cmd = 'mpiexec -bind-to rr -n {cores} dinfdecayaccum -ang {ang} -dm {dm} -dsca {dsca}, -wg {weight} -nc'.format(**tauParams) # Create string of tauDEM shell command
            print(cmd)
            result = subprocess.run(cmd, shell = True) # Run shell command
            result.stdout
            print("Parameter accumulation written to: {0}".format(outRast))
                    
        except:
            print('Error Accumulating Data')
            traceback.print_exc()
    else:
        try:
            print('Accumulating parameter')
            tauParams = {
            'ang':ang,
            'cores':cores, 
            'dm':mult,
            'dsca': outRast,
            }
                    
            cmd = 'mpiexec -bind-to rr -n {cores} dinfdecayaccum -ang {ang} -dm {dm} -dsca {dsca}, -nc'.format(**tauParams) # Create string of tauDEM shell command
            print(cmd)
            result = subprocess.run(cmd, shell = True) # Run shell command
            result.stdout
            print("Parameter accumulation written to: {0}".format(outRast))
                
        except:
            print('Error Accumulating Data')
            traceback.print_exc()



def dist2stream(fdr, fac, thresh, outRast, cores=1) :
    '''
    Inputs:
        
        fdr - flow direction raster
        fac - flow accumulation raster
        thresh - accumulation threshold for stream formation
        outRast - output file path for distance raster
        cores - number of cores to use

    Outputs:
        outRast - raster with values of d8 flow distance from each cell to the nearest stream
    '''

    try:
        print('Accumulating parameter')
        tauParams = {
        'fdr':fdr,
        'cores':cores, 
        'fac':fac,
        'outRast': outRast,
        'thresh':thresh
        }
                
        cmd = 'mpiexec -bind-to rr -n {cores} d8hdisttostrm -p {fdr} -src {fac} -dist {outRast}, -thresh {thresh}'.format(**tauParams) # Create string of tauDEM shell command
        print(cmd)
        result = subprocess.run(cmd, shell = True) # Run shell command
        result.stdout
        print("Distance raster written to: {0}".format(outRast))
                
    except:
        print('Error computing distances')
        traceback.print_exc()

def maskStreams(inRast, streamRast, outRast):
    '''
    Inputs:
        
        inRast - input raster to mask
        streamRast - raster with all non-stream pixels set to no data
        outRast - output raster file location

    Outputs:
        outRast - raster with non-stream cells set to no data
    '''
  
    if not os.path.isfile(inRast):
        print("Error - Parameter raster file is missing!")
        return #Function will fail, so end it now
    if not os.path.isfile(streamRast):
        print("Error - Stream raster file is missing!")
        return #Function will fail, so end it now


    with rs.open(inRast) as ds: # load input raster
        data = ds.read(1)
        profile = ds.profile
        inNoData = ds.nodata 

    with rs.open(streamRast) as ds: # load input raster
        strmVals = ds.read(1)
        strmNoData = ds.nodata 

    data[data == inNoData] = np.NaN #Set no data values to NaN
    data[strmVals == strmNoData] = np.NaN #Set values off streams to NaN

    data[data == np.NaN] = inNoData #Set NaNs to input no data value

    # Update raster profile
    profile.update({
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':inNoData,
                'bigtiff':'IF_SAFER'})

    print("Saving raster {0}".format(datetime.datetime.now()))
    with rs.open(outRast, 'w', **profile) as dst:
        dst.write(data,1)
        print("CPG file written to: {0}".format(outRast))

def resampleParams(inParams, fdr, outWorkspace, resampleMethod="bilinear", cores=1, appStr="rprj"):
    '''
    Inputs:
        
        inParam - list of input parameter rasters
        fdr - flow direction raster
        
        outWorkspace - output directory for resampled rasters
        resampleMethod (str)- resampling method, either bilinear or nearest neighbor
        cores = number of cores to use
        appStr = String of text to append to filename

    Outputs:
        Resampled, reprojected, and clipped parameter rasters

    Returns:
        List of fielpaths to resampled rasters
    '''

    fileList = [] #Initialize list of output files

    for param in inParams:

        baseName = os.path.splitext(os.path.basename(param))[0] #Get name of input file without extention

        
        ext = ".tif" #File extension

        outPath = os.path.join(outWorkspace, baseName + appStr + ext)
        fileList.append(outPath)

        resampleParam(param, fdr, outPath, resampleMethod, cores) #Run the resample function for the parameter raster

    return fileList

def accumulateParams(paramRasts, fdr, outWorkspace, cores = 1, appStr="accum"):
    '''
    Inputs:
        
        paramRasts - list of input parameter rasters to accumulate
        fdr - flow direction raster
        
        outWorkspace - output directory for accumulation rasters
        cores = number of cores to use
        appStr = string of text to append to filename

    Outputs:
        raster of accumulated parameter values

    Returns:
        list of fielpaths to accumulated parameter rasters
    '''

    fileList = [] #Initialize list of output files
    
    for param in paramRasts:

        baseName = os.path.splitext(os.path.basename(param))[0] #Get name of input file without extention
        ext = ".tif" #File extension

        outPath = os.path.join(outWorkspace, baseName + appStr + ext)
        fileList.append(outPath)

        nodataPath = os.path.join(outWorkspace, baseName + "nodata" + ext) 
        nodataAccumPath = os.path.join(outWorkspace, baseName + "nodataaccum" + ext) 

        accumulateParam(param, fdr, outPath, outNoDataRast=nodataPath, outNoDataAccum=nodataAccumPath, cores=cores) #Run the flow accumulation function for the parameter raster

    """
    processCores = min(4, cores) # Set number of cores used by each process to 4 or the number of available cores
    numProcess = floor(cores / processCores) # Compute the number of processes to create

    from functools import partial
    pool = processPool(processes=numProcess)

    # Use pool.map() to call tauDEM accumulation in parallel
    fileList = pool.map(partial(accumulateParam, fdr, outPath, processCores), paramRasts)

    #close the pool and wait for the work to finish
    pool.close()
    pool.join()
    """



    return fileList

def make_cpgs(accumParams, fac, outWorkspace, minAccum=None, appStr="CPG"):
    '''
    Inputs:
        
        accumParams - list of accumulated parameter rasters to create CPGs from
        fac - flow accumulation raster
        
        outWorkspace - output directory for CPGs
        appStr = string of text to append to filename

    Outputs:
        CPG

    Returns:
        list of fielpaths to parameter CPGs
    '''

    fileList = [] #Initialize list of output files

    for param in accumParams:

        baseName = os.path.splitext(os.path.basename(param))[0] #Get name of input file without extention
        ext = ".tif" #File extension

        outPath = os.path.join(outWorkspace, baseName + appStr + ext)
        fileList.append(outPath)

        make_cpg(param, fac, outPath, minAccum=minAccum) #Run the CPG function for the accumulated parameter raster

    return fileList

def cat2bin(inCat, outWorkspace):
    '''
    Inputs:
        
        inCat - input catagorical parameter raster
        outWorkspace - workspace to save binary raster outputs
        
    Outputs:
        Binary rasters for each parameter category

    Returns:
        List of filepaths to output files
    '''
    print("Creating binaries for %s"%inCat)
    

    baseName = os.path.splitext(os.path.basename(inCat))[0] #Get name of input file without extention
    ext = ".tif" #File extension

    # load input data
    with rs.open(inCat) as ds:
        dat = ds.read(1)
        profile = ds.profile.copy() # save the metadata for output later
        nodata = ds.nodata
    

    
    cats = np.unique(dat) # Get unique values in raster
    cats = np.delete(cats, np.where(cats ==  nodata)) # Remove no data value from list

    fileList = [] #Initialize list of output files

    # edit the metadata
    profile.update({'dtype':'int8',
                'compress':'LZW',
                'profile':'GeoTIFF',
                'tiled':True,
                'sparse_ok':True,
                'num_threads':'ALL_CPUS',
                'nodata':-1,#Use -1 as no data value
                'bigtiff':'IF_SAFER'})

    #Create binary rasters for each category
    """
    for n in cats:
        catData = dat.copy()
        catData[(dat != n) & (dat != nodata)] = 0
        catData[dat == n] = 1
        catData[dat == nodata] = -1 #Use -1 as no data value
        catData = catData.astype('int8')#8 bit integer is sufficient for zeros and ones

        catRasterName = baseName + str(n) + ext
        catRaster = os.path.join(outWorkspace, catRasterName)
        fileList.append(catRaster)

        print("Saving %s"%catRaster)
        with rs.open(catRaster,'w',**profile) as dst:
            dst.write(catData,1)
    """
    from functools import partial
    pool = processPool()

    # Use pool.map() to create binaries in parallel
    fileList = pool.map(partial(binarizeCat, data=dat, nodata=nodata, outWorkspace=outWorkspace, baseName=baseName, ext=ext, profile=profile), cats)

    #close the pool and wait for the work to finish
    pool.close()
    pool.join()
    
    
    return fileList



def binarizeCat(val, data, nodata, outWorkspace, baseName, ext, profile):

    '''
    Inputs:
        
        data - numpy arrary of raster data to convert to binary
        val - raster value to extract binary for
        nodata - raster no data value
        outWorkspace - workspace to save binary raster outputs
        baseName - base name for the raster output
        ext - file extension for raster output
        
    Outputs:
        Binary raster the specified parameter value

    Returns:
        Filepath to output files
    '''

    catData = data.copy()
    catData[(data != val) & (data != nodata)] = 0
    catData[data == val] = 1
    catData[data == nodata] = -1 #Use -1 as no data value
    catData = catData.astype('int8')#8 bit integer is sufficient for zeros and ones

    catRasterName = baseName + str(val) + ext
    catRaster = os.path.join(outWorkspace, catRasterName)

    print("Saving %s"%catRaster)
    with rs.open(catRaster,'w',**profile) as dst:
        dst.write(catData,1)
    

    return catRaster # Return the path to the raster created

def tauFlowAccum(fdr, accumRast, cores = 1):
    """
    Inputs:
        fdr - flow direction raster in tauDEM format
        accumRast - file location to store accumulated parameter values
        cores - number of cores to use parameter accumulation

    Outputs:
        accumRast - raster of accumulated parameter values
    """


    #Use tauDEM to accumulate the parameter
    try:
        print('Accumulating Data...')
        tauParams = {
        'fdr':fdr,
        'cores':cores, 
        'outFl':accumRast, 
        }
        
        cmd = 'mpiexec -bind-to rr -n {cores} aread8 -p {fdr} -ad8 {outFl} -nc'.format(**tauParams) # Create string of tauDEM shell command
        print(cmd)
        result = subprocess.run(cmd, shell = True) # Run shell command
        
        result.stdout
        

    except:
        print('Error Accumulating Data')
        traceback.print_exc()










def downloadNHDPlusRaster(HUC4, fileDir):
    '''
    Inputs:
        
        HUC4 - 4 digit HUC to download NHDPlus raster data for
        fileDir - Directory in which to save NHDPlus data

    Outputs:
        NHDPlus raster files saved to directory

    '''
    compressedFile = os.path.join(fileDir, str(HUC4) + "_RASTER.7z")
    print("Downloading File: " + compressedFile)
    urllib.request.urlretrieve("https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlus/HU4/HighResolution/GDB/NHDPLUS_H_%s_HU4_RASTER.7z"%str(HUC4), compressedFile)

    print("Extracting File...")
    os.system("7za x {0} -o{1}".format(compressedFile,fileDir))

    

def ExtremeUpslopeValue(fdr, param, output, accum_type = "MAX", cores = 1, fac = None, thresh = None):
    '''
    Wrapper for the TauDEM extreme upslope value function.

    Parameters
    ----------
    fdr : str
        Path to TauDEM D8 flow accumulation raster
    param : str
        Path to parameter raster to run through the D8 Extreme Upslope Value tool
    output : str
        Path to outplet file
    accum_type : str (optional, defaults to "MAX") 
        Either  "MAX" or "MIN".
    cores : int
        Number of cores to run this process on.

    Returns
    -------
    output : str
    '''
    
    print()
    tauParams = {
        'fdr':fdr,
        'cores':cores, 
        'outFl':output,
        'param':param,
        'accum_type':accum_type.lower()
        }

    if accum_type == "min": # insert flag for min 
        cmd = 'mpiexec -bind-to rr -n {cores} d8flowpathextremeup -p {fdr} -sa {param} -ssa {outFl} -{accum_type} -nc'.format(**tauParams) # Create string of tauDEM shell command
    else: # no flag for max
        cmd = 'mpiexec -bind-to rr -n {cores} d8flowpathextremeup -p {fdr} -sa {param} -ssa {outFl} -nc'.format(**tauParams) # Create string of tauDEM shell command

    print(cmd)
    result = subprocess.run(cmd, shell = True) # Run shell command
        
    result.stdout

    if fac != None and thresh != None: # if a stream mask is specified
        outNoData = -9999

        with rs.open(output) as src:
            dat = src.read(1)
            params = src.meta.copy()
            noData = src.nodata
            dat[dat == noData] = np.NaN
            
        del src

        with rs.open(fac) as src:
            fac = src.read(1)
            fac[fac == src.nodata] = outNoData

        del src

        dat[fac < thresh] = outNoData # make low accumulation areas noData
        dat[fac == outNoData] = outNoData # make borders noData

        params['nodata'] = outNoData

        with rs.open(output,'w',**params) as dst: # write out raster.
            dst.write(dat,1)

    return None
