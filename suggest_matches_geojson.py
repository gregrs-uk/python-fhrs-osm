from fhrs_osm import *

db = Database()
db.connect()

print db.get_suggest_matches_geojson()
