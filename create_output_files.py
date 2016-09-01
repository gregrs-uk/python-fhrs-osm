from fhrs_osm import *
from datetime import datetime
import config

db = Database(dbname=config.dbname)
db.connect()

print "Getting list of districts which contain some data"
districts = db.get_inhabited_districts()

for dist in districts:
    print "Creating GeoJSON and HTML files for " + dist['name']

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

    stats = db.get_district_stats(district_id=dist['id'])
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
    </style>
</head>
<body>

    <h1>FHRS/OSM comparison</h1>
    <h2>""" + dist['name'] + """</h2>

	<h3>District statistics</h3>
	<table>
	    <tr>
	        <td>Total number of FHRS establishments</td>
	        <td>""" + str(stats['total_FHRS']) + """</td>
	    </tr>
	    <tr>
	        <td>Total number of relevant OSM nodes/ways</td>
	        <td>""" + str(stats['total_OSM']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: green'>OSM nodes/ways with valid fhrs:id and matching postcode</td>
	        <td>""" + str(stats['matched']) + """</td>
	    </tr>
	    <tr>
	        <td><span style='color: yellow; background-color: gray'>
            Relevant OSM nodes/ways with postcode but no valid fhrs:id</span></td>
	        <td>""" + str(stats['OSM_with_postcode']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: orange;'>Relevant OSM nodes/ways without fhrs:id or postcode</td>
	        <td>""" + str(stats['OSM_no_postcode']) + """</td>
	    </tr>
        <tr>
	        <td style='color: red;'>OSM nodes/ways with valid fhrs:id but mismatched/missing postcode</td>
	        <td>""" + str(stats['matched_postcode_error']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: red;'>OSM nodes/ways with invalid fhrs:id</td>
	        <td>""" + str(stats['mismatch']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: blue;'>FHRS establishments with no matching OSM node/way</td>
	        <td>""" + str(stats['FHRS']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: green;'>Percentage of FHRS establishments successfully matched</td>
	        <td>""" + '%.1f' % stats['FHRS_matched_pc'] + """%</td>
	    </tr>
	    <tr>
	        <td>Percentage of relevant OSM nodes/ways with <span style='color: green'>FHRS match</span>
            or <span style='color: yellow; background-color: gray'>postcode</span></td>
	        <td>""" + '%.1f' % stats['OSM_matched_or_postcode_pc'] + """%</td>
	    </tr>
	</table>

    <h3>Overview</h3>
	<div id="overview_map" style="width: 800px; height: 600px"></div>

	<h3>Suggested matches</h3>
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
        html += ('<p>Below is a list of OSM entities which have an fhrs:id tag for which there is no matching ' +
                 'FHRS establishment. This may indicate an establishment which has closed, but please check ' +
                 'before making any changes to the OSM data.</p>' +
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

	<p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm">""" +
	"""python-fhrs-osm</a> on """ +
	datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """</p>

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

print "Creating index HTML file"

html = ("""
<!DOCTYPE html>
<html>
<head>
    <title>FHRS/OSM comparison</title>
    <meta charset="utf-8" />

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <link rel="stylesheet" href="http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.css" />
</head>

<body>

    <h1>FHRS/OSM comparison</h1>

    <h2>Districts</h2>
    <ul>
    """)

for dist in districts:
    html += ('<li><a href="district-' + str(dist['id']) + '.html">' + dist['name'] + '</a></li>')

html += ("""
    </ul>

<p>Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> data
&copy Crown copyright and database right</p>

</body>
</html>
""")

f = open('html/index.html', 'w')
f.write(html)
f.close
