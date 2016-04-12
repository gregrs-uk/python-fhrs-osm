from fhrs_osm import *

db = Database()
db.connect()

print "Getting list of districts which contain some data"
district_dicts = db.get_inhabited_districts()
# blank list to hold district IDs
districts = []
for dist in district_dicts:
    districts.append(dist['id'])

for this_id in districts:
    print "Creating overview GeoJSON for district " + str(this_id)
    filename = 'html/json/overview-' + str(this_id) + '.json'
    f = open(filename, 'w')
    f.write(db.get_overview_geojson(district_id=this_id))
    f.close

    print "Creating suggest matches GeoJSON for district " + str(this_id)
    filename = 'html/json/suggest-matches-' + str(this_id) + '.json'
    f = open(filename, 'w')
    f.write(db.get_suggest_matches_geojson(district_id=this_id))
    f.close
