# opensidewalks-data

Build workflows for OpenSidewalks data releases. Workflows generate OpenSidewalks
Schema reference implementations for multiple cities.

## Installation

### Local installation and deployment

A local installation involves installing various libraries directly on your local
computer. This is less automated than the alternative `docker` installation, but will
be more straightforward for development and debugging if you are comfortable with
command-line package installation.

#### osmosis

Some workflows require the `osmosis` command line utility and/or libraries. On ubuntu:

    apt install osmosis

#### GDAL

GDAL is used throughout the workflows both directly and as a library. On ubuntu:

    sudo apt install gdal-bin

#### Python setup

It is easiest to install the Python dependencies using the
[Poetry](https://python-poetry.org/) packaging tool. Once installed, simply run:

    poetry install

A dedicated virtual environment will be created and exactly the right versions of all
Python dependencies will be installed.

### Docker-based installation

1. Build the container
    docker build -t opensidewalks-data .

## Extract a single region's data

Note: if you used `docker` to install the dependencies, you can run a modified version
of these commands by (1) including a volume bind (`-v`) to the region's directory and
(2) running an extended command, e.g.
`docker run opensidewalks-data -v $(pwd)/cities/seattle:/bound bash -c "cd /bound && poetry run snakemake -j 8"`.

1. Enter a region's directory
    cd cities/{region}

2. Fetch the source data
    poetry run snakemake -j 8 --snakefile Snakefile.fetch

3. Extract / build into a connected pedestrian network
    poetry run snakemake -j 8

## Extract all regions and transform into `transportation.geojson` and `regions.geojson`

Note: if you used `docker` to install the dependencies, you can run a modified version
of these commands by (1) including a volume bind (`-v`) to the region's directory and
(2) running an extended command, e.g.
`docker run opensidewalks-data -v $(pwd):/work poetry ./merge.py"`.

1. Extract each region one at a time. Their `output` directories will now be populated
with a `transportation.geojson`.

2. In the main repo directory, run the merge script, which will (1) merge all
`transportation.geojson` files into a single set of (otherwise unchanged) data and (2)
create a `regions.geojson` that describes the different regions that were extracted.
    python ./merge.py

# OpenSidewalks Data Schema

See the [schema repo](https://github.com/OpenSidewalks/OpenSidewalks-Schema).
