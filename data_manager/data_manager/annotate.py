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
