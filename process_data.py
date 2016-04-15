from fhrs_osm import *

db = Database()
db.connect()

# compute districts
print "Adding district ID for FHRS establishments"
db.add_fhrs_districts()
print "Adding district ID for OSM entities"
db.add_osm_districts()

# create database views
print "Creating database view for data comparison"
db.create_comparison_view()
print "Creating database view to suggest FHRS/OSM matches"
db.create_suggest_matches_view()
