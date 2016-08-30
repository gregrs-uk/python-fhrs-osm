# config file to be read by both Python and BASH

# postgresql database name
dbname="gregrs_fhrs"

# fhrs download mode
# small_test = Rugby and Warwick, west_mids = West Midlands, full = All regions
get_fhrs_mode="small_test"

# do we want to use a filtered planet extract file (data/filtered.osm)
# instead of querying using Overpass API?
use_xml_file=True

# path of pbf file if we're using a planet extract
input_pbf="data/great-britain-latest.osm.pbf"

# path of osmosis binary if we're using a planet extract
osmosis_bin="~/osmosis/bin/osmosis"
