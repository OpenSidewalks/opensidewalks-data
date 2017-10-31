from io import BytesIO
import os
import shutil
import tempfile
import zipfile

import click
import geopandas as gpd
import rasterio
from rasterio import Affine
from rasterio.warp import calculate_default_transform, reproject, RESAMPLING
import requests
from shapely import geometry


def gdfs_bounds(gdfs):
    # Use a LineString as storage format for bounding box - can group together
    # in GeoSeries and use total_bounds to get bounding box of the whole set
    lines = []
    for gdf in gdfs:
        # Filter out invalid geometries
        # FIXME: This should be done more carefully - e.g. compare data to
        # exact dimensions of the projection
        crs = gdf.crs

        def valid(bounds, limit=1e10):
            for bound in bounds:
                if bound > limit or bound < (-1 * limit):
                    return False
            return True

        gdf = gdf.dropna(axis=0, subset=['geometry'])
        df_bounds = gdf.loc[gdf.bounds.apply(valid, axis=1)].total_bounds
        line = geometry.LineString([(df_bounds[0], df_bounds[1]),
                                    (df_bounds[2], df_bounds[3])])
        line = gpd.GeoSeries([line])
        line.crs = crs
        lines.append(line.to_crs({'init': 'epsg:4326'}).iloc[0])

    bounds = gpd.GeoSeries(lines).total_bounds
    return bounds


def which_regions(bounds):
    '''Return the NED dataset DEMs to be returned - in the format of e.g.
    n48w123.

    :param bounds: Bounding box (s, w, n, e) of the region of interest. Must be
                   in SRID 4326.
    :type bounds: tuple

    '''
    regions = []
    # NED naming scheme orders lons from negative to positive
    for i in range(-180, 180):
        # NED naming scheme orders lons from positive to negative
        for j in reversed(range(-89, 91)):
            geom = geometry.Polygon([(i, j - 1), (i, j), (i + 1, j),
                                     (i + 1, j - 1)])

            regions.append({
                'geometry': geom,
                'lon': str(abs(i)),
                'lat': str(abs(j)),
                'ew': 'w' if i < 0 else 'e',
                'ns': 's' if j < 0 else 'n'
            })

    regions = gpd.GeoDataFrame(regions)
    regions.crs = {'init': 'epsg:4326'}

    rect = geometry.Polygon([
        (bounds[0], bounds[1]),
        (bounds[0], bounds[3]),
        (bounds[2], bounds[3]),
        (bounds[2], bounds[1]),
        (bounds[0], bounds[1])
    ])

    regionlist = []
    for index, row in regions.loc[regions.intersects(rect)].iterrows():
        region = ''.join([row.ns, row.lat, row.ew, row.lon])
        regionlist.append(region)

    return regionlist


def fetch_dem(region):
    '''Fetch DEM (elevation) data for the city of interest.'''
    # Base url for DEM data
    data_url = ('https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/'
                'ArcGrid/{region}.zip')

    # Actually download the files
    tempdir = tempfile.mkdtemp()

    # FIXME: turn all of these click.echos into logger messages that get
    # caught by a listener at the top level (click should not be involved
    # anywhere except main.py).
    click.echo('Downloading {}...'.format(region))
    url = data_url.format(region=region)
    # TODO: add progress bar using stream argument + click progress bar
    response = requests.get(url)
    response.raise_for_status()
    zipper = zipfile.ZipFile(BytesIO(response.content))

    extract_dir = 'grd{}_13/'.format(region)

    # FIXME: DEMs are huge and should be stored in a standard location, not
    # temporary dirs. Temporary dirs will blow up in size and probably blow up
    # other things.
    # FIXME: check to see if this dataset was already downloaded. If so, skip
    # everything!
    for path in zipper.namelist():
        if extract_dir in path:
            if extract_dir == path:
                continue
            extract_path = os.path.join(tempdir, os.path.basename(path))
            with zipper.open(path) as f:
                with open(extract_path, 'wb') as g:
                    g.write(f.read())

    # Read into memory
    dem = rasterio.open(os.path.join(tempdir, 'w001001.adf'))
    return dem


def fetch_dems(gdfs):
    bounds = gdfs_bounds(gdfs)
    regions = which_regions(bounds)
    dems = {}
    for region in regions:
        dems[region] = fetch_dem(region)
    return dems


def dem_to_wgs84(src, path, scale=1.0):
    dst_crs = 'EPSG:4326'

    affine, width, height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)
    kwargs = src.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': affine,
        'affine': affine,
        'width': round(width * scale),
        'height': round(height * scale),
        'driver': 'GTiff',
        'compress': 'lz2'
    })

    with rasterio.open(path, 'w', **kwargs) as dst:
        for i in range(1, src.count + 1):
            aff = src.affine
            newaff = Affine(aff.a / scale, aff.b, aff.c,
                            aff.d, aff.e / scale, aff.f)
            reproject(
                source=rasterio.band(src, i),
                destination=rasterio.band(dst, i),
                src_transform=aff,
                src_crs=src.crs,
                dst_transform=newaff,
                dst_crs=dst_crs,
                resampling=RESAMPLING.cubic)
    src.close()
    dst.close()


def dem_workflow(gdfs, outdir, wgs84=False):
    # Fetch the DEMS based on shapefiles for which DEMs are needed
    dems = fetch_dems(gdfs)

    # Reproject to wgs84 to keep things standardize, write to standard
    # location, and clean up the temporary dir
    for region, dem in dems.items():
        try:
            path = os.path.join(outdir, '{}.tif'.format(region))
            if wgs84:
                dem_to_wgs84(dem, path, 1.0)
            else:
                bounds = dem.bounds
                kwargs = {
                    'width': dem.width,
                    'height': dem.height,
                    'count': dem.count,
                    'dtype': dem.dtypes[0],
                    'transform': Affine(
                      (bounds.right - bounds.left) / dem.width,
                      0,
                      bounds.left,
                      0,
                      -1 * (bounds.top - bounds.bottom) / dem.height,
                      bounds.top
                    ),
                    'crs': dem.crs,
                    'driver': 'GTiff',
                    'compress': 'lzw'
                }
                # TODO: handle multiple bands?
                click.echo('    Writing to file...')
                with rasterio.open(path, 'w', **kwargs) as dst:
                    band = dem.read(1)
                    dst.write(band, 1)
                    # Remove from memory
                    # TODO: Operate on streams (minimize memory) / GDAL tools?
                    del band
                click.echo('    Done.')
        finally:
            dem.close()
            shutil.rmtree(os.path.dirname(dem.name))
