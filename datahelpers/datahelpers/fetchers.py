from io import BytesIO
import os
import tempfile
import shutil
from zipfile import ZipFile

import geopandas as gpd
import requests


def fetch_shapefile(url, unzipped_path, bounds=None):
    # Download based on source.json layer url
    tempdir = tempfile.mkdtemp()
    shp_filename = os.path.basename(unzipped_path)
    shp_path = os.path.join(tempdir, shp_filename)

    fetch_and_unzip(url, unzipped_path, shp_path)

    gdf = gpd.read_file(shp_path)

    # Remove invalid geometries, as they will create invalid GeoJSON and break
    # fiona
    gdf = gdf[~gdf.geometry.isnull()]
    gdf = gdf[~gdf.geometry.is_empty]
    # Convert to wgs84 and require that values be within the bounding box
    gdf = gdf.to_crs(4326)
    if bounds is not None:
        hits = list(gdf.sindex.intersection(bounds))
        gdf = gdf.iloc[hits]

    return gdf


def fetch_gdb(url, expanded_path, destination, bounds=None):
    fetch_and_unzip(url, expanded_path, destination)
    gdf = gpd.read_file(destination)

    # Remove invalid geometries, as they will create invalid GeoJSON and break
    # fiona
    gdf = gdf[~gdf.geometry.isnull()]
    gdf = gdf[~gdf.geometry.is_empty]
    # Convert to wgs84 and require that values be within the bounding box
    gdf = gdf.to_crs(4326)
    if bounds is not None:
        hits = list(gdf.sindex.intersection(bounds))
        gdf = gdf.iloc[hits]

    return gdf


def fetch_and_unzip(url, expanded_path, destination):
    response = requests.get(url)
    tempdir = tempfile.mkdtemp()
    try:
        archive = ZipFile(BytesIO(response.content))
        archive.extractall(tempdir)
        unzipped_path = os.path.join(tempdir, expanded_path)

        if not os.path.exists(unzipped_path):
            raise Exception('Could not find matching files in zip archive.')

        shutil.move(unzipped_path, destination)
    finally:
        shutil.rmtree(tempdir)
