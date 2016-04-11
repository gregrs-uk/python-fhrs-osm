from fhrs_osm import *

db = Database()
db.connect()

db.add_fhrs_districts()
db.add_osm_districts()
