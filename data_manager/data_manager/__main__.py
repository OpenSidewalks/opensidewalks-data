'''Handle data fetching/cleaning tasks automatically. Reads and writes partial
builds using a provided directory on the host filesystem, using the `pathname`
argument.

'''

import json
import os
import shutil
from tempfile import mkdtemp

import click
import geopandas as gpd
import rasterio as rio
import sidewalkify

from .annotate import annotate_line_from_points
from .raster_interp import interpolated_value
from . import fetchers
from . import dems
from . import clean as sidewalk_clean
from . import make_crossings
from .standardize import standardize_df, assign_st_to_sw, whitelist_filter
# FIXME: refactor to be object-oriented on a per-dataset level. Classes
# implement methods for standardization, cleaning, etc.


def get_metadata(pathname):
    with open(os.path.join(pathname, 'city.json')) as f:
        return json.load(f)


def get_data(pathname, layername, category):
    path = os.path.join(pathname, category, '{}.geojson'.format(layername))
    return gpd.read_file(path)


def put_data(gdf, pathname, layername, category):
    directory = os.path.join(pathname, category)
    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = '{}.geojson'.format(layername)
    writepath = os.path.join(directory, filename)
    # write to temp dir and then move? Prevents loss of old data if write fails
    tempdir = mkdtemp()
    tempfile = os.path.join(tempdir, filename)

    try:
        gdf.to_file(tempfile, driver='GeoJSON')
    except Exception as e:
        shutil.rmtree(tempdir)
        raise e

    # Writing was successful, so move the file to the correct path
    shutil.move(tempfile, writepath)


def build_dir(pathname):
    return os.path.join(pathname, 'build')


@click.group()
def cli():
    pass


@cli.command()
@click.argument('pathname')
def fetch(pathname):
    metadata = get_metadata(pathname)
    layers = fetchers.fetch(metadata)
    # Iterate over each layer and write to file
    for name, gdf in layers.items():
        put_data(gdf, build_dir(pathname), name, 'original')


@cli.command()
@click.argument('pathname')
def fetch_dem(pathname):
    '''Fetch DEM (elevation) data for the area of interest. Data is output to
    pathname/dem/region, where region is e.g. n48w123.

    '''
    metadata = get_metadata(pathname)
    pathname = build_dir(pathname)
    outdir = os.path.join(pathname, 'dems')
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    click.echo('Reading in vector data...')
    layernames = metadata['layers'].keys()
    gdfs = [get_data(pathname, layername, 'original') for layername in
            layernames]

    click.echo('Downloading DEMs...')
    # FIXME: all DEMs should be merged into a single file at this point, but
    # currently aren't?
    dems.dem_workflow(gdfs, outdir, wgs84=True)


@cli.command()
@click.argument('pathname')
def standardize(pathname):

    # FIXME: reproject to UTF before doing mathy things
    click.echo('Standardizing data schema')

    click.echo('    Loading metadata...')
    with open(os.path.join(pathname, 'city.json')) as f:
        sources = json.load(f)
        layers = sources['layers'].keys()

        # Require streets input
        if 'streets' not in sources['layers']:
            raise ValueError('streets data source required')
        elif 'metadata' not in sources['layers']['streets']:
            raise ValueError('streets data source must have metadata')
        st_metadata = sources['layers']['streets']['metadata']

        # Require sidewalks input
        if 'sidewalks' not in sources['layers']:
            raise ValueError('sidewalks data source required')
        elif 'metadata' not in sources['layers']['sidewalks']:
            raise ValueError('sidewalks data source must have metadata')
        sw_metadata = sources['layers']['sidewalks']['metadata']

        # Require a foreign key between sidewalks and streets
        if ('pkey' not in st_metadata) or ('streets_pkey' not in sw_metadata):
            raise Exception('Sidewalks must have foreign key to streets'
                            'dataset and streets must have primary key')

    pathname = build_dir(pathname)
    click.echo('    Reading input data...')
    outpath = os.path.join(pathname, 'standardized')
    if not os.path.exists(outpath):
        os.mkdir(outpath)

    frames = {}
    for layer in sources['layers'].keys():
        frames[layer] = get_data(pathname, layer, 'original')

    click.echo('    Running standardization scripts...')
    # Standardize GeoDataFrame columns
    frames['streets'] = standardize_df(frames['streets'], st_metadata)
    frames['sidewalks'] = standardize_df(frames['sidewalks'], sw_metadata)

    # Require that streets to simple LineString geometries to simplify process
    # of assigning sidewalks to streets
    if (frames['streets'].geometry.type != 'LineString').sum():
        raise ValueError('streets dataset must be use simple LineStrings')

    # Filter streets to just those that matter for sidewalks (excludes, e.g.,
    # rail and highways).

    # Used to include 'motorway_link', but unfortunately the 'level' (z-level)
    # is not correctly logged, so it's impossible to know whether a given
    # highway entrance/exit segment is grade-separated. Erring on the side of
    # connectivity for now.
    st_whitelists = {
        'waytype': ['street']
    }
    frames['streets'] = whitelist_filter(frames['streets'], st_whitelists)

    # Assign street foreign key to sidewalks, remove sidewalks that don't refer
    # to a street
    click.echo('    Assigning sidewalks to streets...')
    frames['sidewalks'] = assign_st_to_sw(frames['sidewalks'],
                                          frames['streets'])

    for layer in layers:
        # Project to SRID 26910 (NAD83 for WA in meters)
        # FIXME: this shouldn't be hardcoded, should be determined from extent
        # May also need to ask for projection from user, if dataset doesn't
        # report it (or reports it incorrectly)
        # FIXME: Use non-NAD83?
        click.echo('    Reprojecting to srid 26910...')
        srid = '26910'
        frame = frames[layer]

        # Reprojection creates an error for empty geometries - they must
        # be removed first
        frame = frame.dropna(axis=0, subset=['geometry'])
        # frame = frame[~frame.geometry.is_empty]
        # frame = frame[~frame['geometry'].isnull()]

        # Reproject
        frame = frame.to_crs({'init': 'epsg:{}'.format(srid)})

        frames[layer] = frame

        # May need to overwrite files, but Fiona (used by GeoPandas) can't do
        # that sometimes, so remove first
        # click.echo('    Writing file...')
        # for filepath in os.listdir(outpath):
        #     if filepath.split(os.extsep, 1)[0] == layer:
        #         os.remove(os.path.join(outpath, filepath))

        # # Write back to the same files
        # # TODO: Make writing to file non-blocking (threads?)
    click.echo('done')

    streets = frames['streets']
    sidewalks = frames['sidewalks']

    click.echo('Assigning sidewalk side to streets...')
    streets = sidewalk_clean.sw_tag_streets(sidewalks, streets)
    # FIXME: Use UTM for meters-based calculations, wgs84 at all other times

    # FIXME: remove / turn into a debug mode
    sidewalks_wgs84 = sidewalks.to_crs({'init': 'epsg:4326'})
    bounds = (-122.3202, 47.6503, -122.3102, 47.6624)
    query = sidewalks_wgs84.sindex.intersection(bounds, objects=True)
    sidewalks = sidewalks.loc[[q.object for q in query]]

    put_data(streets, pathname, 'streets', 'standardized')
    put_data(sidewalks, pathname, 'sidewalks', 'standardized')
    if 'curbramps' in frames:
        put_data(frames['curbramps'], pathname, 'curbramps', 'standardized')


@cli.command()
@click.argument('pathname')
def redraw(pathname):
    click.echo('Reading in standardized data')
    streets = get_data(build_dir(pathname), 'streets', 'standardized')

    click.echo('Drawing sidewalks...')
    sidewalk_paths = sidewalkify.graph.graph_workflow(streets)
    sidewalks = sidewalkify.draw.draw_sidewalks(sidewalk_paths,
                                                crs=streets.crs)

    # Join back to street data to retrieve metadata used for crossings
    joined = sidewalks.merge(streets, left_on='street_id', right_on='id',
                             how='left', suffixes=['_sw', '_st'])
    sidewalks = joined[['geometry_sw', 'street_id', 'layer', 'pkey', 'id',
                        'forward']]
    sidewalks = sidewalks.rename(columns={
        'pkey': 'streets_pkey',
        'id': 'st_id',
        'geometry_sw': 'geometry'
    })
    sidewalks = gpd.GeoDataFrame(sidewalks)

    click.echo('Generating crossings...')
    crossings = make_crossings.make_graph(sidewalks, streets)

    # Ensure crs is set
    sidewalks.crs = streets.crs
    crossings.crs = streets.crs

    if crossings.empty:
        raise Exception('Generated no crossings')
    else:
        put_data(crossings, build_dir(pathname), 'crossings', 'redrawn')

    click.echo('Writing to file...')
    put_data(sidewalks, build_dir(pathname), 'sidewalks', 'redrawn')


@cli.command()
@click.argument('pathname')
def annotate(pathname):
    click.echo('Standardizing data schema')

    click.echo('    Loading metadata...')
    with open(os.path.join(pathname, 'city.json')) as f:
        sources = json.load(f)

        frames = {}
        layers = ['sidewalks', 'crossings']
        for layer in layers:
            frames[layer] = get_data(build_dir(pathname), layer, 'redrawn')

        # Also add crossings...
        frames['crossings'] = get_data(build_dir(pathname), 'crossings',
                                       'redrawn')

        # Add incline info to sidewalks, crossings
        # Read in DEM
        def interp_line(row):
            geom = row['geometry']
            x1, y1 = geom.coords[0][0], geom.coords[0][1]
            x2, y2 = geom.coords[-1][0], geom.coords[-1][1]
            start = interpolated_value(x1, y1, dem, dem_arr)
            end = interpolated_value(x2, y2, dem, dem_arr)
            incline = (end - start) / row['length']

            return incline

        dem_path = os.path.join(pathname, 'build', 'dems', 'merged.tif')

        with rio.open(dem_path) as dem:
            click.echo('    Calculating inclines...')
            # TODO: put elevation stuff in its own function
            # FIXME: Too much conversion between latlon and UTM!
            # TODO: Use sample to read data from disk rather than in-memory
            dem_arr = dem.read(1)

            sidewalks = frames['sidewalks'].to_crs({'init': 'epsg:26910'})
            crossings = frames['crossings'].to_crs({'init': 'epsg:26910'})
            frames['sidewalks']['length'] = sidewalks.geometry.length
            frames['crossings']['length'] = crossings.geometry.length

            sidewalks_demcrs = frames['sidewalks'].to_crs(dem.crs)
            crossings_demcrs = frames['crossings'].to_crs(dem.crs)

            sw_incline = sidewalks_demcrs.apply(interp_line, axis=1)
            cr_incline = crossings_demcrs.apply(interp_line, axis=1)

            frames['sidewalks']['incline'] = sw_incline
            frames['crossings']['incline'] = cr_incline

            put_data(frames['sidewalks'], build_dir(pathname), 'sidewalks',
                     'annotated')
            put_data(frames['crossings'], build_dir(pathname), 'crossings',
                     'annotated')

        annotations = sources.get('annotations')
        if annotations is not None:
            click.echo('Annotating...')
            for name, annotation in annotations.items():
                # TODO: download all files at the beginning
                # Fetch the annotations
                click.echo('Downloading {}...'.format(name))
                url = annotation['url']
                click.echo(url)
                gdf = fetchers.fetch_shapefile(url, annotation['shapefile'])

                # Reproject
                gdf = gdf.to_crs({'init': 'epsg:26910'})

                # Apply appropriate functions, overwrite layers in 'clean' dir
                # FIXME: this is hardcoded. Might as well just have a
                # 'curb ramps' flag instead.
                crs = gdf.crs
                annotate_line_from_points(frames['crossings'], gdf,
                                          annotation['default_tags'])
                frames['crossings'].crs = crs
                put_data(frames['crossings'], build_dir(pathname), 'crossings',
                         'annotated')


@cli.command()
@click.argument('pathname')
def finalize(pathname):
    click.echo('Finalizing data')
    frames = {}
    layers = ['sidewalks', 'crossings']
    for layer in layers:
        frames[layer] = get_data(build_dir(pathname), layer, 'annotated')

    # Also add crossings...
    frames['crossings'] = get_data(build_dir(pathname), 'crossings',
                                   'annotated')

    # Reduce columns via whitelist logic
    sw_crs = frames['sidewalks'].crs
    cr_crs = frames['crossings'].crs

    sidewalks_cols = ['geometry', 'incline']
    crossings_cols = ['geometry', 'incline', 'marked']
    frames['sidewalks'] = gpd.GeoDataFrame(frames['sidewalks'][sidewalks_cols])
    frames['crossings'] = gpd.GeoDataFrame(frames['crossings'][crossings_cols])
    frames['sidewalks'].crs = sw_crs
    frames['crossings'].crs = cr_crs

    for name, gdf in frames.items():
        gdf_wgs84 = gdf.to_crs({'init': 'epsg:4326'})
        put_data(gdf_wgs84, pathname, name, 'data')


@cli.command()
@click.argument('pathname')
@click.pass_context
def fetch_all(ctx, pathname):
    ctx.forward(fetch)
    ctx.forward(fetch_dem)


@cli.command()
@click.argument('pathname')
@click.pass_context
def all(ctx, pathname):
    ctx.forward(fetch)
    ctx.forward(fetch_dem)
    ctx.forward(standardize)
    ctx.forward(redraw)
    ctx.forward(annotate)
    ctx.forward(finalize)


if __name__ == '__main__':
    cli()
