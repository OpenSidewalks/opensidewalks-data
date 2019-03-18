import json
import os

from shapely.geometry import MultiPoint, mapping


CITY_DATA = [{
    "name": "Seattle",
    "center": [-122.339, 47.604, 15],
    "transportation_data": "./cities/seattle/output/transportation.geojson",
}, {
    "name": "Mt. Vernon",
    "center": [-122.336, 48.419, 14],
    "transportation_data": "./cities/mtvernon/output/transportation.geojson",
}, {
    "name": "Bellingham",
    "center": [-122.47871,48.75253,13.5],
    "transportation_data": "./cities/bellingham/output/transportation.geojson"
}]


def merge_geojson(datasets):
    merged = {"type": "FeatureCollection", "features": []}
    datasets_metadata = []
    for dataset in datasets:
        with open(dataset["transportation_data"]) as f:
            fc = json.load(f)

        points = []
        for feature in fc["features"]:
            merged["features"].append(feature)
            points += feature["geometry"]["coordinates"]

        points = MultiPoint(points)
        hull = points.convex_hull
        datasets_metadata.append({
            "name": dataset["name"],
            "center": dataset["center"],
            "hull": mapping(hull),
        })

    return merged, datasets_metadata


if __name__ == "__main__":
    merged, datasets_metadata = merge_geojson(CITY_DATA)
    if not os.path.exists("./merged"):
        os.mkdir("./merged")
    with open("./merged/transportation.geojson", "w") as f:
        json.dump(merged, f)
    with open("./merged/areas_served.json", "w") as f:
        json.dump(datasets_metadata, f)
