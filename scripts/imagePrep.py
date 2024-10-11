import rasterio
from rasterio.merge import merge
from rasterio.windows import from_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling
import os
from rasterio.mask import mask
from shapely.geometry import box

def imagePrep(sarImages,jrcImg, workspace, threshold, lower_left, upper_right):
    """
    Clip and mosaic images and convert the water image to bindary
    jrcImg: the input JRCWater image of "occurrence" (0-100)
    workspace: a location to store images
    threshold: the threshold to classify the jrciImg to binary, e.g.20
    lower_left: the lower left corner of the extent
    upper_right: the upper right corner of the extent (use the native coordinate system of the image)
    for the coordiinates, you can use qgis to read from the map
    *sarImages: a tuple of sar images
    """
    min_x, min_y = map(float,lower_left.split(','))
    max_x, max_y = map(float,upper_right.split(','))

    clip_bounds = (min_x, min_y, max_x, max_y)  # Example: (-50, -20, -30, 0)
 # Working with the JRC image (thresholding and clip)
    threshold_value = int(threshold)
    with rasterio.open(jrcImg) as src:
    
        # Apply the threshold to create a binary image
        # Values greater than the threshold become 1 (white), others become 0 (black)

        bbox = box(*clip_bounds)

        clipped_image, clipped_transform = mask(src,[bbox], crop=True, nodata=0)
        
        # Update the clipped image to match the binary transformation
        clipped_image[clipped_image <= threshold_value] = 0
        clipped_image[clipped_image > threshold_value] = 1

        # Define metadata for the new image
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": clipped_image.shape[1],
            "width": clipped_image.shape[2],
            "transform": clipped_transform
        })

        # Save the binary image to a new file
        jrc_path = os.path.join(workspace,"temp.tif")
        with rasterio.open(jrc_path, 'w', **out_meta) as dst:
            dst.write(clipped_image[0,:,:].astype(rasterio.uint8), 1)  # Save as unsigned 8-bit (0 or 1 values)
            
    # Working with the sar images        
            
    if(len(sarImages) > 1):
        print("Mosaicing multiple images")
        sars = [rasterio.open(image_path) for image_path in sarImages]
        mosaic_array, out_transform = merge(sars)
        profs = [src.profile for src in sars]
        profile = profs[0]
        window = from_bounds(clip_bounds[0], clip_bounds[1], clip_bounds[2], clip_bounds[3], out_transform)
        mosaic_clipped = mosaic_array[:, int(window.row_off):int(window.row_off + window.height), int(window.col_off):int(window.col_off + window.width)]

        profile.update({
            'height': mosaic_clipped.shape[1],
            'width': mosaic_clipped.shape[2],
            'transform': rasterio.windows.transform(window, out_transform)
        })
        sar_path = os.path.join(workspace,"sar.tif")
        with rasterio.open(sar_path, 'w', **profile) as dst:
            dst.write(mosaic_clipped)
    else:
        sar = rasterio.open(sarImages[0]) 
        profile = sar.profile
        sar_path = os.path.join(workspace,"sar.tif")
        with rasterio.open(sar_path, 'w', **profile) as dst:
            dst.write(sar)
        
    # resampling to align the raster cells
    target_raster = rasterio.open(sar_path)
    src = rasterio.open(jrc_path)

    # Get target raster properties
    target_transform = target_raster.transform
    target_crs = target_raster.crs
    target_width = target_raster.width
    target_height = target_raster.height
    
    # Calculate transform and new dimensions based on the target raster
    transform, width, height = calculate_default_transform(
        src.crs, target_crs, src.width, src.height, *src.bounds, dst_width=target_width, dst_height=target_height
    )
    
    # Create a new profile (metadata) for the aligned image
    profile = src.profile
    profile.update({
        'crs': target_crs,
        'transform': transform,
        'width': width,
        'height': height
    })
  
    new_jrc_path = os.path.join(workspace,"jrc_watermask.tif")
    # Open a new file to write the aligned image
    with rasterio.open(new_jrc_path, 'w', **profile) as dst:
        for i in range(1, src.count + 1):  # Loop through each band
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=Resampling.nearest  # Use nearest neighbor resampling, or choose another method
            )
    target_raster.close()
    src.close()
    os.remove(jrc_path)
