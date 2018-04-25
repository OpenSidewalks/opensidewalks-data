# AccessMap Data Generator TO-DO List

## Stay on 'street network' longer, use to stage crossings

Attempting to draw crossings from sidewalk lines and streets, sans metadata
on street associations, has some serious and possibly insurmoountable problems
given the incompleteness and differences between maps. Examples:

  - SDOT errors. The street locations suggested by SDOT's streets dataset, and
  the Street Network Database, can be off by 10+ meters in ways that make
  sidewalk locations absurd. As a consequence, sidewalks get placed on the
  opposite side of nearby streets from where they should be.

  - Boulevards. Staging a crossing for a boulevard requires some street
  network-level interpretations: the two streets in a boulevard have the same
  network connections, just in opposite orientation (one-way streets), and the
  locations they intersect should be considered *one* intersection, not two.
  This idea follows from how osmnx treats them, but is very relevant to our
  issues with crossings.

  - Partial / missing sidewalks. An example is near the University Bridge,
  near the first turn-off heading south on Roosevelt. There's a small 'island'
  near an intersection, and only one half has sidewalks. Nevertheless, we're
  adding crossings that go from one sidewalk, across the street, then across
  grass and trees, to a sidewalk associated with a different street. This can
  be avoided if we pre-decide the sidewlaks to connect from a street network-
  associated description.

  - z-layer inconsistencies. We can completely ignore z-layer differences by
  looking at the street network intersections first, and just jogging up x
  meters to an initial approximation of the crossing point.

The proposed new strategy looks like this:

  1. Associate each sidewalk with street (already done in current workflow)

  2. Derive intersections from street network (also done in current workflow)

  3. Group intersections to deal with boulevards, etc.

  4. Add associated street information to the intersections.

  5. Iterate over each associated street:
    1. Travel at most half-way down the street, minimum X meters away from the
       intersection. X can be parameterized/informed by associated street
       widths.

    2. Find the first street segment with sidewalk associated with both sides.

    3. This is the first approximation of the crossing location. It has this
       information:

       - The associated street (ID)
       - The associated sidewalks (ID)
       - The associated intersection (ID)

    4. (optional) attempt to associate metadata from SDOT at this point as well
    such as marked/unmarked, signalization, etc.

  6. For every initial crossing location, attempt to draw an actual crossing by
  finding the closest points on the associated sidewalks / some other strategy

    - Addendum: This doesn't handle the situation where, e.g., there should
    be a crossing between sidewalks associated with orthogonal streets. e.g.,
    these cases:
      - There is a sidewalk on the 'left' side of a street, and not the right,
      but there is a sidewalk approach from the right on the neighboring street.
      - There are no sidewalks on the left or right of the street, but there
      should still be a crossing to connect sidewalks on the 'top' of an
      orthogonal street.

      - Potential solution: attempt to identify corners, accounting for:
        - The two (potential) sidewalks on each side of the street of interest
        - The neighboring sidewalks
        - Need to strategize about boulevards


This strategy should be much faster than the current solution, which is also
the bottleneck of our build process. It should also lead to fewer data errors.

The primary downside is that it requires an associated between a sidewalk and
a street, something we have not properly addressed in OpenStreetMap. With that
said, we can get away with it because it's meant for use with AccessMap, and
for staging data for later use in OpenStreetMap, and does not need to derive
from OSM itself.

## Match to OSM roads first, then do network, etc.

The SDOT dataset is not aware of several roads, particularly those on large
piece of public/private property such as UW campus or South Seattle CC. As a
workaround, the sidewalks dataset will sometimes have multiple entries for a
single sidewalk along a street, with corresponding offset start/stop distances.
If you draw a parallel offset at those distances, it kind of approximates
breaks in the sidewalk.

This poses some issues:

1. It's not spatially accurate
2. We want to know when someone has to cross the street - i.e. we need the
real street network to figure out crossing situations, and SDOT is missing
important bits.

As a workaround, we should do this:
1. Make an OSM street graph.
2. Match maps. OSM should generally have more detail, so expect many:1 mappings
from SDOT:OSM.
3. Attempt to match specific 'trouble' sidewalks with the street grap

## Performance

- Optimize `assign sidewalks to side of street` and `crossify`, these are the
longest steps by far.

- Use multiple cores for long-running processing steps.

 All files should be downloaded in parallel and cached, with an option to
just rebuild rather than download new data.

- When `all` command has been run, pass data in-memory rather than waiting for
read/write.

- DEMs should be cached. Appropriate directory for a cache?

- Sample DEM data from disk rather than in-memory, perhaps with slight caching.

- Don't combine DEMs, just sort input data into DEM zones and directly access.

## Data improvement

- Sample more points for sidewalks/crossings, estimate maximum incline rather
than endpoint-to-endpoint.

- Create routable graph data as well, even if it's stored as tables. e.g.,
add node where sidewalks meet crossings (for OSM import), split at those
points (for routing downstream).

## UI

- Show download progress bars, ensure that all steps are enclosed by start/end
bars.

- Crossings-generation progress: we already know how many intersections need to
be processed, just need to update `crossify` to do one-at-a-time (good for
vectorization anyways) so we can report completion.

## Generalization

- Implement proper UTM support.

- Just attempt this for another city and see what breaks.

- Consider recombining with `sidewalkify` and `crossify` repositories (still
make CLI apps available, though) and turning into a general data staging tool
for all kinds of pedestrian data, make it look more like OSM data. Useful for
future imports.

- `import tool` would use most of this functionality

- Separate out / reconsider meaning of `incline` values. These may be
router-specific and would not be used for OSM data staging. e.g.,
OpenTripPlanner ends up recalculating segment-by-segment incline values, which
implies splitting input ways, which we don't want to do for our 'main',
asset-focused task.
