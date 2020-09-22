def lonlat_to_utm_epsg(lon, lat):
    utm_zone_epsg = 32700 - 100 * round((45 + lat) / 90.) + \
        round((183 + lon) / 6.)
    return int(utm_zone_epsg)


def gdf_to_utm(gdf):
    # Convert to wgs84 to get lon-lat info
    gdf_wgs84 = gdf.to_crs(4326)

    # Grab the roughly center point
    bounds = gdf_wgs84.total_bounds
    lon = (bounds[0] + bounds[2]) / 2
    lat = (bounds[1] + bounds[3]) / 2
    utm_zone = lonlat_to_utm_epsg(lon, lat)
    utm_crs = utm_zone

    gdf_utm = gdf.to_crs(utm_crs)

    return gdf_utm
