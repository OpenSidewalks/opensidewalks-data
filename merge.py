import json
import os

from shapely.geometry import MultiPoint, mapping


CITY_DATA = [{
    "name": "Seattle",
    "key": "wa.seattle",
    "center": [-122.339, 47.604, 15],
    "transportation_data": "./cities/seattle/output/transportation.geojson",
}, {
    "name": "Mt. Vernon",
    "key": "wa.mtvernon",
    "center": [-122.336, 48.419, 14],
    "transportation_data": "./cities/mtvernon/output/transportation.geojson",
}, {
    "name": "Bellingham",
    "key": "wa.bellingham",
    "center": [-122.478, 48.751, 13.5],
    "transportation_data": "./cities/bellingham/output/transportation.geojson"
}]


def merge_geojson(datasets):
    merged = {"type": "FeatureCollection", "features": []}
    datasets_metadata = {"type": "FeatureCollection", "features": []}
    for dataset in datasets:
        with open(dataset["transportation_data"]) as f:
            fc = json.load(f)

        points = []
        for feature in fc["features"]:
            merged["features"].append(feature)
            points += feature["geometry"]["coordinates"]

        points = MultiPoint(points)
        hull = points.convex_hull

        bounds = list(hull.bounds);

        datasets_metadata["features"].append({
            "type": "Feature",
            "geometry": mapping(hull),
            "properties": {
                "bounds": bounds,
                "key": dataset["key"],
                "name": dataset["name"],
                "lon": dataset["center"][0],
                "lat": dataset["center"][1],
                "zoom": dataset["center"][2],
            }
        })

    return merged, datasets_metadata


if __name__ == "__main__":
    merged, datasets_metadata = merge_geojson(CITY_DATA)
    if not os.path.exists("./merged"):
        os.mkdir("./merged")
    with open("./merged/transportation.geojson", "w") as f:
        json.dump(merged, f)
    with open("./merged/regions.geojson", "w") as f:
        json.dump(datasets_metadata, f)
