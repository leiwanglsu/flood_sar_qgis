
import os
import numpy as np
from .gamma_fit import find_threshold,invpsi,fit,compute_bimodality

from osgeo import gdal, ogr, osr
from tqdm import tqdm
        
def main():
    import json,os
    launch_json = "multigamma.json"
    json_file_path = launch_json

    # Read the JSON file
    try:
        
        with open(json_file_path, 'r') as file:
            args = json.load(file)
            workspace = args["Workspace"]

            input_path = os.path.join(workspace,args['input image'])
            shapefile_path = os.path.join(workspace,args['regions'])
            init = args['init']
            point_shapefile_path = os.path.join(workspace,args['point_shapefile_path'])
            init = [float(i) for i in init.split()]
            alpha = np.array(init[0:2])
            rate = np.array(init[2:4])
 
    except:
        print("Error reading from the json file") 
           
        return
    bimodalFit(workspace=workspace,
               sarImage=input_path,
               regions=shapefile_path,
               gamma = init)
def bimodalFit(workspace,sarImage,regions,gamma):
    # read the shapefile
    print(f"bimodal: {workspace},{sarImage},{regions},{gamma}")
    shapefile_path = regions
    shapefile = ogr.Open(shapefile_path,0)
    layer = shapefile.GetLayer()
    src_srs = layer.GetSpatialRef()

    #Reading the raster data {input_path}
    
    # Open the raster image
    raster = gdal.Open(sarImage)
    geotransform = raster.GetGeoTransform()
    projection = raster.GetProjection()
    minX = geotransform[0]
    maxX = geotransform[0] + raster.RasterXSize * geotransform[1]
    minY = geotransform[3] + raster.RasterYSize * geotransform[5]
    maxY = geotransform[3]
    pixel_width = geotransform[1]
    pixel_height = abs(geotransform[5])
    # Create a spatial reference from the raster
    raster_srs = osr.SpatialReference()
    raster_srs.ImportFromWkt(projection)
    
    tmpfile = os.path.join(workspace,"tmp.tif")
    outshapefile = os.path.join(workspace,"threshold.shp")
    thresholds =[]
    BCs = []
    init = [float(i) for i in gamma.split()]
    alpha = np.array(init[0:2])
    rate = np.array(init[2:4])
    for feature in tqdm(layer,desc="Fitting bimodal distributions"):
        mean = feature.GetField("mean")
        geom = feature.GetGeometryRef()
       # Use gdal.Warp to clip the raster with the polygon and store the result in memory
        mem_driver = gdal.GetDriverByName('MEM')

        x_res = raster.RasterXSize,  # Replace with actual pixel width
        y_res = raster.RasterYSize  # Replace with actual pixel height
# Get the bounding box of the feature
        minX, maxX, minY, maxY = geom.GetEnvelope()

        # Use gdal.Warp to clip the raster with the polygon and store the result in memory
        options = gdal.WarpOptions(
            format='GTiff',
            cutlineDSName=shapefile_path,
            #cutlineLayer=layer.GetName(),
            cutlineWhere=f"FID={feature.GetFID()}",
            cropToCutline=True,
            #dstNodata=0,
            #dstSRS=projection,
            #srcSRS=src_srs.ExportToWkt(),  # Set source spatial reference from shapefile
            #outputBounds=(minX, minY, maxX, maxY),  # Set output bounds
            #xRes=x_res,  # Set pixel width
            #yRes=y_res   # Set pixel height
            )
        gdal.Warp(tmpfile, raster, options=options)
        clipped_raster = gdal.Open(tmpfile) 
            
        # Convert the clipped raster to a numpy array
        image= clipped_raster.GetRasterBand(1).ReadAsArray().flatten()
        clipped_raster = None
        os.remove(tmpfile)

        #print(image)
        BC = compute_bimodality(image)
        min_value = np.percentile(image, 0)
        max_value = np.percentile(image, 100)
        shift = min_value - 2
        shifted_image = image - shift
        new_alpha,new_rate,pi = fit(shifted_image, alpha,rate,np.array([mean, 1-mean]), k=2)
        if(np.isnan(alpha[0])):
            print("Cannot find a good fit to the data")
        #compute the threshold
        min_value = np.percentile(shifted_image, 0)
        max_value = np.percentile(shifted_image, 100)
        bins = np.linspace(min_value, max_value, 1000)
        try:
            index = find_threshold(bins,new_alpha,new_rate,pi)
                        
            if(index == None or index < 0):
                threshold = float('inf') 
            else:  
                threshold = bins[index] + shift
        except Exception as e:
            threshold = float('inf')    
        #write to the feature class 
        thresholds.append(threshold)
        BCs.append(BC)
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if driver is None:
        raise RuntimeError("ESRI Shapefile driver not available")

    # Remove the existing point shapefile if it exists
    point_ds = driver.CreateDataSource(outshapefile)
    point_layer = point_ds.CreateLayer("points", srs=src_srs, geom_type=ogr.wkbPoint)

    # Add fields to the point shapefile
    point_layer.CreateField(ogr.FieldDefn("id", ogr.OFTInteger))
    point_layer.CreateField(ogr.FieldDefn("threshold", ogr.OFTReal))
    point_layer.CreateField(ogr.FieldDefn("BC", ogr.OFTReal))
    # Add points (centroids) to the point shapefile
    shapefile = ogr.Open(shapefile_path,1)
    layer = shapefile.GetLayer()
    for i, polygon_feature in tqdm(enumerate(layer),desc="writing features"):
        # Get the centroid of the polygon
        geom = polygon_feature.GetGeometryRef()
        centroid = geom.Centroid()

        # Create a new point feature
        point_feature = ogr.Feature(point_layer.GetLayerDefn())
        point_feature.SetGeometry(centroid)
        point_feature.SetField("id", polygon_feature.GetFID())
        point_feature.SetField("threshold", thresholds[i])
        point_feature.SetField("BC", BCs[i])

        # Add the point feature to the point layer
        point_layer.CreateFeature(point_feature)
    point_ds = None
    shapefile = None
    raster = None

    return


if __name__ == "__main__":
    main()