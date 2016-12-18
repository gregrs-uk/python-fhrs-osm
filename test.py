from fhrs_osm import *

db = Database()
db.connect()

print db.get_district_boundary_geojson(simplify=0.002)
