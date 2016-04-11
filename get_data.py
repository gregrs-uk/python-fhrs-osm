from fhrs_osm import *

db = Database(dbname='fhrs')
con = db.connect()

# get FHRS data
fhrs = FHRSDataset()
print "Creating FHRS authority database table"
fhrs.create_authority_table(connection=con)

print "Getting data for FHRS authorities"
xmlstring = fhrs.download_authorities()
print "Writing data for FHRS authorities"
fhrs.write_authorities(xmlstring, con)
print "Querying database for authority IDs"
# remove region_name argument below to get authorities in all regions
fhrs_authorities = fhrs.get_authorities(connection=con, region_name='West Midlands')

# comment out line below to get data for all authorities, not just Rugby
fhrs_authorities = [371, 375, 373]

print "Creating FHRS establishment database table"
fhrs.create_establishment_table(connection=con)

for this_authority in fhrs_authorities:
    print "Getting data for authority " + str(this_authority)
    xmlstring = fhrs.download_establishments_for_authority(this_authority)
    print "Writing data for authority " + str(this_authority)
    fhrs.write_establishments(xmlstring, con)

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
