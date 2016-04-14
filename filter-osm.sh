#!/bin/bash

INPUT_PBF=data/great-britain-latest.osm.pbf
OSMOSIS_BIN=~/Downloads/osmosis-latest/bin/osmosis
FILTER_LIST="amenity=fast_food,restaurant,cafe,pub,bar,nightclub,hospital,\
school,college tourism=hotel,guest_house"

if [ ! -d data ]
then
    mkdir data
fi

$OSMOSIS_BIN \
  --read-pbf $INPUT_PBF \
  --tf accept-ways fhrs:id=* \
  --tf reject-relations \
  --used-node outPipe.0="ways-fhrsid" \
  \
  --read-pbf $INPUT_PBF \
  --tf accept-ways $FILTER_LIST \
  --tf reject-relations \
  --used-node outPipe.0="ways-filter" \
  \
  --read-pbf $INPUT_PBF \
  --tf accept-nodes fhrs:id=* \
  --tf reject-ways \
  --tf reject-relations outPipe.0="nodes-fhrsid" \
  \
  --read-pbf $INPUT_PBF \
  --tf accept-nodes $FILTER_LIST \
  --tf reject-ways \
  --tf reject-relations outPipe.0="nodes-filter" \
  \
  --merge inPipe.0="ways-fhrsid" inPipe.1="ways-filter" \
  --merge inPipe.0="nodes-fhrsid" inPipe.1="nodes-filter" \
  --merge \
  --write-xml data/filtered.osm
