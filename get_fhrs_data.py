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

# comment out line below to get data for all authorities, not just Rugby & Warwick
fhrs_authorities = [371, 373]

print "Creating FHRS establishment database table"
fhrs.create_establishment_table(connection=con)

for this_authority in fhrs_authorities:
    print "Getting data for authority " + str(this_authority)
    xmlstring = fhrs.download_establishments_for_authority(this_authority)
    print "Writing data for authority " + str(this_authority)
    fhrs.write_establishments(xmlstring, con)
