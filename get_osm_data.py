from fhrs_osm import *

db = Database(dbname='fhrs')
con = db.connect()

fhrs = FHRSDataset()

print 'Calculating geographical extent of FHRS data, ignoring outliers'
fhrs_bbox = fhrs.get_corrected_bbox(connection=con)

# get OSM data within matching bounding box
osm = OSMDataset()
print "Creating OSM database table"
osm.create_table(connection=con)
print "Running Overpass query"
result = osm.run_overpass_query(bbox=fhrs_bbox)
if len(result.get_node_ids()) + len(result.get_way_ids()) < 1:
    print "Overpass query result appears to be empty. Stopping."
    exit(1)
print "Writing OSM data to database"
osm.write_result_nodes_and_ways(result=result, connection=con)
