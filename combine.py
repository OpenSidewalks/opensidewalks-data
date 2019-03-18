import json


CITY_DATA = [
    "./cities/seattle/output/transportation.geojson",
    "./cities/mtvernon/output/transportation.geojson",
    "./cities/bellingham/output/transportation.geojson"
]


def merge_geojson(paths):
    combined = {"type": "FeatureCollection", "features": []}
    for path in paths:
        with open(path) as f:
            fc = json.load(f)
        for feature in fc["features"]:
            combined["features"].append(feature)

    return combined


if __name__ == "__main__":
    merged = merge_geojson(CITY_DATA)
    with open("./transportation.geojson", "w") as f:
        json.dump(merged, f)
