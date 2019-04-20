from fhrs_osm import *
import config

db = Database(dbname=config.dbname)
con = db.connect()

osm = OSMDataset()
fhrs = FHRSDataset()

# get FHRS establishments that aren't matched in OSM
fhrs_cur = con.cursor(cursor_factory=DictCursor)
sql = ("SELECT fhrs_name, fhrs_postcode, fhrs_fhrsid FROM compare\n" +
       "WHERE fhrs_district_id = 86\n" +
       "AND status IN ('FHRS', 'mismatch')\n" +
       "AND fhrs_postcode IS NOT NULL\n" +
       "ORDER BY fhrs_postcode")
fhrs_cur.execute(sql)

print """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        table.sub, .sub th, .sub td {
            border: none;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.25em;
        }
    </style>
</head>
<body>
<h1>Possible OSM matches for FHRS establishments by postcode</h1>
<table class="main">
    <tr>
        <th>Postcode</th>
        <th>FHRS establishment</th>
        <th>OSM nodes/ways</th>
    </tr>
"""

for fhrs_row in fhrs_cur.fetchall():
    this_fhrs_postcode = fhrs_row['fhrs_postcode'].strip()
    osm_cur = con.cursor(cursor_factory=DictCursor)
    sql = ("SELECT osm_name, osm_type, osm_id FROM compare\n" +
           "WHERE osm_district_id = 86\n" +
           "AND osm_postcode = '" + this_fhrs_postcode + "'\n" +
           "AND status = 'OSM_with_postcode'")
    osm_cur.execute(sql)
    # if there are any OSM entities with matching postcodes
    if osm_cur.rowcount:
        print "<tr>"
        print "<td>" + this_fhrs_postcode + "</td>"
        print ('<td><a href="https://ratings.food.gov.uk/business/en-GB/' +
               str(fhrs_row['fhrs_fhrsid']) + '" target="_blank">' +
               fhrs_row['fhrs_name'] + '</a></td>')
        print '<td>'
        for osm_row in osm_cur.fetchall():
            this_osm_name = (osm_row['osm_name']
                             if osm_row['osm_name'] is not None
                             else "[Unnamed]")
            this_osm_link = ("https://www.openstreetmap.org/" +
                             osm_row['osm_type'].strip() + "/" +
                             str(osm_row['osm_id']))
            this_osm_ident = osm_row['osm_type'][0] + str(osm_row['osm_id'])
            print ('<a href="' + this_osm_link + '" target="_blank">' +
                   this_osm_name + '</a> &ndash; ' +
                   '<a href="' + db.josm_url_prefix + 'load_object?objects=' +
                   this_osm_ident + '&addtags=fhrs:id=' +
                   str(fhrs_row['fhrs_fhrsid']) +
                   '" target="_blank">Match</a><br>')
        print "</td>"
        print "</tr>"

print "</table>\n\n</body>\n</html>"
