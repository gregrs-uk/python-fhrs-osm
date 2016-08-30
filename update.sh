#!/bin/bash

cd ~/python-fhrs-osm || exit 1

source ~/gregrs-python-env/bin/activate || exit 1
source config.py || exit 1

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

cd ~/public_html || exit 1
mkdir fhrs-new || exit 1
mv ~/python-fhrs-osm/html/* /home/gregrs/public_html/fhrs-new/ || exit 1
mv fhrs fhrs-old || exit 1
mv fhrs-new fhrs || exit 1
rm -r fhrs-old || exit 1
