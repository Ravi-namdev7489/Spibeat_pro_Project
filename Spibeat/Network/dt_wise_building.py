import geopandas as gpd
import pandas as pd
import os
import zipfile
import uuid


def process_dt_buildings_session(
    dt_shp_path,
    building_shp_path,
    output_base_folder,
    buffer_distance=200,
    dt_name_field="Name"
):

    unique_id = str(uuid.uuid4())
    output_folder = os.path.join(output_base_folder, unique_id)
    os.makedirs(output_folder, exist_ok=True)

    # ----------------------------------------
    # LOAD DATA
    # ----------------------------------------
    points = gpd.read_file(dt_shp_path)
    buildings = gpd.read_file(building_shp_path)

    if points.empty:
        raise Exception("DT shapefile is empty")

    if buildings.empty:
        raise Exception("Building shapefile is empty")

    if dt_name_field not in points.columns:
        raise Exception(f"Column '{dt_name_field}' not found in DT shapefile")

    if points.crs is None:
        raise Exception("DT shapefile CRS missing")

    if buildings.crs is None:
        raise Exception("Building shapefile CRS missing")

    # ----------------------------------------
    # CONVERT TO UTM (Meters)
    # Gurgaon/Haryana → UTM Zone 43N
    # ----------------------------------------
    points = points.to_crs(epsg=32643)
    buildings = buildings.to_crs(epsg=32643)

    selected_building_ids = set()
    final_selected_list = []

    # ----------------------------------------
    # MAIN LOOP
    # ----------------------------------------
    for idx, point in points.iterrows():

        dt_value = point[dt_name_field]
        dt_name = f"DT_{dt_value}"

        buffer_geom = point.geometry.buffer(float(buffer_distance))

        buffer_gdf = gpd.GeoDataFrame(
            [{"geometry": buffer_geom}],
            crs=points.crs
        )

        buildings_in_buffer = gpd.sjoin(
            buildings,
            buffer_gdf,
            how="inner",
            predicate="intersects"
        )

        buildings_in_buffer = buildings_in_buffer[
            ~buildings_in_buffer.index.isin(selected_building_ids)
        ]

        if buildings_in_buffer.empty:
            continue

        temp_selected = buildings_in_buffer.copy()
        selected_building_ids.update(temp_selected.index)

        if "index_right" in temp_selected.columns:
            temp_selected = temp_selected.drop(columns=["index_right"])

        out_file = os.path.join(output_folder, f"{dt_name}.shp")
        temp_selected.to_file(out_file)

        final_selected_list.append(temp_selected)

    if not final_selected_list:
        raise Exception("No buildings selected for any DT")

    # ----------------------------------------
    # MERGED OUTPUT
    # ----------------------------------------
    final_output = gpd.GeoDataFrame(
        pd.concat(final_selected_list, ignore_index=True),
        crs=points.crs
    )

    # Convert back to WGS84 for web preview
    final_output = final_output.to_crs(epsg=4326)

    merged_path = os.path.join(
        output_folder,
        "all_unique_selected_buildings.shp"
    )
    final_output.to_file(merged_path)

    # GeoJSON preview
    geojson_path = os.path.join(output_folder, "preview.geojson")
    final_output.to_file(geojson_path, driver="GeoJSON")

    # ZIP all shapefile parts
    zip_path = os.path.join(output_folder, "dt_building_output.zip")

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(output_folder):
            if file.endswith((".shp", ".shx", ".dbf", ".prj", ".cpg")):
                zipf.write(
                    os.path.join(output_folder, file),
                    arcname=file
                )

    return  zip_path