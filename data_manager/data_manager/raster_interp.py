import geopandas as gpd
import math
import numpy as np
from scipy.interpolate import RectBivariateSpline
from rasterio.windows import Window

from .utils import cut


def split_for_inclines(row):
    # Step 1: Split into more lines. The distance between split segments will
    # be irregular, as they break points will be spread evenly across the line.
    # 20-meter line: split in 2
    # 19-meter line: keep as 1
    geometry = row['geometry']
    maxlen = 20
    # Number of times to split the geometry
    n = int(np.floor(geometry.length / maxlen))
    rows = []
    if n == 0:
        rows.append(row)
    else:
        increment = geometry.length / (n + 1)

        line2 = geometry
        for i in range(n):
            line1, line2 = cut(line2, increment)
            new_row = dict(row)
            new_row['geometry'] = line1
            rows.append(new_row)
        new_row = dict(row)
        new_row['geometry'] = line2
        rows.append(new_row)

    return gpd.GeoDataFrame(rows)


def elevation_change(linestring, dem):
    x1, y1 = linestring.coords[0][0], linestring.coords[0][1]
    x2, y2 = linestring.coords[-1][0], linestring.coords[-1][1]
    start = interpolated_value(x1, y1, dem)
    end = interpolated_value(x2, y2, dem)

    return end - start


def interpolated_value(x, y, dem, method='bilinear', scaling_factor=1.0):
    '''Given a point (x, y), find the interpolated value in the raster using
    bilinear interpolation.

    '''
    methods = {
        'spline': bivariate_spline,
        'bilinear': bilinear
    }

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

    # Extract a window of coordinates
    if method == 'bilinear':
        # Get a 2x2 window of pixels surrounding the coordinates
        dim = 2
        offset_x = math.floor(_x)
        offset_y = math.floor(_y)
    elif method == 'spline':
        # Get a 5x5 window of pixels surrounding the coordinates
        dim = 3  # window size (should be odd)
        offset = math.floor(dim / 2.)
        offset_x = int(math.floor(_x) - offset)
        offset_y = int(math.floor(_y) - offset)
    else:
        raise ValueError('Invalid interpolation method {} selected'.format(
            method
        ))
    dem_arr = dem.read(1, window=Window(offset_x, offset_y, dim, dim))

    dx = _x - offset_x
    dy = _y - offset_y

    interpolator = methods[method]

    interpolated = interpolator(dx, dy, dem_arr)

    return scaling_factor * interpolated


def bivariate_spline(dx, dy, arr):
    nrow, ncol = arr.shape

    ky = min(nrow - 1, 3)
    kx = min(nrow - 1, 3)

    spline = RectBivariateSpline(np.array(range(ncol)), np.array(range(nrow)),
                                 arr, kx=kx, ky=ky)
    return spline(dx, dy)[0][0]


def bilinear(dx, dy, arr):
    nrow, ncol = arr.shape
    if (nrow != 2) or (ncol != 2):
        raise ValueError('Shape of bilinear interpolation input must be 2x2')
    top = dx * arr[0, 0] + (1 - dx) * arr[0, 1]
    bottom = dx * arr[1, 0] + (1 - dx) * arr[1, 1]

    return dy * top + (1 - dy) * bottom
