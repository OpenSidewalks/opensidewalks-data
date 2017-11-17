import math


def interpolated_value(x, y, dem, dem_arr):
    '''Given a point (x, y), find the interpolated value in the raster using
    bilinear interpolation.

    '''
    # At this point, we assume that the input DEM is in the same crs as the
    # x y values.

    # The DEM's affine transformation: maps units along its indices to crs
    # coordinates. e.g. if the DEM is 1000x1000, maps xy values in the
    # 0-1000 range to the DEM's CRS, e.g. lon-lat
    aff = dem.transform
    # The inverse of the transform: maps values in the DEM's crs to indices.
    # Note: the output values are floats between the index integers.
    inv = ~aff

    # Get the in-DEM index coordinates
    _x, _y = inv * (x, y)

    # Get the coordinates for the four actual pixel centers surrounding this
    # one point (to use for interpolation)
    xmin = int(math.floor(_x))
    xmax = int(math.ceil(_x))
    ymin = int(math.floor(_y))
    ymax = int(math.ceil(_y))

    # Convert to (absolute value) deltas
    dx_left = abs(_x - xmin)
    dx_right = abs(xmax - _x)
    dy_top = abs(ymax - _y)
    dy_bottom = abs(_y - ymin)

    # Apply bilinear interp algorithm
    # Note: indexing into the DEM array goes (y, x) from lonlat.
    top = dx_left * dem_arr[ymax, xmin] + dx_right * dem_arr[ymax, xmax]
    bottom = dx_left * dem_arr[ymin, xmin] + dx_right * dem_arr[ymin, xmax]

    interpolated = dy_top * top + dy_bottom * bottom

    return interpolated
