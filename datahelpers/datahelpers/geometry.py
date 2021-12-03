from shapely.geometry import LineString, Point


# def cut(line, distance):
#     # Cuts a line in two at a distance from its starting point
#     if distance <= 0.0 or distance >= line.length:
#         return [LineString(line)]
#     coords = list(line.coords)
#     for i, p in enumerate(coords):
#         pd = line.project(Point(p))
#         if pd == distance:
#             return [
#                 LineString(coords[:i+1]),
#                 LineString(coords[i:])
#             ]
#         if pd > distance:
#             cp = line.interpolate(distance)
#             return [
#                 LineString(coords[:i] + [(cp.x, cp.y)]),
#                 LineString([(cp.x, cp.y)] + coords[i:])
#             ]


def cut(line, distance):
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)

    pd = 0
    last = coords[0]
    for i, p in enumerate(coords):
        if i == 0:
            continue
        pd += point_distance(last, p)

        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])
            ]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])
            ]

        last = p
    # If the code reaches this point, we've hit a floating point error or something, as
    # the total estimated distance traveled is less than the distance specified and
    # the distance specified is less than the length of the geometry, so there's some
    # small gap. The approach floating around online is to use linear projection to
    # find the closest point to the given distance, but this is not robust against
    # complex, self-intersection lines. So, instead: we just assume it's between the
    # second to last and last point.
    cp = line.interpolate(distance)
    return [
        LineString(coords[:i] + [(cp.x, cp.y)]),
        LineString([(cp.x, cp.y)] + coords[i:])
    ]


def point_distance(p1, p2):
    dx = (p2[0] - p1[0])
    dy = (p2[1] - p1[1])

    return (dx**2 + dy**2)**0.5
