inputfile=$1
outputdir=$2
osmosis --read-pbf $inputfile \
        --bounding-box left=-122.4062 bottom=48.3752 right=-122.1987 top=48.4503 completeWays=yes \
          outPipe.0=source \
        --tee inPipe.0=source \
          outputCount=3 \
          outPipe.0=footways_in \
          outPipe.1=nonfootways_in \
          outPipe.2=nodes_in \
\
        --tf inPipe.0=footways_in \
          accept-ways highway=footway \
          --un \
          --write-xml $outputdir/footways.osm \
        --tf inPipe.0=nonfootways_in \
          accept-ways highway=* \
            --tf \
              reject-ways highway=footway \
            outPipe.0=nonfootways_out \
\
        --tee inPipe.0=nonfootways_out \
          outputCount=4 \
          outPipe.0=nonfootways0 \
          outPipe.1=nonfootways1 \
          outPipe.2=nonfootways2 \
          outPipe.3=nonfootways3 \
\
        --tf inPipe.0=nonfootways0 \
          accept-ways highway=pedestrian \
          --un \
          --write-xml $outputdir/pedestrian_roads.osm \
        --tf inPipe.0=nonfootways1 \
          accept-ways highway=steps \
          --tf \
            reject-ways highway=pedestrian \
            --un \
            --write-xml $outputdir/stairs.osm \
        --tf inPipe.0=nonfootways2 \
          accept-ways foot=yes \
          --tf reject-ways highway=steps \
          --tf \
            reject-ways highway=pedestrian \
            --un \
            --write-xml $outputdir/footyes.osm \
        --tf inPipe.0=nonfootways3 \
          accept-ways highway=primary,secondary,tertiary,residential,service \
          --tf \
            reject-ways foot=yes \
            --un \
            --write-xml $outputdir/streets.osm \
\
        --tee inPipe.0=nodes_in \
          outPipe.0=kerbs_in \
          outPipe.1=elevators_in \
        --tf inPipe.0=kerbs_in \
          accept-nodes kerb=* \
          --un \
          --write-xml $outputdir/kerbs.osm \
        --tf inPipe.0=elevators_in \
          accept-nodes highway=elevator \
          --un \
          --write-xml $outputdir/elevators.osm
