from fhrs_osm import *

db = Database(dbname='fhrs')
con = db.connect()

fhrs = FHRSDataset()

print 'Calculating geographical extent of FHRS data'
fhrs_bbox = fhrs.get_bbox(connection=con)

# get OSM data within matching bounding box
osm = OSMDataset()
print "Creating OSM database table"
osm.create_table(connection=con)
print "Running Overpass query"
result = osm.run_overpass_query(bbox=fhrs_bbox)
print "Writing OSM data to database"
osm.write_result_nodes_and_ways(result=result, connection=con)
