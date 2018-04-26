def lonlat_to_utm_epsg(lon, lat):
    utm_zone_epsg = 32700 - 100 * round((45 + lat) / 90.) + \
        round((183 + lon) / 6.)
    return utm_zone_epsg


def gdf_wgs84_to_utm(gdf):
    # Random point - should probably find centroid or something
    lon, lat = gdf.iloc[0]['geometry'].coords[0]
    zone = lonlat_to_utm_epsg(lon, lat)

    gdf.crs = {'init': 'epsg:4326'}
    new = gdf.to_crs({'init': 'epsg:{}'.format(zone)})

    return new
