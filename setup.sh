#!/bin/bash

if [ ! -f "./shapefiles/district_borough_unitary_region.shp" ]
then
	echo "Can't find the OS Boundary Line shapefiles. Please see"
	echo "shapefiles/README-shapefiles.md for instructions."
    exit 1
fi

source config.py

pip install overpy || exit 1
pip install psycopg2 || exit 1
pip install shapely || exit 1
dropdb --if-exists $dbname || exit 1
createdb $dbname || exit 1
psql -d $dbname -c "create extension postgis; create extension fuzzystrmatch;" || exit 1
./import_bline_districts.sh || exit 1
python get_fhrs_data.py || exit 1
python get_osm_data.py || exit 1
python process_data.py || exit 1
if [ -d "./html" ]
then
	rm -rf ./html || exit 1
fi
mkdir ./html || exit 1
mkdir ./html/json || exit 1
python create_output_files.py || exit 1
