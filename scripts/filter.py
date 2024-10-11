import os
from osgeo import gdal,ogr, osr
import json
import numpy as np
def main():
    launch_json = "filter.json"
    json_file_path = launch_json
    # Read the JSON file
    with open(json_file_path, 'r') as file:
        args = json.load(file)
    workspace = args['Workspace']
    input_shapefile = os.path.join(workspace,args["shapefile_path"])
    output_shapefile = os.path.join(workspace,args["output_path"])
    
def filterOutliers(workspace, threshold_points,BC):
# turn on GDAL exceptions to avoid deprecation warning
    gdal.UseExceptions()
    ogr.UseExceptions()
    # Open the input shapefile
    output_shapefile = os.path.join(workspace,"threshold_filtered.shp")
    driver = ogr.GetDriverByName('ESRI Shapefile')
    input_ds = driver.Open(threshold_points, 0)  # 0 means read-only
    if not input_ds:
        raise RuntimeError(f"Unable to open input shapefile: {threshold_points}")

    input_layer = input_ds.GetLayer()
    #calculate the mean and standard deviation
    values = []
    for feature in input_layer:
        value = feature.GetField('threshold')
        if value is not None and value != float('inf'):
            values.append(value)
    
    # Convert the list to a numpy array
    values = np.array(values, dtype=np.float32)
    # Calculate mean and standard deviation
    mean_value = np.mean(values)
    std_deviation = np.std(values)
    threshold_u25 = mean_value + std_deviation * 1.5
    threshold_l25 = mean_value - std_deviation * 1.5
    threshold_u3 = mean_value + std_deviation * 2
    threshold_l3 = mean_value - std_deviation * 2
    sql_query = f"(BC > {BC} and (threshold > {threshold_l3} and threshold <  {threshold_u3})) or (BC < {BC} and (threshold > {threshold_l25} and threshold < {threshold_u25}))"
    # Execute the SQL query
    print(f"Executing query {sql_query}")
    input_ds.ExecuteSQL(f"SELECT * FROM {input_layer.GetName()} WHERE {sql_query}")
    print(sql_query)
    # Check if the output shapefile already exists and delete it if necessary
    if os.path.exists(output_shapefile):
        driver.DeleteDataSource(output_shapefile)

    # Create the output shapefile
    output_ds = driver.CreateDataSource(output_shapefile)
    # Get the spatial reference from the input layer
    spatial_ref = input_layer.GetSpatialRef()

    # Create the output layer with the same geometry type and spatial reference as the input
    output_layer = output_ds.CreateLayer(input_layer.GetName(), spatial_ref, input_layer.GetGeomType())
    
    # Copy the fields from the input layer to the output layer
    layer_defn = input_layer.GetLayerDefn()
    for i in range(layer_defn.GetFieldCount()):
        field_defn = layer_defn.GetFieldDefn(i)
        output_layer.CreateField(field_defn)

    # Get the features from the input layer that match the SQL query and add them to the output layer
    selected_features = input_ds.ExecuteSQL(f"SELECT * FROM {input_layer.GetName()} WHERE {sql_query}")
    for feature in selected_features:
        output_layer.CreateFeature(feature)
    print(f"Shapefile written {output_shapefile}")
    # Cleanup
    input_ds.ReleaseResultSet(selected_features)
    input_ds = None
    output_ds = None

# Example usage



if __name__ == "__main__":
    main()