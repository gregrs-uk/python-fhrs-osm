#!/bin/bash

source config.py

filter_list="amenity=fast_food,restaurant,cafe,pub,bar,nightclub,hospital,\
school,college tourism=hotel,guest_house"

if [ ! -d data ]
then
    mkdir data
fi

$osmosis_bin \
  --read-pbf $input_pbf \
  --tf accept-ways fhrs:id=* \
  --tf reject-relations \
  --used-node outPipe.0="ways-fhrsid" \
  \
  --read-pbf $input_pbf \
  --tf accept-ways $filter_list \
  --tf reject-relations \
  --used-node outPipe.0="ways-filter" \
  \
  --read-pbf $input_pbf \
  --tf accept-nodes fhrs:id=* \
  --tf reject-ways \
  --tf reject-relations outPipe.0="nodes-fhrsid" \
  \
  --read-pbf $input_pbf \
  --tf accept-nodes $filter_list \
  --tf reject-ways \
  --tf reject-relations outPipe.0="nodes-filter" \
  \
  --merge inPipe.0="ways-fhrsid" inPipe.1="ways-filter" \
  --merge inPipe.0="nodes-fhrsid" inPipe.1="nodes-filter" \
  --merge \
  --write-xml data/filtered.osm
