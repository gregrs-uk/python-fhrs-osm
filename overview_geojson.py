from fhrs_osm import *

db = Database()
db.connect()

print db.get_overview_geojson()
