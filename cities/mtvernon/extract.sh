inputfile=$1
outputdir=$2
osmosis --read-pbf $inputfile \
        --bounding-box \
          left=-122.4062 \
          bottom=48.3752 \
          right=-122.1987 \
          top=48.4503 \
          clipIncompleteEntities=true \
          outPipe.0=source \
\
        --tee inPipe.0=source \
          outputCount=3 \
          outPipe.0=transportation_in \
          outPipe.1=streets_in \
          outPipe.2=barriers_in \
\
        --tf inPipe.0=transportation_in \
          accept-ways highway=footway,cycleway,path,pedestrian,service,steps \
        --un \
        --write-xml $outputdir/transportation.osm \
\
        --tf inPipe.0=streets_in \
          accept-ways highway=primary,secondary,tertiary,residential,service \
        --write-xml $outputdir/streets.osm \
\
        --tf inPipe.0=barriers_in \
          accept-nodes kerb=* \
        --un \
        --write-xml $outputdir/barriers.osm \
