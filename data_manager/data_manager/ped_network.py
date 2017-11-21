import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point


def network_sidewalks(sidewalks, crossings, tolerance=1e-1):
    '''Create a network from (potentially) independently-generated sidewalks
    and crossings lines. Sidewalks will be split into multiple lines wherever
    their endpoints (nearly) intersect crossings on their same layer, within
    some distance tolerance.

    '''
    precision = 3
    ends = []
    for idx, row in crossings.iterrows():
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
            if (distance_along == 0.0) or (distance_along == line.length):
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
            splits.append(split)

    sidewalks_network = gpd.GeoDataFrame(splits)
    sidewalks_network.crs = sidewalks.crs

    return sidewalks_network


def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]
