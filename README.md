# opensidewalks-data

Build workflows for OpenSidewalks data releases. Workflows generate OpenSidewalks
Schema reference implementations for multiple cities.

## Installation

### Docker-based installation

1. Build the container
    docker build -t opensidewalks-data .

## Extract a single region's data

    docker run --rm -v $(pwd):/data opensidewalks-data bash -c "cd /data/cities/seattle && snakemake -j 8 --snakefile ./Snakefile.fetch"
    docker run --rm -v $(pwd):/data opensidewalks-data bash -c "cd /data/cities/seattle && snakemake -j 8 --snakefile ./Snakefile"

## Extract all regions and transform into `transportation.geojson` and `regions.geojson`

docker run --rm -v $(pwd):/data opensidewalks-data bash -c "cd /data && python ./merge.py"

# OpenSidewalks Data Schema

See the [schema repo](https://github.com/OpenSidewalks/OpenSidewalks-Schema).
