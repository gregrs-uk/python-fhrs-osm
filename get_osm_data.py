from fhrs_osm import *
import config

db = Database(dbname=config.dbname)
con = db.connect()

fhrs = FHRSDataset()

print 'Calculating geographical extent of FHRS data, ignoring outliers'
fhrs_bbox = fhrs.get_corrected_bbox(connection=con)

# get OSM data within matching bounding box
osm = OSMDataset()
print "Creating OSM database table"
osm.create_table(connection=con)
if config.use_xml_file is True:
    print "Parsing OSM XML file"
    result = osm.parse_xml_file('data/filtered.osm')
    print "Writing OSM data to database"
    osm.write_result_nodes_and_ways(result=result, connection=con, filter_ways=False)
else:
    print "Running Overpass query"
    result = osm.run_overpass_query(bbox=fhrs_bbox)
    if len(result.get_node_ids()) + len(result.get_way_ids()) < 1:
        print "Overpass query result appears to be empty. Stopping."
        exit(1)
    print "Writing OSM data to database"
    osm.write_result_nodes_and_ways(result=result, connection=con, filter_ways=False)
