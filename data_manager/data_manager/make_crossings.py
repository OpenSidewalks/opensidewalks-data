import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import affinity, geometry


PARALLEL_MIN = np.pi * 3 / 4
PARALLEL_MAX = np.pi * 5 / 4
MAX_DIST = 30  # in meters
SNAP_DIST = 3


def make_graph(sidewalks, streets):
    #
    # Strategy:
    #
    # 1) Identify all corners that should (possibly) be connected to others
    # 2) Identify all nearby sidewalks within some threshold
    # 3) Find nearest point on nearby sidewalks, draw a line, calculate
    #    distance
    # 4) If the endpoint of that sidewalk is close to that distance, just
    #    connect to that.
    # 5) Remove crossings that cross more than one street on same vertical
    #    level.
    # 6) Detect diagonal crossings -e.g. two nearby T intersections? Maybe use
    #    angles of intersections + angle of crossing?

    #
    # Implementation - identifying corners
    # Corners are where:
    # 1) Sidewalks end (endpoints)
    # 2) The angle of endpoints meeting is greater than 45 degrees (i.e.
    #    not parallel)

    # FIXME: this is redundant with the cleaning scripts - share the data?
    #       - Would also be able to keep the association at connected points
    starts = sidewalks.geometry.apply(lambda x: geometry.Point(x.coords[0]))
    ends = sidewalks.geometry.apply(lambda x: geometry.Point(x.coords[-1]))
    n = sidewalks.shape[0]
    ends = gpd.GeoDataFrame({
        'sw_index': 2 * list(sidewalks.index),
        'streets_pkey': 2 * list(sidewalks['streets_pkey']),
        'st_id': 2 * list(sidewalks['st_id']),
        'forward': 2 * list(sidewalks['forward']),
        'endtype': n * ['start'] + n * ['end'],
        'layer': 2 * list(sidewalks['layer']),
        'geometry': pd.concat([starts, ends])
    })

    ends.reset_index(drop=True, inplace=True)
    # Initialize the spatial index(s) (much faster distance queries)
    ends.sindex
    streets.sindex

    ends['wkt'] = ends.apply(lambda r: r.geometry.wkt, axis=1)

    grouped = ends.groupby('wkt')

    def extract(group):
        geom = group.iloc[0]['geometry']
        sw1_index = group.iloc[0]['sw_index']
        sw1type = group.iloc[0]['endtype']
        if group.shape[0] > 1:
            sw2_index = group.iloc[1]['sw_index']
            sw2type = group.iloc[1]['endtype']
        else:
            sw2_index = pd.np.nan
            sw2type = pd.np.nan
        # FIXME: there is probably a faster way to do this
        return gpd.GeoDataFrame({
            'geometry': [geom],
            'sw1_index': [sw1_index],
            'sw1type': [sw1type],
            'sw2_index': [sw2_index],
            'sw2type': [sw2type]
        })

    corners = grouped.apply(extract)
    corners.reset_index(drop=True, inplace=True)
    corners.sindex

    # Calculate azimuth between paired ends, if appropriate
    def azimuth(p1, p2):
        '''Azimuth function - calculates angle between two points in radians
        where 0 = north, in clockwise direction.'''
        radians = np.arctan2(p2[0] - p1[0], p2[1] - p1[1])
        if radians < 0:
            radians += 2 * np.pi
        return radians

    def azimuth_sw(sw, endtype):
        if endtype == 'start':
            p1 = sw['geometry'].coords[1]
            p2 = sw['geometry'].coords[0]
        else:
            p1 = sw['geometry'].coords[-2]
            p2 = sw['geometry'].coords[-1]

        return azimuth(p1, p2)

    def sw_is_parallel(end):
        if pd.isnull(end['sw2_index']):
            return False
        endtype1 = end['sw1type']
        endtype2 = end['sw2type']
        azimuth1 = azimuth_sw(sidewalks.loc[end['sw1_index']], endtype1)
        azimuth2 = azimuth_sw(sidewalks.loc[int(end['sw2_index'])],
                              endtype2)
        # TODO: consider using unit vectors
        # These azimuths are pointed towards one another if parallel. Find
        # the deviation from 'towards one another-ness', i.e. deviation
        # from 180 degrees (or pi)
        # if variation is 45 degrees, then look for 135 to 225 degrees
        # (3/4 pi and 5/4 pi)

        diff = azimuth2 - azimuth1

        if PARALLEL_MIN < abs(diff) < PARALLEL_MAX:
            # Skip if they're too parallel
            return True
        else:
            return False

    valid_corners = corners.loc[list(~corners.apply(sw_is_parallel, axis=1))]
    valid_corners.sindex

    candidates = []
    for idx, row in corners.iterrows():
        # Keep track of whether this is a terminal end of the sidewalk
        terminating1 = False
        if not pd.isnull(row['sw2_index']):
            if sw_is_parallel(row):
                continue
        else:
            # These is a terminating end of the sidewalk
            terminating1 = True

        # If this point is reached, this corner is valid
        corner = row['geometry']
        coords = corner.coords[0]

        # This is the fastest 'dwithin x meters' implementation I've found
        n = 1
        if not pd.isnull(row['sw2_index']):
            # Ignore both of the sidewalks!
            n += 1
        while True:
            close = sidewalks.sindex.nearest(coords, n + 1, objects=True)
            other_sw = sidewalks.loc[list(close)[-1].object]

            projection = other_sw.geometry.project(corner)
            point = other_sw.geometry.interpolate(projection)

            # Is there a very closeby endpoint? If so, connect to it
            # instead
            near = valid_corners.sindex.nearest(point.coords[0], 1,
                                                objects=True)
            near_idx = list(near)[0].object
            nearest = valid_corners.loc[near_idx]

            corner_snapped = False
            if nearest.geometry.distance(point) < SNAP_DIST:
                # FIXME: should back out to the original line if the snapped
                #        version is no good later on
                corner_snapped = True
                point = nearest.geometry

            if terminating1 and corner_snapped:
                # Both are terminating endpoints
                sw1 = sidewalks.loc[row['sw1_index']]
                sw2 = sidewalks.loc[nearest['sw1_index']]
                if sw1['st_id'] == sw2['st_id']:
                    # They're on the same street
                    if sw1['forward'] != sw2['forward']:
                        # They're on opposite sides of the street
                        # Don't use this candidate - it's basically a dead end.
                        n += 1
                        continue

            candidate = geometry.LineString([corner, point])
            # Distance of farthest
            if candidate.length < MAX_DIST and candidate.length > 1e-5:
                if corner_snapped:
                    to = near_idx
                else:
                    to = -1
                # z-level logic: 100% consensus. If there is any ambiguity,
                # z-level is ignored ('layer' set to nan) and no streets
                # intersections will be removed later in the process. If a
                # z-level can be determined unambiguously, it will be used
                # later (e.g. a bridge will be ignored).

                # Corner z-level ('layer')
                c1layer = sidewalks.loc[row['sw1_index'], 'layer']
                if not pd.isnull(row['sw2_index']):
                    c2layer = sidewalks.loc[int(row['sw2_index']), 'layer']
                    if c1layer == c2layer:
                        clayer = c1layer
                    else:
                        clayer = pd.np.nan
                else:
                    clayer = pd.np.nan

                # Opposite side z-level
                if corner_snapped:
                    # Need to evaluate this corner's sidewalks the same way
                    oc1layer = sidewalks.loc[nearest['sw1_index'], 'layer']
                    if not pd.isnull(nearest['sw2_index']):
                        oc2layer = sidewalks.loc[int(nearest['sw2_index']),
                                                 'layer']
                        if oc1layer == oc2layer:
                            other_layer = oc1layer
                        else:
                            other_layer = pd.np.nan
                    else:
                        other_layer = oc1layer
                else:
                    # Just get the layer for the one sidewalk
                    other_layer = other_sw['layer']

                if clayer == other_layer:
                    layer = clayer
                else:
                    layer = pd.np.nan

                candidates.append({
                    'geometry': candidate,
                    'from': row.name,
                    'to': to,
                    'sw_idx': other_sw.name,
                    'layer': layer
                })
                n += 1
            else:
                break

    df = gpd.GeoDataFrame(candidates)

    # Remove candidates that intersect more than one street or do not intersect
    # a street at all
    # FIXME: Need to insert layer awareness here - z-level is currently ignored
    #        so bridges ave impacting crossings.
    def filter_single_st(row):
        query = streets.sindex.intersection(row.geometry.bounds, objects=True)
        st_idxs = [x.object for x in query]
        if len(st_idxs) == 0:
            # Didn't find any bounding box intersections
            return -1
        else:
            intersecting = []
            # Check for actual intersections
            # Not efficient but also not buggy
            for st_idx in st_idxs:
                street = streets.loc[st_idx]
                if pd.isnull(row['layer']) or street['layer'] == row['layer']:
                    intersects = row.geometry.intersects(street.geometry)
                    intersecting.append(intersects)

            if sum(intersecting) == 1:
                return st_idxs[intersecting.index(True)]
            else:
                # Intersected more than one street - flag for removal
                return -1

    df['st_idx'] = df.apply(filter_single_st, axis=1)
    df = df.loc[df['st_idx'] != -1]

    # Remove duplicates - literal from-to duplicates
    df = df.drop_duplicates(['from', 'to', 'sw_idx'])

    # Remove duplicates - reflexive to-from lines
    df['remove'] = False
    for idx in df.index:
        row = df.loc[idx]
        if row['remove']:
            continue

        other = df.loc[(df['from'] == row['to']) & (df['to'] == row['from'])]
        if not other.empty:
            df.loc[other.index, 'remove'] = True

    df = df[~df['remove']]
    df = df.drop('remove', axis=1)
    df['crossing_id'] = df.index

    # Combine 'from' and 'to' columns into single 'corner_id' column, then drop
    # all -1 values (not nodes, crossing was connecting to edge of sidewalk)
    melted = pd.melt(df, id_vars=['crossing_id', 'st_idx', 'geometry'],
                     value_vars=['from', 'to'], value_name='corner_id')
    melted = gpd.GeoDataFrame(melted.loc[melted['corner_id'] != -1])

    # Group by graph edge ('from', 'to') and street, keep the shortest one
    def remove_redundant(group):
        # Grouped by corner and street. If the number of rows in this group
        # is more than one, it means there is more than one crossing edge doing
        # the same 'job' and we should restrict it to only one - i.e. report
        # the crossing ids that need removing.
        if group.shape[0] > 1:
            # Want to keep the shortest segments - so identify the too-long
            # ones for removal
            order = group.geometry.length.sort_values().index
            return group.loc[order[1:], 'crossing_id']

    remove = melted.groupby(['corner_id', 'st_idx']).apply(remove_redundant)
    df = df.loc[~df['crossing_id'].isin(remove)]
    df = df.reset_index(drop=True)

    # Remove crossings that intersect sidewalks (or at least flag them)
    def intersects_sw(row):
        geom = affinity.scale(row.geometry, 0.99, 0.99)
        query = sidewalks.sindex.intersection(geom.bounds, objects=True)
        idxs = [x.object for x in query]
        return sidewalks.loc[idxs].intersects(geom).any()

    df = df.loc[list(~df.apply(intersects_sw, axis=1))]
    # Drop rows with empty geometries
    df = df.loc[~df.geometry.is_empty]
    # Drop rows with NAs - these should originate from rows with specifically-
    # flagged null values in city metadata.
    df = df.dropna(axis=1)

    df.crs = sidewalks.crs

    return df
