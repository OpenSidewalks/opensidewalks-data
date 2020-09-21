# opensidewalks-data

Build workflows for OpenSidewalks data releases. Workflows generate OpenSidewalks
Schema reference implementations for multiple cities.

## Installation

### City-specific dependencies

- The `uwashington` "region" requires the command line utility `osmosis`.

### Local machine installation

0. (Optional) Install a virtualenv

    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip

1. Install GDAL
    # On ubuntu:
    sudo apt install gdal-bin

2. Install dependencies
    pip install snakemake
    pip install -r requirements.txt

### Docker-based installation

1. Build the container
    docker build -t opensidewalks-data .

## Extract a single region's data

Note: if you used `docker` to install the dependencies, you can run a modified version
of these commands by (1) including a volume bind (`-v`) to the region's directory and
(2) running an extended command, e.g.
`bash -c "cd /bound/directory && snakemake -j 8"`.

1. Enter a region's directory
    cd cities/{region}

2. Fetch the source data
    snakemake -j 8 --snakefile Snakefile.fetch

3. Extract / build into a connected pedestrian network
    snakemake -j 8

## Extract all regions and transform into `transportation.geojson` and `regions.geojson`

Note: if you used `docker` to install the dependencies, you can run a modified version
of the merge command by (1) binding the entirey repo to a volume (`-v`) and (2) running
an extended command: `bash -c cd /bound/directory && python ./merge.py`.

1. Extract each region one at a time. Their `output` directories will now be populated
with a `transportation.geojson`.

2. In the main repo directory, run the merge script, which will (1) merge all
`transportation.geojson` files into a single set of (otherwise unchanged) data and (2)
create a `regions.geojson` that describes the different regions that were extracted.
    python ./merge.py

# OpenSidewalks Data Schema

See the [schema repo](https://github.com/OpenSidewalks/OpenSidewalks-Schema).
