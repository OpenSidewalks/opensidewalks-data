import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from .utils import cut


def network_sidewalks(sidewalks, paths_list, tolerance=1e-1, precision=3):
    '''Create a network from (potentially) independently-generated sidewalks
    and other paths. Sidewalks will be split into multiple lines wherever
    their endpoints (nearly) intersect other paths on their same layer, within
    some distance tolerance.

    '''
    ends = []
    for paths in paths_list:
        for idx, row in paths.iterrows():
            ends.append(Point(np.round(row['geometry'].coords[0], precision)))
            ends.append(Point(np.round(row['geometry'].coords[-1], precision)))

    ends = gpd.GeoDataFrame(geometry=ends)
    ends['wkt'] = ends.geometry.apply(lambda x: x.wkt)
    ends = ends.drop_duplicates('wkt')
    ends = ends.drop('wkt', axis=1)

    splits = []
    for idx, row in sidewalks.iterrows():
        line = row['geometry']

        # Expand bounds by tolerance to catch everything in range, order is
        # left, bottom, right, top
        bounds = [
            line.bounds[0] - tolerance,
            line.bounds[1] - tolerance,
            line.bounds[2] + tolerance,
            line.bounds[3] + tolerance
        ]

        query = ends.sindex.intersection(bounds, objects=True)

        # Now iterate over and filter
        distances_along = []
        for q in query:
            idx = q.object
            point = ends.loc[idx, 'geometry']

            # Is the point actually within the tolerance distance?
            if point.distance(line) > tolerance:
                continue

            # Find closest point on line
            distance_along = line.project(point)

            # Did you find an endpoint?
            if (distance_along < 0.01) or \
               (distance_along >= (line.length - 0.01)):
                continue

            distances_along.append(distance_along)

        # Split
        lines = []
        line1 = line
        for distance in reversed(sorted(distances_along)):
            line1, line2 = cut(line1, distance)
            lines.append(line2)

        lines.append(line1)

        for line in lines:
            split = dict(row)
            split['geometry'] = line
            # Ignore incline for short segments near paths - these are
            # usually near intersections and are more flat on average.
            # (8 meters)
            if line.length < 8:
                split['incline'] = 0
            splits.append(split)

    sidewalks_network = gpd.GeoDataFrame(splits)
    sidewalks_network.crs = sidewalks.crs

    return sidewalks_network
