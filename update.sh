#!/bin/bash

source ~/gregrs-python-env/bin/activate || exit 1
source ~/python-fhrs-osm/config.py || exit 1

cd ~/python-fhrs-osm || exit 1
python get_fhrs_data.py || exit 1

echo "Downloading latest OSM data"
cd ~/python-fhrs-osm/data || exit 1
mv great-britain-latest.osm.pbf great-britain-latest.osm.pbf.old
wget http://download.geofabrik.de/europe/great-britain-latest.osm.pbf \
	|| exit 1
rm great-britain-latest.osm.pbf.old

cd ~/python-fhrs-osm || exit 1

echo "Filtering OSM data"
./filter-osm.sh || exit 1

python get_osm_data.py || exit 1
python process_data.py || exit 1
if [ -d "./html" ]
then
	rm -rf ./html || exit 1
fi
mkdir ./html || exit 1
mkdir ./html/json || exit 1
mkdir ./html/gpx || exit 1
python create_output_files.py || exit 1

echo "Moving output files to public directory"
cd ~/public_html || exit 1
mkdir fhrs-new || exit 1
mv ~/python-fhrs-osm/html/* /home/gregrs/public_html/fhrs-new/ || exit 1
mv fhrs fhrs-old || exit 1
mv fhrs-new fhrs || exit 1
rm -r fhrs-old || exit 1
echo "Completed successfully"
