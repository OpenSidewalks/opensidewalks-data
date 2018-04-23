def lonlat_to_utm_epsg(lon, lat):
    utm_zone_epsg = 32700 - 100 * round((45 + lat) / 90.) + \
        round((183 + lon) / 6.)
    return utm_zone_epsg
