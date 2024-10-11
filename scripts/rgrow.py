from osgeo import gdal
from .utils import readImageGDAL,writeImageGDAL
import rgrow_flood
import os
import numpy as np

def regionGrow(workspace,seed_image_path,grow_image_path,threshold):
    seed_image, seed_dataset = readImageGDAL(seed_image_path)
    grow_image, grow_dataset = readImageGDAL(grow_image_path)

    output_image = np.zeros_like(grow_image, dtype=np.uint8)
    out_image_path = os.path.join(workspace,"permanent_water.tif")
    try:
        rgrow_flood.rgrow(seed_image, grow_image, output_image, threshold)
        writeImageGDAL(out_image_path, output_image, seed_dataset)

    except Exception  as e:
        print(e)