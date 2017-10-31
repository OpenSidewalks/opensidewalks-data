from io import BytesIO
import os
import tempfile
import shutil
from zipfile import ZipFile

import click
import geopandas as gpd
import requests


def fetch_shapefile(url, shp_path, bounds=None):
    # Download based on source.json layer url
    response = requests.get(url)
    tempdir = tempfile.mkdtemp()
    try:
        archive = ZipFile(BytesIO(response.content))
        archive.extractall(tempdir)
        shp_path = os.path.join(tempdir, '{}.shp'.format(shp_path))

        if not os.path.isfile(shp_path):
            raise Exception('Could not find matching files in zip archive.')

        gdf = gpd.read_file(os.path.join(tempdir, shp_path))
    finally:
        shutil.rmtree(tempdir)
    # Remove invalid geometries, as they will create invalid GeoJSON and break
    # fiona
    gdf = gdf[~gdf.geometry.isnull()]
    gdf = gdf[~gdf.geometry.is_empty]
    # Convert to wgs84 and require that values be within the bounding box
    gdf = gdf.to_crs({'init': 'epsg:4326'})
    if bounds is not None:
        query = gdf.sindex.intersection(bounds, objects=True)
        gdf = gdf.loc[[q.object for q in query]]

    return gdf


def fetch(metadata):
    layers = {}
    # FIXME: do this asynchronously - the slowest part is often waiting for the
    # server to respond. If multiprocessing is used, will be compatible with
    # Python 2 and Python 3
    for name, layer in metadata['layers'].items():
        click.echo('Downloading {}...'.format(name))
        url = layer['url']
        click.echo(url)
        layers[name] = fetch_shapefile(url, layer['shapefile'],
                                       metadata['bounds'])

    return layers
