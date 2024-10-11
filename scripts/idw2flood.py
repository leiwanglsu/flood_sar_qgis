import json
from osgeo import gdal,ogr
import numpy as np
import os

def main():
# read the json file for parameters
    launch_json = "idw2flood.json"
    json_file_path = launch_json
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        args = json.load(file)
    workspace = args["Workspace"]
    fcName = os.path.join(workspace,args["Point Features"])
    fieldName = args['field name']
    demName = os.path.join(workspace,args["Raster"])
    outRaster = os.path.join(workspace,args["Output binary raster"])
    numerNeighbors = int(args['nn'])
    power = float(args["power"])
    interpFlood(workspace=workspace,
                threshold_points=fcName,
                field=fieldName,
                sarImage=demName,
                power=power)
def interpFlood(workspace,threshold_points,field,sarImage, power ):
    
# Read the dem data into a NumPy array
#turn on GDAL exceptions to avoid deprecation warning
    gdal.UseExceptions()
    ogr.UseExceptions()
    dem = gdal.Open(sarImage)
    band = dem.GetRasterBand(1)
    demData = band.ReadAsArray()
    dem__prj = dem.GetProjection()    
    geotransform = dem.GetGeoTransform()
    origin_x = geotransform[0]
    pixel_width = geotransform[1]
    rotation_x = geotransform[2]
    origin_y = geotransform[3]
    rotation_y = geotransform[4]
    pixel_height = geotransform[5]

    # Get the dimensions of the raster
    cols = dem.RasterXSize
    rows = dem.RasterYSize

    # Calculate the bounds
    min_x = origin_x
    max_x = origin_x + (cols * pixel_width) + (rows * rotation_x)
    min_y = origin_y + (cols * rotation_y) + (rows * pixel_height)
    max_y = origin_y
    outbnd = [min_x, min_y, max_x, max_y]
    tmpImage = os.path.join(workspace,"idw_threshold.tif")
    outRaster = os.path.join(workspace,"flood.tif")
# use gdal to interpolate
    print("Performing spatial interpolation")
    if os.path.exists(tmpImage):
            os.remove(tmpImage)

    ds = gdal.Grid(tmpImage, threshold_points, format='GTiff',
                outputBounds=outbnd,
                width=cols, height=rows, outputType=gdal.GDT_Float32,
                algorithm=f'invdist:power={power}:smoothing=1.0',
                zfield=field)    
# read the feature class
    idwRaster = ds.GetRasterBand(1).ReadAsArray()
    result_array = np.where(demData < idwRaster, 1, 0)
    ds = None

    # Create the output GeoTIFF file
    if os.path.exists(outRaster):
        os.remove(outRaster)
    print(f"\nWriting to raster{outRaster}")

    driver = gdal.GetDriverByName('GTiff')
    outds = driver.Create(outRaster, cols, rows, 1, gdal.GDT_Byte)


    # Set geotransform and projection
    outds.SetGeoTransform(geotransform)
    outds.SetProjection(dem__prj)
    out_band = outds.GetRasterBand(1)
    out_band.WriteArray(result_array)    
    outds = None
if __name__ == "__main__":
    main()