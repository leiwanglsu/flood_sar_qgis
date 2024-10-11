"""
This script does terrain correction and sigma-lee filter for Sentinel-1 images
pip install earthengine-api
earthengine authenticate
"""
import ee
import math
def TerrainCorrection(image):
    img_geom = image.geometry()
    srtm = ee.Image('USGS/SRTMGL1_003').clip(img_geom)  # 30m SRTM
    sigma0_pow = ee.Image.constant(10).pow(image.divide(10.0))
    
    # 2.1.1 Radar geometry
    theta_i = image.select('angle')
    phi_i = ee.Terrain.aspect(theta_i)\
        .reduceRegion(reducer=ee.Reducer.mean(), geometry=theta_i.geometry(), scale=1000)\
        .get('aspect')
    
    # 2.1.2 Terrain geometry
    alpha_s = ee.Terrain.slope(srtm).select('slope')
    phi_s = ee.Terrain.aspect(srtm).select('aspect')
    
    # 2.1.3 Model geometry
    phi_r = ee.Image.constant(phi_i).subtract(phi_s)
    
    # Convert all to radians
    phi_r_rad = phi_r.multiply(math.pi / 180)
    alpha_s_rad = alpha_s.multiply(math.pi / 180)
    theta_i_rad = theta_i.multiply(math.pi / 180)
    ninety_rad = ee.Image.constant(90).multiply(math.pi / 180)
    
    # Slope steepness in range (eq. 2)
    alpha_r = (alpha_s_rad.tan().multiply(phi_r_rad.cos())).atan()
    
    # Slope steepness in azimuth (eq 3)
    alpha_az = (alpha_s_rad.tan().multiply(phi_r_rad.sin())).atan()
    
    # Local incidence angle (eq. 4)
    theta_lia = (alpha_az.cos().multiply((theta_i_rad.subtract(alpha_r)).cos())).acos()
    theta_lia_deg = theta_lia.multiply(180 / math.pi)
    
    # 2.2 Gamma_nought_flat
    gamma0 = sigma0_pow.divide(theta_i_rad.cos())
    gamma0dB = ee.Image.constant(10).multiply(gamma0.log10())
 
    
    # Volumetric Model
    nominator = (ninety_rad.subtract(theta_i_rad).add(alpha_r)).tan()
    denominator = (ninety_rad.subtract(theta_i_rad)).tan()
    vol_model = (nominator.divide(denominator)).abs()
    
    # Apply model
    gamma0_volume = gamma0.divide(vol_model)
    gamma0_volumeDB = ee.Image.constant(10).multiply(gamma0_volume.log10())
    
    
    return gamma0_volumeDB

def db_to_power(image):
    return ee.Image.constant(10).pow(image.divide(10.0))

def power_to_db(image):
    return ee.Image.constant(10).multiply(image.log10())

def refined_lee(img):
    
    # Set up 3x3 kernels 
    weights3 = ee.List.repeat(ee.List.repeat(1, 3), 3)
    kernel3 = ee.Kernel.fixed(3, 3, weights3, 1, 1, False)
    
    mean3 = img.reduceNeighborhood(ee.Reducer.mean(), kernel3)
    variance3 = img.reduceNeighborhood(ee.Reducer.variance(), kernel3)
    
    # Use a sample of the 3x3 windows inside a 7x7 windows to determine gradients and directions
    sample_weights = ee.List([
        [0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 1, 0, 1, 0], [0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 1, 0, 1, 0], [0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ])
    
    sample_kernel = ee.Kernel.fixed(7, 7, sample_weights, 3, 3, False)
    
    # Calculate mean and variance for the sampled windows and store as 9 bands
    sample_mean = mean3.neighborhoodToBands(sample_kernel)
    sample_var = variance3.neighborhoodToBands(sample_kernel)
    
    # Determine the 4 gradients for the sampled windows
    gradients = sample_mean.select(1).subtract(sample_mean.select(7)).abs()
    gradients = gradients.addBands(sample_mean.select(6).subtract(sample_mean.select(2)).abs())
    gradients = gradients.addBands(sample_mean.select(3).subtract(sample_mean.select(5)).abs())
    gradients = gradients.addBands(sample_mean.select(0).subtract(sample_mean.select(8)).abs())
    
    # And find the maximum gradient amongst gradient bands
    max_gradient = gradients.reduce(ee.Reducer.max())
    
    # Create a mask for band pixels that are the maximum gradient
    gradmask = gradients.eq(max_gradient)
    
    # Duplicate gradmask bands: each gradient represents 2 directions
    gradmask = gradmask.addBands(gradmask)
    
    # Determine the 8 directions
    directions = sample_mean.select(1).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(7))).multiply(1)
    directions = directions.addBands(sample_mean.select(6).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(2))).multiply(2))
    directions = directions.addBands(sample_mean.select(3).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(5))).multiply(3))
    directions = directions.addBands(sample_mean.select(0).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(8))).multiply(4))
    # The next 4 are the not() of the previous 4
    directions = directions.addBands(directions.select(0).Not().multiply(5))
    directions = directions.addBands(directions.select(1).Not().multiply(6))
    directions = directions.addBands(directions.select(2).Not().multiply(7))
    directions = directions.addBands(directions.select(3).Not().multiply(8))
    
    # Mask all values that are not 1-8
    directions = directions.updateMask(gradmask)
    
    # "Collapse" the stack into a single band image
    directions = directions.reduce(ee.Reducer.sum())
    
    sample_stats = sample_var.divide(sample_mean.multiply(sample_mean))
    
    # Calculate localNoiseVariance
    sigmaV = sample_stats.toArray().arraySort().arraySlice(0, 0, 5).arrayReduce(ee.Reducer.mean(), [0])
    
    # Set up the 7*7 kernels for directional statistics
    rect_weights = ee.List.repeat(ee.List.repeat(0, 7), 3).cat(ee.List.repeat(ee.List.repeat(1, 7), 4))
    diag_weights = ee.List([
        [1, 0, 0, 0, 0, 0, 0], [1, 1, 0, 0, 0, 0, 0], [1, 1, 1, 0, 0, 0, 0],
        [1, 1, 1, 1, 0, 0, 0], [1, 1, 1, 1, 1, 0, 0], [1, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 1, 1]
    ])
    
    rect_kernel = ee.Kernel.fixed(7, 7, rect_weights, 3, 3, False)
    diag_kernel = ee.Kernel.fixed(7, 7, diag_weights, 3, 3, False)
    
    # Create stacks for mean and variance using the original kernels. Mask with relevant direction.
    dir_mean = img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel).updateMask(directions.eq(1))
    dir_var = img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel).updateMask(directions.eq(1))
    
    dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel).updateMask(directions.eq(2)))
    dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel).updateMask(directions.eq(2)))
    
    for i in range(1, 4):
        dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
        dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
        dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))
        dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))
    
    # "Collapse" the stack into a single band image
    dir_mean = dir_mean.reduce(ee.Reducer.sum())
    dir_var = dir_var.reduce(ee.Reducer.sum())
    
    # Finally generate the filtered value
    varX = dir_var.subtract(dir_mean.multiply(dir_mean).multiply(sigmaV)).divide(sigmaV.add(1.0))
    b = varX.divide(dir_var)
    
    return power_to_db(dir_mean.add(b.multiply(img.subtract(dir_mean)))\
        .arrayProject([0])\
        .arrayFlatten([['sum']])\
        .float())
    



