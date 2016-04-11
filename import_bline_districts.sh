#!/bin/bash

shp2pgsql -d -s 27700:4326 -I shapefiles/district_borough_unitary_region.shp districts > temp.sql && \
psql -d fhrs -f temp.sql && \
rm temp.sql
