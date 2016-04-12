#!/bin/bash

if [ -f "./shapefiles/district_borough_unitary_region.shp" ]
then
	pip install psycopg2 && \
	dropdb fhrs
    createdb fhrs && \
    psql -d fhrs -c "create extension postgis; create extension fuzzystrmatch;" && \
    ./import_bline_districts.sh && \
    python get_data.py && \
    python process_data.py && \
		if [ ! -d "./html/json" ]
		then
			mkdir ./html/json
		fi
    python create_geojsons.py
else
	echo "Can't find the OS Boundary Line shapefiles. Please see"
	echo "shapefiles/README-shapefiles.md for instructions."
fi
