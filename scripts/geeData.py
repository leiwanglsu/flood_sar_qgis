"""
This script help user obtain jrc and sentinel-1 images from Google Earth Engine by user specified extent and time.
Images will be uploaded by Google to user's Google drive. 
Authentication is need 

"""
import ee
import os,json
from .gee_s1_lee import refined_lee

def main():


    try:
        ee.Initialize()
        
    except Exception as e:
        print(e)
        ee.Authenticate()
        ee.Initialize()

    # Getting the parameters from json
    base_name, _ = os.path.splitext(__file__)
    launch_json = base_name + '.json'
    json_file_path = launch_json

    # Read the JSON file
    try:
        with open(json_file_path, 'r') as file:
            args = json.load(file)
            workspace = args["Workspace"]
            extent_gcs = args['extent gcs[x1,y1,x2,y2]']
            url_jrc = args["url jrc"] #give an empty url if the image is not needed
            jrc_band = args['jrc band']
            url_s1 = args['url Sentinel-1'] #give an empty url if the image is not needed
            s1_band = args['Sentinel-1 band']
            s1_date = args["Sentinel-1 date[yyyy-mm-dd,yyyy-mm--dd]"].split(",")
            crs = args['Coordinate system'] #e.g. 'EPSG:32119'
            download_s1 = args["Download S1"]
            download_jrc = args["Download jrc"]
    except Exception as e:
        print(e)    
        return
    getGeeData(workspace,extent_gcs,s1_date,crs,url_jrc,url_s1,download_s1,download_jrc)
    
def getGeeData(workspace,extent_gcs,s1_date,crs,url_jrc="JRC/GSW1_4/GlobalSurfaceWater",jrc_band = "occurrence",
               s1_band = "VV", url_s1="COPERNICUS/S1_GRD",download_s1=True,download_jrc=True):

    numbers = extent_gcs.split(',')
    s1_date = s1_date.split(',')

    # Assign the extracted numbers to variables
    x1, y1, x2, y2 = map(float, numbers)
    bbox = ee.Geometry.BBox(x1,y1,x2,y2)
    
    # send the task for jrc on gee for processing. Establish a watching thread to update the status until the task is completed
    if(url_jrc != ""):
        try:
            datasetJRC = ee.Image(url_jrc).select(jrc_band).clip(bbox)
            if download_jrc:
                task = ee.batch.Export.image.toDrive(
                    image= datasetJRC,
                    description= 'JCRwaterpixels',
                    region= bbox,
                    folder= 'AnyFolder',
                    scale= 10,
                    fileFormat= 'GeoTIFF',
                    maxPixels= 3784216672400,
                    crs= crs
                    )
                task.start()
                print(f"Export task started with ID: {task.id}")
                print(f"Export destination: JCRwaterpixels.tif in AnyFolder")
  
        except Exception as e:
            print(e)
    if(url_s1 != ""):

        s1ImgC = ee.ImageCollection(url_s1).select([s1_band,"angle"]) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filterBounds(bbox) \
            .filterDate(s1_date[0],s1_date[1])
        # Function to calculate intersection area.
        
        def calculate_intersection_area(image):
            intersection = image.geometry().intersection(bbox, ee.ErrorMargin(1))
            intersection_area = intersection.area()
            return image.set('intersection_area', intersection_area)

        # Map the function over the filtered collection.
        with_area = s1ImgC.map(calculate_intersection_area)

        # Sort the collection by the intersection area.
        sorted_collection = with_area.sort('intersection_area', False)
        s1Img = sorted_collection.first()
        metadata = s1Img.getInfo()
        with open(os.path.join(workspace,'s1_metadata.json'), 'w') as json_file:
            json.dump(metadata, json_file, indent=4)
            print(f"Sentinel-1 image metadata is written to s1_metadata.json")
        s1Img = s1Img.clip(bbox).toFloat()
        s1Img = refined_lee(s1Img).select(s1_band)

        if download_s1:
            #s1Img = TerrainCorrection(s1Img)
            taskS1 = ee.batch.Export.image.toDrive(
                image= s1Img,
                description= 'S1_Lee_filter',
                region= bbox,
                folder= 'AnyFolder',
                scale= 10,
                fileFormat= 'GeoTIFF',
                maxPixels= 3784216672400,
                crs= crs
                )
            taskS1.start()
            print(f"Export task started with ID: {taskS1.id}")
            print(f"Export destination: s1_Lee_filter.tif in AnyFolder")
if __name__ == "__main__":
    main()