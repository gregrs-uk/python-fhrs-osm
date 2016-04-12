# [python-fhrs-osm](http://github.com/gregrs-uk/python-fhrs-osm)
Python tools for downloading and comparing Food Hygiene Rating Scheme (FHRS) and OpenStreetMap (OSM) data and finding possible matches between it, together with Leaflet slippy maps for visualising the data.

## Features
* Download specific OpenStreetMap and FHRS data using a modified version of overpy and the FHRS API and parse it into a PostgreSQL/PostGIS database
* Use database views to compare OpenStreetMap and FHRS data and find anomalies
* Use a database view to find possible matches between OSM nodes/ways and FHRS establishments, based on proximity and similarity of names
* Export GeoJSON files to use in Leaflet slippy maps, allowing users to visualise OSM/FHRS data as well as to review possible matches between FHRS and OSM data and import useful tags into JOSM

## Requirements
* Tested using Python 2.7 on Ubuntu and Mac OS X
* Tested using PostgreSQL 9.3

## Installation
1. Download the Boundary Line shapefiles from
[Ordnance Survey](https://www.ordnancesurvey.co.uk/opendatadownload/) and
place the four `district_borough_unitary_region.*` files in the `shapefiles` directory. (These are used to compute which district FHRS establishments and OSM entities are in so that relavitely small GeoJSON files can be created, one for each district)
* Run `setup.sh`, which should:
    * Install psycopg2 module
    * (Re)create `fhrs` PostgreSQL database
    * Enable PostGIS and fuzzystrmatch extensions
    * Import district boundaries from shapefiles
    * Run `python get_fhrs_data.py` to download FHRS data to the PostgreSQL database
        * By default, data for the Rugby and Warwick areas are downloaded, but this can be altered in `get_fhrs_data.py`
        * FHRS data is always downloaded one authority at a time
    * Run `python get_osm_data.py` to download OpenStreetMap data to the PostgreSQL database
        * By default, data is downloaded to match the bounding box of the FHRS data present in the database, but this can be altered in `get_osm_data.py`
        * FHRS data is always downloaded one authority at a time
        * The OSM tag/value pairs to query can also be easily modified. Please see the docstrings in `fhrs_osm/__init__.py` for details)
    * Run `python process_data.py` to compute which district FHRS establishments and OSM entities are in and to create the database views
    * Run `python create_geojsons.py` to create a GeoJSON file for each district which contains data

## Usage
* Open `overview.html` in a browser to visualise the FHRS and OSM data (see below). Adding a question mark followed by the district ID loads data for that district e.g. `overview.html?182`
* Open `suggest_matches.html` in a browser to see a map which suggests matching FHRS establishments for OSM entities (see below). Adding a question mark followed by the district ID loads data for that district e.g. `suggest_matches.html?182`
* The `compare` and `suggest_matches` database views can be used to compare FHRS with OSM data and suggest matching FHRS establishments for OSM entities. (These are used to create GeoJSON files for the slippy maps)
* The `postcode_mismatch` database view can be used to list OSM entities with an `fhrs:id` tag for which the FHRS postcode does not match the OSM one

## Overview map

![Example overview map](overview.jpg)

Multiple establishments in the same location are aggregated because the FHRS position data is reverse geocoded from postcodes
* Locations with at least one OSM entity with an `fhrs:id` value not present in the FHRS data table are **red** e.g. establishments that have closed and are no longer present in the FHRS database
* Locations with at least one OSM entity with no `fhrs:id` tag are **yellow**
* Locations containing at least one establishment from the FHRS database with no matching OSM entity (matched using `fhrs:id` tag) are **blue**
* Locations containing only OSM entities with a valid `fhrs:id` value are **green**

Clicking on a point shows a popup with the name of any OSM entities or FHRS establishments, which link to the FHRS web page for that establishment

## Suggested matches map

![Example suggested matches map](match.jpg)

By default, this map shows OSM entities with possible matches in the FHRS database, based on the following criteria:
* < 250m distance
* Either FHRS name contains OSM name within it or names are closely matched using Levenshtein distance algorithm

Clicking on a point shows links to the OSM node/way web page and the FHRS establishment web page, as well as allowing the user to copy relevant tag/value pairs into JOSM

## Notes

OSM ways are simplified to a single point at the center of the way. We use a modified version of overpy (overpy_mod) which, amongst other things, allows way centroids to be parsed. Hopefully this functionality will be included in later versions of overpy as I have made my modifications available through pull requests


## Copyright

Copyright &copy; [gregrs-uk](http://github.com/gregrs-uk/) 2016, published under the GNU GPL v3.0

Modified version of [overpy](http://github.com/DinoTools/python-overpy) contained in `overpy_mod` directory is copyright &copy; 2014 PhiBo ([DinoTools](http://github.com/DinoTools/)), published under the MIT licence
