from fhrs_osm import *

db = Database(dbname='fhrs')
con = db.connect()

# get OSM data
osm = OSMDataset()
print "Creating OSM database table"
osm.create_table(connection=con)
print "Running Overpass query"
result = osm.run_overpass_query()
print "Writing OSM data to database"
osm.write_result_nodes_and_ways(result=result, connection=con)

# get FHRS data
fhrs = FHRSDataset()
print "Creating FHRS database table"
fhrs.create_table(connection=con)

print "Getting list of FHRS authorities"
fhrs_authorities = fhrs.get_authorities()
# comment out line below to get data for all authorities, not just Rugby
fhrs_authorities = [371]

for this_authority in fhrs_authorities:
    print "Getting data for authority " + str(this_authority)
    xmlstring = fhrs.download_establishments_for_authority(this_authority)
    print "Writing data for authority " + str(this_authority)
    fhrs.write_establishments(xmlstring, con)

# create database views
print "Creating database view for data comparison"
db.create_comparison_view()
print "Creating database view for postcode mismatches"
db.create_postcode_mismatch_view()
print "Creating database view to suggest FHRS/OSM matches"
db.create_suggest_matches_view()
