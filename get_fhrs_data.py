from fhrs_osm import *
import config

db = Database(dbname=config.dbname)
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

# read the mode from the config file to work out what will be downloaded
if (config.get_fhrs_mode == 'small_test'):
    fhrs_authorities = [371, 373]
elif (config.get_fhrs_mode == 'west_mids'):
    fhrs_authorities = fhrs.get_authorities(connection=con, region_name='West Midlands')
elif (config.get_fhrs_mode == 'full'):
    fhrs_authorities = fhrs.get_authorities(connection=con)
else:
    raise RuntimeError("Bad value for get_fhrs_mode in config.py\n"
                       "Should be 'small_test', 'west_mids' or 'full'")

print "Creating FHRS establishment database table"
fhrs.create_establishment_table(connection=con)

for this_authority in fhrs_authorities:
    print "Getting data for authority " + str(this_authority)
    xmlstring = fhrs.download_establishments_for_authority(this_authority)
    print "Writing data for authority " + str(this_authority)
    fhrs.write_establishments(xmlstring, con)
