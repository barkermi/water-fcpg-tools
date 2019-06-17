import dbf
import os
import pandas as pd
import numpy as np
import rasterio as rs

paramtables = ["../data/cov/static/Soils/DrainageClass.dbf"]
MUCraster = "../data/cov/static/MapunitRaster_CONUS_90m1.tif"

outDir = "../data/cov/static/Soils/work"

#Convert dbfs to csvs
for paramtable in paramtables:


    paramName = os.path.splitext(os.path.basename(paramtable))[0]
    MUCname = os.path.splitext(os.path.basename(MUCraster))[0]
    

    csvName = os.path.join(outDir, paramName + ".csv") #Create csv file
    print(csvName)

    db = dbf.Table(paramtable)
    db.open()

    dbf.export(db, csvName, header = True)

    df = pd.read_csv(csvName)

    combdf = pd.concat([df["(b'mukey', 5)"], df["(b'drnclass_1', 10)"]], axis=1)

    combdf = combdf.set_index("(b'mukey', 5)")
    print(combdf)
    d = combdf.to_dict()



    print(d.viewkeys())
    print(d)
    print(d[1949705])

"""
    with rs.open(MUCraster) as ds: # load map unit code raster
        MUC = ds.read(1)
        MUCNoData = ds.nodata # pull the no data value
        profile = ds.profile


        print(ds.profile)

        #paramArray = np.copy(MUC)
        #for k, v in d.items(): paramArray[MUC==k] = v

        #print(len(np.unique(MUC)))

        print(d[296575])
        MUC = np.vectorize(d.get)(MUC)
        MUC[MUC == None] = MUCNoData
        print(MUC)
        print(len(np.unique(MUC)))
        #print(paramArray)

        #newName = os.path.join(outDir, "")

"""



