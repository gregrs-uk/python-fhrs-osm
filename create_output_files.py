from fhrs_osm import *
from datetime import datetime, date
import config

db = Database(dbname=config.dbname)
db.connect()

print "Getting list of districts which contain some data"
districts = db.get_inhabited_districts()

json_details = [{'filename': 'overview', 'method': db.get_overview_geojson},
                {'filename': 'suggest-matches', 'method': db.get_suggest_matches_geojson},
                {'filename': 'distant-matches', 'method': db.get_distant_matches_geojson},
                {'filename': 'boundary', 'method': db.get_district_boundary_geojson}]

gpx_details = [{'filename': 'fhrs-unmatched',
                'geog_col': 'fhrs_geog',
                'name_col':'fhrs_name',
                'view_name':'compare',
                'district_id_col':'fhrs_district_id',
                'status':'FHRS'},
               {'filename': 'osm-unmatched-with-postcode',
                'geog_col':'osm_geog',
                'name_col':'osm_name',
                'view_name':'compare',
                'district_id_col':'osm_district_id',
                'status':'OSM_with_postcode'},
               {'filename': 'osm-unmatched-no-postcode',
                'geog_col':'osm_geog',
                'name_col':'osm_name',
                'view_name':'compare',
                'district_id_col':'osm_district_id',
                'status':'OSM_no_postcode'},
               {'filename': 'osm-invalid-fhrsid',
                'geog_col':'osm_geog',
                'name_col':'osm_name',
                'view_name':'compare',
                'district_id_col':'osm_district_id',
                'status':'mismatch'},
               {'filename': 'suggested-matches',
                'geog_col':'osm_geog',
                'name_col':'osm_name',
                'view_name':'suggest_matches',
                'district_id_col':'osm_district_id',
                'status':None}
              ]

# loop round inhabited districts to create relevant files for each district

for dist in districts:
    print "Creating GeoJSON, GPX, CSV and HTML files for " + dist['name']

    # create GeoJSON files as specified in json_details above
    for this_json in json_details:
        path = 'html/json/' + this_json['filename'] + '-' + str(dist['id']) + '.json'
        f = open(path, 'w')
        f.write(this_json['method'](district_id=dist['id']))
        f.close

    # create GPX files as specified in gpx_details above
    for this_gpx in gpx_details:
        path = 'html/gpx/' + this_gpx['filename'] + '-' + str(dist['id']) + '.gpx'
        f = open(path, 'w')
        f.write(db.get_gpx(geog_col=this_gpx['geog_col'],
                           name_col=this_gpx['name_col'],
                           view_name=this_gpx['view_name'],
                           district_id_col=this_gpx['district_id_col'],
                           district_id=dist['id'],
                           status=this_gpx['status']))
        f.close

    # create CSV file of mismatches for 'Survey Me!' tool
    path = 'html/csv/osm-invalid-fhrsid-' + str(dist['id']) + '.csv'
    f = open(path, 'w')
    f.write(db.get_csv(district_id=dist['id'], status='mismatch'))
    f.close

    # add stats to district's dictionary so that we can access them later
    dist['stats'] = db.get_district_stats(district_id=dist['id'])
    postcode_errors = db.get_district_postcode_errors(district_id=dist['id'])
    mismatches = db.get_district_mismatches(district_id=dist['id'])
    duplicates = db.get_district_duplicates(district_id=dist['id'])
    distant_matches = db.get_district_distant_matches(district_id=dist['id'])

    html = ("""
<!DOCTYPE html>
<html>
<head>
    <title>FHRS/OSM comparison for """ + dist['name'] + """</title>
    <meta charset="utf-8" />

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.2.0/dist/leaflet.css"
      integrity="sha512-M2wvCLH6DSRazYeZRIm1JnYyh22purTM+FDB5CsyxtQJYeKq83arPe5wgbNmcFXGqiSH2XR8dT/fJISVA1r/zQ=="
      crossorigin=""/>

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
            <td style='color: #4daf4a;'>
                OSM objects with valid fhrs:id and matching addr:postcode or
                not:addr:postcode</td>
            <td>""" + str(dist['stats']['matched']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td><span style='color: #c03ca5;'>
                Relevant OSM objects with postcode but no valid fhrs:id</span></td>
            <td>""" + str(dist['stats']['OSM_with_postcode']) + """</td>
            <td><a href="gpx/osm-unmatched-with-postcode-""" +
                str(dist['id']) + """.gpx" download>GPX</a></td>
        </tr>
        <tr>
            <td style='color: #ff7f00;'>
                Relevant OSM objects without postcode or fhrs:id</td>
            <td>""" + str(dist['stats']['OSM_no_postcode']) + """</td>
            <td><a href="gpx/osm-unmatched-no-postcode-""" +
                str(dist['id']) + """.gpx" download>GPX</a></td>
        </tr>
            <tr>
            <td style='color: #e31a1c;'>
                OSM objects with valid fhrs:id but mismatched/missing postcode</td>
            <td>""" + str(dist['stats']['matched_postcode_error']) + """</td>
            <td></td>
        </tr>
        <tr>
            <td style='color: #e31a1c;'>OSM objects with invalid fhrs:id</td>
            <td>""" + str(dist['stats']['mismatch']) + """</td>
            <td><a href="gpx/osm-invalid-fhrsid-""" +
                str(dist['id']) + """.gpx" download>GPX</a></td>
        </tr>
        <tr>
            <td style='color: #007fff;'>FHRS establishments with no matching OSM object</td>
            <td>""" + str(dist['stats']['FHRS']) + """</td>
            <td><a href="gpx/fhrs-unmatched-""" +
                str(dist['id']) + """.gpx" download>GPX</a></td>
        </tr>
        <tr>
            <td>Total number of relevant OSM objects</td>
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
            <td>Percentage of relevant OSM objects with a postcode**</td>
            <td>""" + '%.1f' % dist['stats']['OSM_matched_or_postcode_pc'] + """%</td>
            <td></td>
        </tr>
    </table>
    <p style="font-size: 80%">*A match is considered successful when the OSM objects's fhrs:id
    matches an FHRS one and the OSM addr:postcode or not:addr:postcode matches the FHRS one.</p>
    <p style="font-size: 80%">**OSM objects with an addr:postcode or not:addr:postcode that
    matches the FHRS postcode, or with an addr:postcode but no fhrs:id tag.</p>

    <h3>District progress graphs</h3>
    <p>Click on a graph below to enlarge it. There are also
    <a href="../fhrs-stats/summary-graphs.html">graphs showing progress across the whole of
    Great Britain</a></p>
    <a href="../fhrs-stats/district-graphs/fhrs-no-""" + str(dist['id']) + """.png">
    <img src="../fhrs-stats/district-graphs/fhrs-no-""" + str(dist['id']) +""".png" width=450>
    </a>
    <a href="../fhrs-stats/district-graphs/fhrs-pc-""" + str(dist['id']) + """.png">
    <img src="../fhrs-stats/district-graphs/fhrs-pc-""" + str(dist['id']) + """.png" width=450>
    </a><br>
    <a href="../fhrs-stats/district-graphs/osm-no-""" + str(dist['id']) + """.png">
    <img src="../fhrs-stats/district-graphs/osm-no-""" + str(dist['id']) + """.png" width=450>
    </a>
    <a href="../fhrs-stats/district-graphs/osm-pc-""" + str(dist['id']) + """.png">
    <img src="../fhrs-stats/district-graphs/osm-pc-""" + str(dist['id']) + """.png" width=450>
    </a>

    <h3>Overview</h3>
    <p>Dotted lines in the map below show the difference between the OSM and FHRS locations for
    establishments that have been matched when those locations are more than """ +
    str(config.warning_distance_metres) + """ metres apart. Please see the table below for a
    list of these distant matches.</p>
    <div id="overview_map" style="width: 800px; height: 600px"></div>

    <h3>Suggested matches</h3>
    <p><a href="gpx/suggested-matches-""" + str(dist['id']) + """.gpx" download>
        Download suggested matches GPX</a></p>
    <div id="suggest_matches_map" style="width: 800px; height: 600px"></div>

    <h3>Postcodes missing/mismatched</h3>""")

    if len(postcode_errors) < 1:
        html += "<p>There are no postcode errors to show for this district.</p>"
    else:
        html += ('<p>Below is a list of OSM entities which have a valid fhrs:id tag but a ' +
                 'missing/mismatched addr:postcode. N.B. This does not necessarily indicate an ' +
                 'error with the OSM data. If a not:addr:postcode tag matching the FHRS ' +
                 'postcode is found, the OSM entity is removed from the table and is ' +
                 'instead considered a successful match.</p>\n' +
                 '<table>\n' +
                 '    <tr><th>Name</th><th>OSM addr:postcode</th><th>FHRS postcode</th><th></th></tr>\n')
        for this_error in postcode_errors:
            html += ('<tr><td><a href="' + db.osm_url_prefix + this_error['osm_type'] + '/' +
                     str(this_error['osm_id']) + '" target="_blank">' +
                     str(this_error['osm_name']) + '</a></td>\n' +
                     '<td>' + str(this_error['osm_postcode']) + '</td>\n' +
                     '<td>' + str(this_error['fhrs_postcode'])+ '</td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix +
                     'load_object?objects=' + this_error['osm_ident'])
            if this_error['osm_postcode'] == None:
                html += ('&addtags=' + this_error['add_tags_string'] +
                         '\" target="_blank">Add tags in JOSM')
            else:
                html += '\" target="_blank">Edit in JOSM'
            html += '</a></td></tr>\n'
        html += '</table>'

    html += ("""
    <h3>Mismatched fhrs:id tags</h3>""")

    if len(mismatches) < 1:
        html += "<p>There are no fhrs:id mismatches to show for this district.</p>"
    else:
        html += ('<p>Below is a list of OSM entities which have an fhrs:id tag for which there ' +
                 'is no matching FHRS establishment. This may indicate an establishment which ' +
                 'has closed, but please check before making any changes to the OSM data. ' +
                 'Parsing multiple FHRS IDs separated by semicolons is currently unsupported so ' +
                 'these may also appear below.</p>\n' +
                 '<table>\n' +
                 '    <tr><th>Name</th><th>FHRS ID</th><th></th></tr>\n')
        for this_error in mismatches:
            html += ('<tr><td><a href="' + db.osm_url_prefix + this_error['osm_type'] + '/' +
                     str(this_error['osm_id']) + '" target="_blank">' + str(this_error['osm_name']) + '</a></td>\n' +
                     '<td>' + str(this_error['osm_fhrsid']) + '</td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix + 'load_object?objects=' +
                     this_error['osm_ident'] + '\" target="_blank">Edit in JOSM</a></td></tr>\n')
        html += '</table>'

    html += ("""
    <h3>Duplicate fhrs:id tags</h3>""")

    if len(duplicates) < 1:
        html += "<p>There are no fhrs:id duplicates to show for this district.</p>"
    else:
        html += ('<p>Below is a list of all the OSM entities which have an fhrs:id tag that is ' +
                 'shared with at least one of the OSM entities in this district. N.B. This does ' +
                 'not necessarily indicate an error with the OSM data.</p>' +
                 '<table>\n' +
                 '    <tr><th>FHRS ID</th><th>OSM name</th><th>FHRS name</th><th></th></tr>\n')
        for this_error in duplicates:
            html += ('<tr><td>' + this_error['fhrs:id'] + '</td>' +
                     '<td><a href="' + db.osm_url_prefix + this_error['type'] + '/' +
                     str(this_error['id']) + '" target="_blank">' +
                     str(this_error['osm_name']) + '</a></td>\n' +
                     '<td><a href="' + db.fhrs_est_url_prefix + this_error['fhrs:id'] +
                     db.fhrs_est_url_suffix + '" target="_blank">' +
                     str(this_error['fhrs_name']) + '</a></td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix + 'load_object?objects=' +
                     this_error['osm_ident'] + '\" target="_blank">Edit in JOSM</a></td></tr>\n')
        html += '</table>'

    html += ("""
    <h3>Distant matches</h3>""")

    if len(distant_matches) < 1:
        html += "<p>There are no distant matches to show for this district.</p>"
    else:
        html += ('<p>Below is a list of all the OSM entities which have been matched to an FHRS ' +
                 'establishment where the OSM and FHRS locations are more than ' +
                 str(config.warning_distance_metres) + ' metres apart. N.B. This does ' +
                 'not necessarily indicate an error with the OSM data as OSM locations tend ' +
                 'to be more accurate than those in the FHRS database.</p>' +
                 '<table>\n' +
                 '    <tr><th>OSM name</th><th>FHRS name</th><th>Distance / m</th><th></th></tr>\n')
        for this_error in distant_matches:
            html += ('<tr><td><a href="' + db.osm_url_prefix + this_error['osm_type'] + '/' +
                     str(this_error['osm_id']) + '" target="_blank">' +
                     str(this_error['osm_name']) + '</a></td>\n' +
                     '<td><a href="' + db.fhrs_est_url_prefix + str(this_error['fhrs_id']) +
                     db.fhrs_est_url_suffix + '" target="_blank">' +
                     str(this_error['fhrs_name']) + '</a></td>\n' +
                     '<td>' + str(int(this_error['distance'])) + '</td>\n' +
                     '<td><a href=\"' + db.josm_url_prefix + 'load_object?objects=' +
                     this_error['osm_ident'] + '\" target="_blank">Edit in JOSM</a></td></tr>\n')
        html += '</table>'

    html += ("""

    <hr>

    <p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm" target="_blank">
    python-fhrs-osm</a> on """ +
    datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """.</p>

    <p><a href="https://github.com/gregrs-uk/python-fhrs-osm/issues" target="_blank">
    Report bug or suggest feature</a></p>

    <p>Contains <a href="http://www.ordnancesurvey.co.uk" target="_blank">Ordnance Survey</a>
    data &copy Crown copyright and database right</p>

    <script src="https://unpkg.com/leaflet@1.2.0/dist/leaflet.js"
      integrity="sha512-lInM/apFSqyy1o6s89K4iQUKg6ppXEgsVxT35HbzUupEVRh2Eu9Wdl4tHj7dZO0s1uvplcYGmt3498TtHq+log=="
      crossorigin=""></script>
    <script src="https://code.jquery.com/jquery-2.1.0.min.js"></script>

    <script>

        // create maps

        var overview_map = L.map('overview_map').setView([52.372, -1.263], 16);
        var suggest_matches_map = L.map('suggest_matches_map').setView([52.372, -1.263], 16);


        // add OSM tile layer to each map

        L.tileLayer('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://openstreetmap.org" target="_blank">OpenStreetMap' +
                '</a> contributors. Contains <a href="http://www.ordnancesurvey.co.uk"' +
                'target="_blank">Ordnance Survey</a> and ' +
                '<a href="http://ratings.food.gov.uk/open-data/" target="_blank">' +
                'Food Hygiene Rating Scheme</a> data &copy Crown copyright and database right'
        }).addTo(overview_map);

        L.tileLayer('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://openstreetmap.org" target="_blank">OpenStreetMap' +
                '</a> contributors. Contains <a href="http://www.ordnancesurvey.co.uk"' +
                'target="_blank">Ordnance Survey</a> and ' +
                '<a href="http://ratings.food.gov.uk/open-data/" target="_blank">' +
                'Food Hygiene Rating Scheme</a> data &copy Crown copyright and database right'
        }).addTo(suggest_matches_map);


        // get district boundary JSON, add to maps and fit bounds

        var boundary_json = './json/boundary-""" + str(dist['id']) + """.json';

        var geojsonBoundaryOptions = {
            color: "black",
            weight: 2,
            opacity: 1,
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
            radius: 3,
            color: "white",
            weight: 0,
            opacity: 0.75,
            fillColor: "black",
            fillOpacity: 1
        };


        // function to style CircleMarkers and TileLayer after zoom event

        function setStyleFromZoom(e) {
            // max zoom above is 18
            // below zoom 14, markers should stay the same
            var currentZoom = e.target.getZoom();
            if (currentZoom <= 14) {
                newRadius = 3;
                newWeight = 0;
                newFillOpacity = 1;
                newTileOpacity = 0.75;
            }
            else {
                // do some maths based on values at zoom 14 and scaling
                var newRadius = ((currentZoom - 14) * 2.25) + 3;
                var newWeight = ((currentZoom - 14) * 0.5) + 0;
                var newFillOpacity = ((currentZoom - 14) * -0.125) + 1;
                var newTileOpacity = ((currentZoom - 14) * 0.0625) + 0.75;
            }
            // iterate through all layers and style each
            e.target.eachLayer(function(layer) {
                if (layer instanceof L.CircleMarker) {
                    layer.setStyle({
                        "radius": newRadius,
                        "weight": newWeight,
                        "fillOpacity": newFillOpacity
                    });
                }
                else if (layer instanceof L.TileLayer) {
                    layer.setOpacity(newTileOpacity)
                }
            });
        }


        // add distant matches layer to overview map

        var distant_matches_json = './json/distant-matches-""" + str(dist['id']) + """.json';

        $.getJSON(distant_matches_json, function(data) {
            var overviewLineLayer = L.geoJson(data, {
                style: {
                    "color": "black",
                    "weight": 3,
                    "opacity": 0.5,
                    "dashArray": "5, 5"
                }
            }).addTo(overview_map);
            overviewLineLayer.bringToFront();
        });


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
                        return {fillColor: "#e31a1c"};
                    } else if (feature.properties.osm_no_postcode > 0) {
                        // at least one OSM to be matched without postcode
                        return {fillColor: "#ff7f00"};
                    } else if (feature.properties.osm_with_postcode > 0) {
                        // at least one OSM to be matched
                        return {fillColor: "#c03ca5"};
                    } else if (feature.properties.fhrs > 0) {
                        // at least one FHRS to be matched
                        return {fillColor: "#007fff"};
                    } else {
                        // all matched
                        return {fillColor: "#4daf4a"};
                    }
                }
            }).addTo(overview_map);

            overview_map.on('zoomend', setStyleFromZoom);
            setStyleFromZoom({target: overview_map}); // set initial style
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
                        return {fillColor: "#c03ca5"};
                    }
                    else {
                        // OSM entity has no postcode
                        return {fillColor: "#ff7f00"};
                    }
                }
            }).addTo(suggest_matches_map);

            suggest_matches_map.on('zoomend', setStyleFromZoom);
            setStyleFromZoom({target: suggest_matches_map}); // set initial style
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

<p><a href="../fhrs-stats/summary-graphs.html"
style="padding: 0.5em; border: 1px solid black; background: #ffffd0;">
Graphs for the whole of Great Britain</a></p>

<h2>Districts</h2>

<p style="font-size: 80%">Matched: % of FHRS establishments matched to an OSM object using
the fhrs:id tag. N.B. the OSM addr:postcode or not:addr:postcode must match the FHRS one.</p>
<p style="font-size: 80%">Postcodes: % of OSM objects with an addr:postcode or not:addr:postcode
that matches the FHRS one or with an addr:postcode tag and no fhrs:id tag.</p>

<table>
<tr><th>District</th><th>Matched</th><th>Postcodes</th></tr>
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

<p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm" target="_blank">
python-fhrs-osm</a> on """ +
datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """.</p>

<p><a href="https://github.com/gregrs-uk/python-fhrs-osm/issues" target="_blank">
Report bug or suggest feature</a></p>

<p>Contains <a href="http://www.ordnancesurvey.co.uk" target="_blank">Ordnance Survey</a>
data &copy Crown copyright and database right</p>

</body>
</html>
""")

f = open('html/index.html', 'w')
f.write(html)
f.close

f = open('html/stats-' + date.today().isoformat() + '.csv', 'w')
f.write(csvstring)
f.close
