import json
from shapely.geometry import mapping


def gdf_to_geojson(gdf, path):
    def row_to_feature(row):
        properties = row.loc[~row.isna()].to_dict()
        properties.pop('geometry')
        return {
            'type': 'Feature',
            'geometry': mapping(row['geometry']),
            'properties': properties
        }

    fc = {
        'type': 'FeatureCollection',
        'features': list(gdf.apply(row_to_feature, axis=1))
    }

    with open(path, 'w') as f:
        json.dump(fc, f)
