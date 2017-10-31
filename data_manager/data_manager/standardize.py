

def _filter_columns(df, metadata):
    '''Filters initial data frame to include only the columns specified in
    the metadata document (and the geometry column). Also renames those
    columns.'''
    keep_cols = []
    for category, value in metadata.items():
        if value['colname']:
            keep_cols.append(value['colname'])
    keep_cols.append('geometry')

    df = df[keep_cols]

    return df


# Translate metadata colnames + values into standard schema
def _standardize_schema(df, metadata):
    '''Replaces values in df table with those from the metadata category
    maps. e.g the original dataset may encode a column to have highway=0, but
    we want a standard value (highway) for later processing.

    It also renames the columns of the dataframe to match those described in
    the metadata.

    '''
    df = df.copy()

    # Rename the columns using the metadata object
    rename = {v['colname']: k for k, v in metadata.items()}
    df.rename(columns=rename, inplace=True)

    # Replace all values in non-geometry columns
    ignore = ['pkey', 'streets_pkey']
    for category, data in metadata.items():
        if category not in ignore and 'categorymap' in data:
            mask_values = []
            df[category] = df[category].astype(str)
            # Save masks with values first to avoid duplicate replacement
            for key, value in data['categorymap'].items():
                mask_values.append((df[category] == str(key), value))
            # Apply masks
            for mask, value in mask_values:
                df.loc[mask, category] = value
        if category == 'pkey' and 'nullvalue' in data:
            df = df.loc[df['pkey'].astype(str) != str(data['nullvalue'])]

    return df


def standardize_df(df, metadata):
    # FIXME: Need to add validator to inputs (restrict allowed metadata keys
    #        and values)

    crs = df.crs
    #
    # Metadata-based filtering/value substitution
    #

    # Filter columns to those described in the metadata
    df = _filter_columns(df, metadata)

    # Rename the columns and their values using the metadata
    df = _standardize_schema(df, metadata)

    # Drop rows with empty geometries
    df = df.dropna(axis=0, subset=['geometry'])

    # Goal is to take street lines, draw sidewalks with offset
    # Every street geometry may have one or more sidewalks assigned to it
    # Upon exploding the street geometries, there will be multiple street lines
    # that refer to the same sidewalk geometry

    df = dedupe_geometries(df)

    # Drop nulls - nulls indicate field values outside of those in the
    # whitelist
    df = df.dropna()

    # The primary key ('pkey') may not be unique (looking at you, SDOT), so
    # let's generate a truly unique key ('id'). It will not necessarily be
    # sequential/complete due to subsequent filtering.
    df.reset_index(drop=True, inplace=True)
    df['id'] = df.index

    df.crs = crs

    return df


# def explode_multilinestrings(df):
#     # Expand MultiLineStrings into separate rows of LineStrings
#     linestrings = df.loc[df.geometry.type == 'LineString']
#
#     newlines = []
#     for i, row in df.loc[df.geometry.type == 'MultiLineString'].iterrows():
#         for geom in row.geometry:
#             # Keep metadata
#             newlines.append(row.copy())
#             newlines[-1].geometry = geom
#     multilinestrings = gpd.GeoDataFrame(newlines)
#
#     # Create fresh index
#     df.reset_index(drop=True, inplace=True)
#
#     df = gpd.GeoDataFrame(pd.concat([linestrings, multilinestrings]))
#
#     return df


def dedupe_geometries(df):
    # Dedupe lines WKT (TODO: replace with line similarity)
    df['wkt'] = df.geometry.apply(lambda r: r.wkt)
    df = df.drop_duplicates('wkt')
    df = df.drop('wkt', 1)

    return df


def whitelist_filter(df, whitelists):
    # Filter via whitelists (dictionaries with key = colname, values = allowed
    # values
    for colname, whitelist in whitelists.items():
        if colname in df.columns:
            df = df.loc[df[colname].isin(whitelist)]

    return df


def assign_st_to_sw(df_sw, df_st):
    '''Given a street and sidewalk datasets where the sidewalks dataset has a
    foreign key for the street to which it belongs, associate the two and trim
    drop sidewalks that have no street.

    :param df_st: GeoDataFrame of Seattle's df_st in SDOT's spec
    :type df_st: geopandas.GeoDataFrame
    :param df_sw: GeoDataFrame of Seattle's df_sw in SDOT's spec
    :type df_sw: geopandas.GeoDataFrame

    '''
    # FIXME: Remove sidewalks that are literally on top of street lines
    crs = df_sw.crs

    # Save index as column (survives read/write to filesystem)
    # df_st['index'] = list(df_st.index)

    # Remove sidewalks that don't refer to a specific street
    df_sw = df_sw.loc[df_sw['streets_pkey'].isin(df_st['pkey'])]

    #
    # Restore the CRS
    #
    df_sw.crs = crs

    return df_sw
