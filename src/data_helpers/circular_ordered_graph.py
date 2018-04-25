from sidewalkify.graph.utils import azimuth_cartesian as azimuth
import networkx as nx
import numpy as np
from shapely.geometry import LineString


# TODO: Some elements of this process may make more sense as a subclass of
# networkx.MultiDiGraph. e.g., the circular embedding could be regenerated
# whenever an edge is added/removed.

def circular_ordered_graph(linestring_gdf, precision, columns=None,
                           swap=None):
    '''Create a MultiDigraph from a GeoDataFrame that has LineString
    geometries using end-to-end connections as nodes and the LineStrings as
    edges. Azimuths are calculated for every edge as the angle of the
    LineString as it exits the node (two edges are created for every row of
    the GeoDataFrame - one in each direction), enabling a circular ordering
    strategy.

    :param linestring_gdf: A GeoDataFrame where the `geometry` column is all
                           LineStrings.
    :type linestring_gdf: geopandas.GeoDataFrame
    :param precision: The rounding precision for coordinates to be considered
                      shared (end-to-end). e.g. for lon-lat, 6 or 7 is
                      generally sufficient.
    :type precision: int
    :param columns: The subset of columns of the GeoDataFrame to embed into the
                    graph edges. If not specified, none are kept (but an
                    appropriately-directed geometry is always embedded). These
                    edge attributes are generated for each edge and will
                    take precedence over specified column values: `geometry`,
                    `forward`, and `azimuth`.
    :type columns: List of str
    :param swap: A list of 2-tuples describing properties that need to be
                 swapped for a `reversed` edge.
    :type swap: list of lists

    '''
    df = linestring_gdf
    # A given geospatial network might have parallel paths - wouldn't want to
    # miss any
    G = nx.MultiDiGraph()
    for idx, row in df.iterrows():
        geometry = row['geometry']
        coords = list(geometry.coords)

        start = list(np.round(coords[0], precision))
        end = list(np.round(coords[-1], precision))

        # Use start and end points as graph nodes
        start_node = str(start)
        end_node = str(end)
        G.add_node(start_node, x=start[0], y=start[1])
        G.add_node(end_node, x=end[0], y=end[1])

        # Create two directed edges - one 'forward', one 'reverse'
        for forward in range(2):
            if columns is not None:
                edge_data = row[columns].to_dict()
            else:
                edge_data = {}

            edge_data['forward'] = forward

            if forward:
                azimuth_out = azimuth(coords[0], coords[1])
                edge_data['azimuth'] = azimuth_out
                G.add_edge(start_node, end_node, **edge_data)
            if not forward:
                coords_r = list(reversed(coords))
                geometry_r = LineString(coords_r)
                edge_data['geometry'] = geometry_r
                azimuth_out = azimuth(coords_r[0], coords_r[1])
                edge_data['azimuth'] = azimuth_out

                if swap is not None:
                    for k1, k2 in swap:
                        new_k1 = edge_data[k2]
                        new_k2 = edge_data[k1]
                        edge_data[k1] = new_k1
                        edge_data[k2] = new_k2

                G.add_edge(end_node, start_node, **edge_data)

    # For ease of traversal, the initial circular ordering is embedded in each
    # node as the 'next' node describing the edge (i.e. node u has a list of
    # nodes v1, v2, ..., vn in clockwise ordering).
    for u, d_node in G.nodes(data=True):
        # Note: complexity of for loop is due to potential of more than one
        # edge sharing the same u, v nodes.
        out_data = []
        for v, d_edges in G[u].items():
            for i, d_edge in d_edges.items():
                out_data.append([v, i, d_edge])
        out_data_sorted = sorted(out_data, key=lambda x: x[2]['azimuth'])
        sorted_edges = [(v, i) for v, i, d_edge in out_data_sorted]
        G.node[u]['sorted_edges'] = sorted_edges

    return G
