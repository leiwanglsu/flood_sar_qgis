import ee

# Convert dB to power
def db_to_power(img):
    return ee.Image.constant(10).pow(img.divide(10))

# Convert power back to dB
def power_to_db(img):
    return ee.Image.constant(10).multiply(img.log10())

# Refined Lee filter in Python
def refined_lee(image):
    
    # Get band names
    band_names = image.bandNames()
    
    # Convert image from dB to power
    image = db_to_power(image)
    
    def apply_filter(b):
        img = image.select([b])
        
        # Set up 3x3 kernels
        weights3 = ee.List.repeat(ee.List.repeat(1, 3), 3)
        kernel3 = ee.Kernel.fixed(3, 3, weights3, 1, 1, False)
        
        mean3 = img.reduceNeighborhood(ee.Reducer.mean(), kernel3)
        variance3 = img.reduceNeighborhood(ee.Reducer.variance(), kernel3)
        
        # Use a sample of the 3x3 windows inside a 7x7 window to determine gradients and directions
        sample_weights = ee.List([
            [0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 1, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0]
        ])
        
        sample_kernel = ee.Kernel.fixed(7, 7, sample_weights, 3, 3, False)
        
        # Calculate mean and variance for the sampled windows
        sample_mean = mean3.neighborhoodToBands(sample_kernel)
        sample_var = variance3.neighborhoodToBands(sample_kernel)
        
        # Determine the 4 gradients
        gradients = sample_mean.select(1).subtract(sample_mean.select(7)).abs()
        gradients = gradients.addBands(sample_mean.select(6).subtract(sample_mean.select(2)).abs())
        gradients = gradients.addBands(sample_mean.select(3).subtract(sample_mean.select(5)).abs())
        gradients = gradients.addBands(sample_mean.select(0).subtract(sample_mean.select(8)).abs())
        
        # Find the maximum gradient
        max_gradient = gradients.reduce(ee.Reducer.max())
        
        # Create a mask for band pixels that are the maximum gradient
        gradmask = gradients.eq(max_gradient)
        gradmask = gradmask.addBands(gradmask)
        
        # Determine the 8 directions
        directions = sample_mean.select(1).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(7))).multiply(1)
        directions = directions.addBands(sample_mean.select(6).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(2))).multiply(2))
        directions = directions.addBands(sample_mean.select(3).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(5))).multiply(3))
        directions = directions.addBands(sample_mean.select(0).subtract(sample_mean.select(4)).gt(sample_mean.select(4).subtract(sample_mean.select(8))).multiply(4))
        directions = directions.addBands(directions.select(0).Not().multiply(5))
        directions = directions.addBands(directions.select(1).Not().multiply(6))
        directions = directions.addBands(directions.select(2).Not().multiply(7))
        directions = directions.addBands(directions.select(3).Not().multiply(8))
        
        # Mask all values that are not 1-8
        directions = directions.updateMask(gradmask)
        directions = directions.reduce(ee.Reducer.sum())
        
        # Sample stats and local noise variance
        sample_stats = sample_var.divide(sample_mean.multiply(sample_mean))
        sigmaV = sample_stats.toArray().arraySort().arraySlice(0, 0, 5).arrayReduce(ee.Reducer.mean(), [0])
        
        # Set up the 7x7 kernels for directional statistics
        rect_weights = ee.List.repeat(ee.List.repeat(0, 7), 3).cat(ee.List.repeat(ee.List.repeat(1, 7), 4))
        diag_weights = ee.List([
            [1, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 0, 0],
            [1, 1, 1, 0, 0, 0, 0],
            [1, 1, 1, 1, 0, 0, 0],
            [1, 1, 1, 1, 1, 0, 0],
            [1, 1, 1, 1, 1, 1, 0],
            [1, 1, 1, 1, 1, 1, 1]
        ])
        
        rect_kernel = ee.Kernel.fixed(7, 7, rect_weights, 3, 3, False)
        diag_kernel = ee.Kernel.fixed(7, 7, diag_weights, 3, 3, False)
        
        # Compute directional mean and variance
        dir_mean = img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel).updateMask(directions.eq(1))
        dir_var = img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel).updateMask(directions.eq(1))
        
        dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel).updateMask(directions.eq(2)))
        dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel).updateMask(directions.eq(2)))
        
        # Add the bands for rotated kernels
        for i in range(1, 4):
            dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
            dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), rect_kernel.rotate(i)).updateMask(directions.eq(2 * i + 1)))
            dir_mean = dir_mean.addBands(img.reduceNeighborhood(ee.Reducer.mean(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))
            dir_var = dir_var.addBands(img.reduceNeighborhood(ee.Reducer.variance(), diag_kernel.rotate(i)).updateMask(directions.eq(2 * i + 2)))
        
        # Collapse the stack into a single band image
        dir_mean = dir_mean.reduce(ee.Reducer.sum())
        dir_var = dir_var.reduce(ee.Reducer.sum())
        
        # Calculate the filtered value
        varX = dir_var.subtract(dir_mean.multiply(dir_mean).multiply(sigmaV)).divide(sigmaV.add(1.0))
        b = varX.divide(dir_var)
        
        return dir_mean.add(b.multiply(img.subtract(dir_mean))).arrayProject([0]).arrayFlatten([['sum']]).float()
    
    # Apply the filter to each band
    result = ee.ImageCollection(band_names.map(apply_filter)).toBands().rename(band_names)
    
    # Convert back from power to dB
    return power_to_db(result)

# Example usage:
# Assuming `image` is a properly initialized Earth Engine image
# filtered_image = refined_lee(image)
