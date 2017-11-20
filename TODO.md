# AccessMap Data Generator TO-DO List

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
