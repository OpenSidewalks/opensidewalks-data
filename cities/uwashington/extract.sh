inputfile=$1
outputdir=$2
osmosis --read-xml $inputfile outPipe.0=source \
        --tee inPipe.0=source \
          outputCount=3 \
          outPipe.0=footways_in \
          outPipe.1=nonfootways_in \
          outPipe.2=nodes_in \
\
        --tf inPipe.0=footways_in \
          accept-ways highway=footway \
          outPipe.0=footways_out \
        --tf inPipe.0=nonfootways_in \
          accept-ways highway=* \
            --tf \
              reject-ways highway=footway \
            outPipe.0=nonfootways_out \
\
       --tee inPipe.0=footways_out \
         outputCount=3 \
         outPipe.0=footways0 \
         outPipe.1=footways1 \
         outPipe.2=footways2 \
\
        --tf inPipe.0=footways0 \
          accept-ways footway=sidewalk \
          --un \
          --write-xml $outputdir/sidewalks.osm \
        --tf inPipe.0=footways1 \
          accept-ways footway=crossing \
          --un \
          --write-xml $outputdir/crossings.osm \
        --tf inPipe.0=footways2 \
          reject-ways footway=sidewalk \
          --tf \
            reject-ways footway=crossing \
            --un \
            --write-xml $outputdir/footways.osm \
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
