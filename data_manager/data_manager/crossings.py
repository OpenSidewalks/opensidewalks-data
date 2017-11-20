import geopandas as gpd
import numpy as np
import networkx as nx

from crossify.intersections import group_intersections
from crossify.crossings import make_crossings as mc2


def make_graph(streets):
    '''Create a networkx MultiDiGraph, with intersections as nodes and streets
    as edges. It's assumed that the streets input GeoDataFrame has already
    split the streets by intersections such that the street lines extend from
    intersection to intersection as a single unit (no splits).

    '''
    # Create a MultiDiGraph from the streets, where the direction is in the
    # same direction as the street itself (first point = start node, last
    # point = end node). The DiGraph has data on the edges: 'geometry' is a
    # shapely.LineString of the street.

    # Note: streets should be in a projection in meters

    # Precision for rounding, in meters. 1 = nearest 10 centimeters.
    PRECISION = 2

    G = nx.MultiDiGraph()
    for idx, row in streets.iterrows():
        geometry = row['geometry']

        start = list(np.round(geometry.coords[0], PRECISION))
        end = list(np.round(geometry.coords[-1], PRECISION))

        start_node = str(start)
        end_node = str(end)

        G.add_node(start_node, x=start[0], y=start[1])
        G.add_node(end_node, x=end[0], y=end[1])
        G.add_edge(start_node, end_node, geometry=geometry)

    return G


def make_crossings(sidewalks, streets):
    '''Make street crossings using spatial data from sidewalk and street lines.
    Returns a GeoDataFrame of LineString geometries in the WGS84 projection.

    '''
    # Note: it's assumed that sidewalks and streets are in the same projection,
    # and that its units are meters

    # TODO: use crossify validation functions instead for things like 'layer'
    def validate_layer(gdf):
        copy = gdf.copy()

        def transform_layer(layer):
            if layer is np.nan:
                return 0
            try:
                return int(layer)
            except ValueError:
                return 0

        if 'layer' in gdf.columns:
            copy['layer'] = gdf['layer'].apply(transform_layer)
        else:
            copy['layer'] = 0
        return copy

    streets = validate_layer(streets)
    sidewalks = validate_layer(sidewalks)

    G = make_graph(streets)
    ixns = group_intersections(G)
    crossings = mc2(ixns, sidewalks)
    crossings.crs = streets.crs

    return crossings
