import utm


def group_endpoints(gdf, dist_threshold=0.1, precision=1):
    crs = gdf.crs

    # Convert to UTM so everything can be calculated in meters
    gdf_utm = utm.gdf_to_utm(gdf)

    # Step 1: endpoint-endpoint snapping. Use simple strategy of rounding to a
    # certain precision (in this case, 1 = 1 decimal place, or 0.1 meters)
    firsts = pd.DataFrame({
        'coordinates': df['geometry'].apply(lambda x: tuple(np.round(x.coords[0], PRECISION))),
        'idx': df.index,
        'type': 'first',
    })
    lasts = pd.DataFrame({
        'coordinates': df['geometry'].apply(lambda x: tuple(np.round(x.coords[-1], PRECISION))),
        'idx': df.index,
        'type': 'last',
    })
    ends = pd.concat([firsts, lasts])
    for coord, grp in ends.groupby('coordinates').groups:
        if grp.shape:
            # We've got grouped-together endpoints! These should be merged to a new
            # value. Save this new value back to a new column in the original df.
            new_x = grp.apply(lambda x: x[0]).mean()
            new_y = grp.apply(lambda x: x[1]).mean()
            starts.loc[grp[grp['type'] == 'first']['idx'], 'coordinates'] = (new_x, new_y)
            lasts.loc[grp[grp['type'] == 'last']['idx'], 'coordinates'] = (new_x, new_y)
    ends = pd.concat([starts, lasts])
    ends['geometry'] = ends['coordinates'].apply(lambda x: Point(x))
    ends = gpd.GeoDataFrame(ends)

    # 'ends' is now a GeoDataFrame of potentially-adjusted end coordinates. We will
    # use this data structure to query nearby lines - but throw out any that are
    # just duplicate 'hits' for endpoints. The remaining lines need to be split.

    # Step 2: Update the lines with new ends. When it comes time to split any
    # sidewalk lines, it will be advantageous to use the 'updated' data, avoiding
    # the need to track which pieces came from which sidewalks.
    for sw_idx, grp in ends.groupby('idx'):
        coords = list(df.loc[sw_idx, 'geometry'].coords)
        for idx, row in grp.iterrows():
            if row['type'] == 'start':
                coords[0] = row['coordinates']
            else:
                coords[-1] = row['coordinates']
        gdf_utm.loc[sw_idx, 'geometry'] = LineString(coords)

    # Convert back to original CRS
    df = gdf_utm.to_crs(crs)

    return df


def node_ends(gdf):
    # Save CRS for later
    crs = gdf.crs

    # Convert to UTM so everything can be calculated in meters
    gdf_utm = utm.gdf_to_utm(gdf)

    # Step 3: query for places where endpoints meet lines, implying that the line
    # needs to be split.
    for idx, row in ends.iterrows():
        point = row['geometry']

        bounds = []
        bounds.append(point.x - DIST_THRESHOLD)
        bounds.append(point.y - DIST_THRESHOLD)
        bounds.append(point.x + DIST_THRESHOLD)
        bounds.append(point.y + DIST_THRESHOLD)

        query = df.sindex.intersection(bounds, objects=True)
        sw_rows = df.loc[[q.object for q in query]]
        sw_rows = sw_rows[sw_rows.distance(point) < DIST_THRESHOLD]

        lengths = sw_rows['geometry'].length
        distances_along = sw_rows.project(point)
        not_starts = distances_along > (DIST_THRESHOLD * 2)
        not_lasts = distances_along < (lengths - DIST_THRESHOLD * 2)
        not_ends = not_starts & not_lasts

        if not_ends.any():
            # Grab the closest one and split it
            sorted_distances = distances_along[not_ends].sort_values()
            idx2 = sorted_distances.index[0]
            distance = sorted_distances.iloc[0]

            # There are non-endpoint hits - these geometries should be split at
            # the projected point(s).
            df.loc[idx2, 'split'].append(distance)

            # The original point should also be set to the projected point
            new_point = df.loc[idx2, 'geometry'].interpolate(distance)

            ends.loc[idx, 'geometry'] = new_point

    # Step 4: split the lines
    new_rows = []
    need_splitting = df[df['split'].apply(len) > 0]
    for idx, row in need_splitting.iterrows():
        geometry = row['geometry']
        for distance in sorted(set(row['split']), reverse=True):
            # print('--------------')
            # print(geometry.wkt)
            # print(list(geometry.coords))
            # print(geometry.length, distance)
            x = dh.geometry.cut(geometry, distance)
            geometry, tail = dh.geometry.cut(geometry, distance)
            new_row = df.loc[idx].copy(deep=True)
            new_row['geometry'] = tail
            new_rows.append(new_row)
        df.loc[idx, 'geometry'] = geometry

    new_df = gpd.GeoDataFrame(new_rows)

    combined_df = gpd.GeoDataFrame(pd.concat([df, new_df]))
    combined_df.crs = crs
    df_wgs84 = combined_df.to_crs({'init': 'epsg:4326'})

    dh.io.gdf_to_geojson(df_wgs84, output[0])
