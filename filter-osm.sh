#!/bin/bash

source config.py

filter_list="amenity=bar,cafe,care_home,childcare,church_hall,cinema,college,\
community_centre,community_hall,fast_food,fuel,hospital,kindergarten,\
nightclub,nursing_home,pharmacy,place_of_worship,post_office,pub,restaurant,\
school,social_club,social_facility,theatre,village_hall \
club=scouts,social,sport \
craft=brewery,caterer,confectionery,distillery,winery \
shop=alcohol,bakery,butcher,cheese,chemist,confectionery,convenience,deli,\
delicatessen,discount,farm,fishmonger,greengrocer,grocery,health_food,\
newsagent,pastry,supermarket,variety_store \
tourism=hotel,guest_house"

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
