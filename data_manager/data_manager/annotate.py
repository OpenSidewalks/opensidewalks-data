from shapely.geometry import Point


def annotate_line_from_points(lines, points, default, match, threshold=3.5):
    default = str(default)
    match = str(match)
    lines = lines.to_crs(points.crs)

    def annotate_line(line_geom):
        query = points.sindex.nearest(line_geom.bounds, 1, objects=True)
        points_q = points.loc[[q.object for q in query]]
        if points_q.empty:
            return default
        if (points_q.distance(line_geom) < threshold).any():
            return match
        return default

    return lines.geometry.apply(annotate_line)


def endpoints_bool(lines, points, threshold=3.5):
    # Idea is that to return a series value of true, the points must be within
    # 'threshold' distance.
    # FIXME: don't hard-code, fix workflow to always have clear UTM vs. WGS84
    lines = lines.to_crs(points.crs)

    def both_endpoints(geometry):
        start = Point(geometry.coords[0])
        end = Point(geometry.coords[-1])
        for endpoint in [start, end]:
            query = points.sindex.nearest(endpoint.bounds, 1, objects=True)
            point = points.loc[[q.object for q in query]].iloc[0]['geometry']
            if point.distance(endpoint) > threshold:
                return False
        return True

    return lines.geometry.apply(both_endpoints)
