from fhrs_osm import *
from datetime import datetime, date
import config

db = Database(dbname=config.dbname)
db.connect()

print "Getting list of districts which contain some data"
districts = db.get_inhabited_districts()

# loop round inhabited districts to create relevant files for each district

for dist in districts:
    print "Creating GeoJSON, GPX and HTML files for " + dist['name']

    filename = 'html/json/overview-' + str(dist['id']) + '.json'
    f = open(filename, 'w')
    f.write(db.get_overview_geojson(district_id=dist['id']))
    f.close

    filename = 'html/json/suggest-matches-' + str(dist['id']) + '.json'
    f = open(filename, 'w')
    f.write(db.get_suggest_matches_geojson(district_id=dist['id']))
    f.close

    filename = 'html/json/boundary-' + str(dist['id']) + '.json'
    f = open(filename, 'w')
    f.write(db.get_district_boundary_geojson(district_id=dist['id']))
    f.close

    filename = 'html/gpx/fhrs-unmatched-' + str(dist['id']) + '.gpx'
    f = open(filename, 'w')
    f.write(db.get_gpx(geog_col='fhrs_geog', name_col='fhrs_name',
                       view_name='compare', district_id_col='fhrs_district_id',
                       district_id=dist['id'], status='FHRS'))
    f.close

    filename = 'html/gpx/osm-unmatched-with-postcode-' + str(dist['id']) + '.gpx'
    f = open(filename, 'w')
    f.write(db.get_gpx(geog_col='osm_geog', name_col='osm_name',
                       view_name='compare', district_id_col='osm_district_id',
                       district_id=dist['id'], status='OSM_with_postcode'))
    f.close

    filename = 'html/gpx/osm-unmatched-no-postcode-' + str(dist['id']) + '.gpx'
    f = open(filename, 'w')
    f.write(db.get_gpx(geog_col='osm_geog', name_col='osm_name',
                       view_name='compare', district_id_col='osm_district_id',
                       district_id=dist['id'], status='OSM_no_postcode'))
    f.close

    filename = 'html/gpx/osm-invalid-fhrsid-' + str(dist['id']) + '.gpx'
    f = open(filename, 'w')
    f.write(db.get_gpx(geog_col='osm_geog', name_col='osm_name',
                       view_name='compare', district_id_col='osm_district_id',
                       district_id=dist['id'], status='mismatch'))
    f.close

    filename = 'html/gpx/suggested-matches-' + str(dist['id']) + '.gpx'
    f = open(filename, 'w')
    f.write(db.get_gpx(geog_col='osm_geog', name_col='osm_name',
                       view_name='suggest_matches', district_id_col='osm_district_id',
                       district_id=dist['id']))
    f.close

    # add stats to district's dictionary so that we can access them later
    dist['stats'] = db.get_district_stats(district_id=dist['id'])
    postcode_errors = db.get_district_postcode_errors(district_id=dist['id'])
    mismatches = db.get_district_mismatches(district_id=dist['id'])

    html = ("""
<!DOCTYPE html>
<html>
<head>
    <title>FHRS/OSM comparison for """ + dist['name'] + """</title>
    <meta charset="utf-8" />

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/leaflet.css" />

    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.25em;
        }
    </style>
</head>
<body>

    <h1>FHRS/OSM comparison</h1>
    <h2>""" + dist['name'] + """</h2>

    <h3>District statistics</h3>
    <p>The colours in this table act as a key for the maps below</p>
    <table>
        <tr>
            <td style='color: green'>
                OSM nodes/ways with valid fhrs:id and matching postcode</td>
            <td>""" + str(dist['stats']['matched']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td><span style='color: yellow; background-color: gray'>
                Relevant OSM nodes/ways with postcode but no valid fhrs:id</span></td>
            <td>""" + str(dist['stats']['OSM_with_postcode']) + """</td>
            <td><a href="gpx/osm-unmatched-with-postcode-""" +
                str(dist['id']) + """.gpx">GPX</a></td>
        </tr>
        <tr>
            <td style='color: orange;'>
                Relevant OSM nodes/ways without postcode or fhrs:id</td>
            <td>""" + str(dist['stats']['OSM_no_postcode']) + """</td>
            <td><a href="gpx/osm-unmatched-no-postcode-""" +
                str(dist['id']) + """.gpx">GPX</a></td>
        </tr>
            <tr>
            <td style='color: red;'>
                OSM nodes/ways with valid fhrs:id but mismatched/missing postcode</td>
            <td>""" + str(dist['stats']['matched_postcode_error']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td style='color: red;'>OSM nodes/ways with invalid fhrs:id</td>
            <td>""" + str(dist['stats']['mismatch']) + """</td>
            <td><a href="gpx/osm-invalid-fhrsid-""" +
                str(dist['id']) + """.gpx">GPX</a></td>
        </tr>
        <tr>
            <td style='color: blue;'>FHRS establishments with no matching OSM node/way</td>
            <td>""" + str(dist['stats']['FHRS']) + """</td>
            <td><a href="gpx/fhrs-unmatched-""" +
                str(dist['id']) + """.gpx">GPX</a></td>
        </tr>
        <tr>
            <td>Total number of relevant OSM nodes/ways</td>
            <td>""" + str(dist['stats']['total_OSM']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td>Total number of FHRS establishments</td>
            <td>""" + str(dist['stats']['total_FHRS']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td>Percentage of FHRS establishments successfully matched*</td>
            <td>""" + '%.1f' % dist['stats']['FHRS_matched_pc'] + """%</td>
            <td></td>
        </tr>
        <tr>
            <td>Percentage of relevant OSM nodes/ways with a postcode**</td>
            <td>""" + '%.1f' % dist['stats']['OSM_matched_or_postcode_pc'] + """%</td>
            <td></td>
        </tr>
    </table>
    <p style="font-size: 80%">*A match is considered successful when the OSM node/way's fhrs:id
    matches an FHRS one and their postcodes are identical.
    <p style="font-size: 80%">**OSM nodes/ways with a postcode that matches the FHRS one or with a
    postcode but no fhrs:id tag.</p>

    <h3>Overview</h3>
    <div id="overview_map" style="width: 800px; height: 600px"></div>

    <h3>Suggested matches</h3>
    <p><a href="gpx/suggested-matches-""" + str(dist['id']) + """.gpx">
        Download suggested matches GPX</a></p>
    <div id="suggest_matches_map" style="width: 800px; height: 600px"></div>

    <h3>Postcodes missing/mismatched</h3>""")

    if len(postcode_errors) < 1:
        html += "<p>There are no postcode errors to show for this district.</p>"
    else:
        html += ('<p>Below is a list of OSM entities which have a valid fhrs:id tag but a missing/mismatched addr:postcode. ' +
                 'N.B. This does not necessarily indicate an error with the OSM data.</p>' +
                 '<table>\n' +
                 '    <tr><th>Name</th><th>OSM addr:postcode</th><th>FHRS postcode</th><th></th></tr>\n')
        for this_error in postcode_errors:
            html += ('<tr><td><a href="' + db.osm_url_prefix + this_error['osm_type'] + '/' +
                     str(this_error['osm_id']) + '">' + str(this_error['osm_name']) + '</a></td>\n' +
                     '<td>' + str(this_error['osm_postcode']) + '</td>\n' +
                     '<td>' + str(this_error['fhrs_postcode'])+ '</td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix + 'load_object?objects=' +
                     this_error['osm_ident'] + '\">Edit in JOSM</a></td></tr>\n')
        html += '</table>'

    html += ("""
    <h3>Mismatched fhrs:id tags</h3>""")

    if len(mismatches) < 1:
        html += "<p>There are no fhrs:id mismatches to show for this district.</p>"
    else:
        html += ('<p>Below is a list of OSM entities which have an fhrs:id tag for which there ' +
                 'is no matching FHRS establishment. This may indicate an establishment which ' +
                 'has closed, but please check before making any changes to the OSM data. ' +
                 'Parsing multiple FHRS IDs separated by semicolons is currently unsupported so' +
                 'these may also appear below.</p>' +
                 '<table>\n' +
                 '    <tr><th>Name</th><th>FHRS ID</th><th></th></tr>\n')
        for this_error in mismatches:
            html += ('<tr><td><a href="' + db.osm_url_prefix + this_error['osm_type'] + '/' +
                     str(this_error['osm_id']) + '">' + str(this_error['osm_name']) + '</a></td>\n' +
                     '<td><a href=\"' + db.fhrs_est_url_prefix + str(this_error['osm_fhrsid']) +
                     db.fhrs_est_url_suffix + '\">' + str(this_error['osm_fhrsid']) + '</a></td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix + 'load_object?objects=' +
                     this_error['osm_ident'] + '\">Edit in JOSM</a></td></tr>\n')
        html += '</table>'

    html += ("""

    <hr>

    <p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm">""" +
    """python-fhrs-osm</a> on """ +
    datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """.</p>

    <p><a href="https://github.com/gregrs-uk/python-fhrs-osm/issues">Report bug or suggest feature</a></p>

    <p>Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> data
    &copy Crown copyright and database right</p>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/leaflet.js"></script>
    <script src="https://code.jquery.com/jquery-2.1.0.min.js"></script>

    <script>

        // create maps

        var overview_map = L.map('overview_map').setView([52.372, -1.263], 16);
        var suggest_matches_map = L.map('suggest_matches_map').setView([52.372, -1.263], 16);


        // add OSM tile layer to each map

        L.tileLayer('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
                'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
                '<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
                'data &copy Crown copyright and database right'
        }).addTo(overview_map);

        L.tileLayer('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
                'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
                '<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
                'data &copy Crown copyright and database right'
        }).addTo(suggest_matches_map);


        // get district boundary JSON, add to maps and fit bounds

        var boundary_json = './json/boundary-""" + str(dist['id']) + """.json';

        var geojsonBoundaryOptions = {
            color: "#000",
            weight: 2,
            opacity: 1,
            fillColor: "#000",
            fillOpacity: 0
        }

        $.getJSON(boundary_json, function(data) {
            var overviewBoundaryLayer = L.geoJson(data, {
                style: geojsonBoundaryOptions
            }).addTo(overview_map);
            var matchesBoundaryLayer = L.geoJson(data, {
                style: geojsonBoundaryOptions
            }).addTo(suggest_matches_map);

            overviewBoundaryLayer.bringToBack();
            matchesBoundaryLayer.bringToBack();

            overview_map.fitBounds(overviewBoundaryLayer.getBounds());
            suggest_matches_map.fitBounds(matchesBoundaryLayer.getBounds());
        });


        // defaults for markers on both maps

        var geojsonMarkerOptions = {
            radius: 5,
            color: "black",
            fillColor: "cyan",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.5
        }


        // add marker layer to each map

        var overview_json = './json/overview-""" + str(dist['id']) + """.json';
        var suggest_matches_json = './json/suggest-matches-""" + str(dist['id']) + """.json';

        $.getJSON(overview_json, function(data) {
            var overviewMarkerLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, geojsonMarkerOptions);
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(feature.properties.list);
                },
                style: function(feature) {
                    if (feature.properties.mismatch +
                        feature.properties.matched_postcode_error > 0) {
                        // at least one mismatch or postcode error
                        return {fillColor: "red"};
                    } else if (feature.properties.osm_no_postcode > 0) {
                        // at least one OSM to be matched without postcode
                        return {fillColor: "orange"};
                    } else if (feature.properties.osm_with_postcode > 0) {
                        // at least one OSM to be matched
                        return {fillColor: "yellow"};
                    } else if (feature.properties.fhrs > 0) {
                        // at least one FHRS to be matched
                        return {fillColor: "blue"};
                    } else {
                        // all matched
                        return {fillColor: "lime"};
                    }
                }
            }).addTo(overview_map);

            overviewMarkerLayer.bringToFront();
        });

        $.getJSON(suggest_matches_json, function(data) {
            var matchesMarkerLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, geojsonMarkerOptions);
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(feature.properties.text);
                },
                style: function(feature) {
                    if (feature.properties.osm_postcode != null) {
                        // OSM entity has a postcode
                        return {fillColor: "yellow"};
                    }
                    else {
                        // OSM entity has no postcode
                        return {fillColor: "orange"};
                    }
                }
            }).addTo(suggest_matches_map);

            matchesMarkerLayer.bringToFront();
        });

    </script>

</body>
</html>
    """)

    filename = 'html/district-' + str(dist['id']) + '.html'
    f = open(filename, 'w')
    f.write(html)
    f.close

# loop round districts again to create index file and CSV file

print "Creating index HTML file and stats CSV file"

html = ("""
<!DOCTYPE html>
<html>
<head>
    <title>FHRS/OSM comparison</title>
    <meta charset="utf-8" />

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.25em;
        }
    </style>
</head>

<body>

<h1>FHRS/OSM comparison</h1>

<h2>Districts</h2>

<p style="font-size: 80%">Matched: % of OSM node/ways whose fhrs:id matches an FHRS one and
their postcodes are identical.
<p style="font-size: 80%">Postcode: % of OSM nodes/ways with a postcode that matches the FHRS one
or with a postcode but no fhrs:id tag.</p>

<table>
<tr><th>District</th><th>Matched</th><th>Postcode</th></tr>
    """)

csvstring = ('district_id,district_name,matched,OSM_with_postcode,OSM_no_postcode,' + 
             'matched_postcode_error,mismatch,FHRS_unmatched,total_OSM,total_FHRS,' +
             'FHRS_matched_pc,OSM_matched_or_postcode_pc\n')

for dist in districts:
    html += ('<tr><td><a href="district-' + str(dist['id']) + '.html">' + dist['name'] + '</a></td>' +
             '<td>' + '%.1f' % dist['stats']['FHRS_matched_pc'] + '%</td>'
             '<td>' + '%.1f' % dist['stats']['OSM_matched_or_postcode_pc'] + '%</td></tr>')

    csvstring += '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%.2f,%.2f\n' % (dist['id'], dist['name'],
                 dist['stats']['matched'], dist['stats']['OSM_with_postcode'],
                 dist['stats']['OSM_no_postcode'], dist['stats']['matched_postcode_error'],
                 dist['stats']['mismatch'], dist['stats']['FHRS'], dist['stats']['total_OSM'],
                 dist['stats']['total_FHRS'], dist['stats']['FHRS_matched_pc'],
                 dist['stats']['OSM_matched_or_postcode_pc'])

html += ("""
</table>

<hr>

<p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm">""" +
"""python-fhrs-osm</a> on """ +
datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """.</p>

<p><a href="https://github.com/gregrs-uk/python-fhrs-osm/issues">Report bug or suggest feature</a></p>

<p>Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> data
&copy Crown copyright and database right</p>

</body>
</html>
""")

f = open('html/index.html', 'w')
f.write(html)
f.close

f = open('html/stats-' + date.today().isoformat() + '.csv', 'w')
f.write(csvstring)
f.close
