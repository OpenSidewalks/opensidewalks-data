from shapely.geometry import Point


def annotate_line_from_points(lines, points, defaults, threshold=3.5):
    # For each point, find the closest line
    lines.sindex
    for idx, row in points.iterrows():
        query = list(lines.sindex.nearest(row.geometry.bounds, objects=True))
        line = lines.loc[query[0].object]
        if line.geometry.distance(row.geometry) < threshold:
            for default in defaults:
                for key, value in default.items():
                    lines.loc[line.name, key] = value


def endpoints_bool(lines, points, threshold=3.5):
    # Idea is that to return a series value of true, the points must be within
    # 'threshold' distance.

    def both_endpoints(geometry, points):
        start = Point(geometry.coords[0])
        end = Point(geometry.coords[-1])
        for endpoint in [start, end]:
            query = points.sindex.nearest(endpoint.bounds, 1, objects=True)
            point = points.loc[[q.object for q in query]].iloc[0]['geometry']
            if point.distance(endpoint) > threshold:
                return False
        return True

    return lines.geometry.apply(both_endpoints, args=[points])
