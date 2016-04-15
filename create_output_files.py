from fhrs_osm import *
from datetime import datetime

db = Database()
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

    stats = db.get_district_stats(dist['id'])

    html = ("""
<!DOCTYPE html>
<html>
<head>
	<title>FHRS/OSM comparison for """ + dist['name'] + """</title>
	<meta charset="utf-8" />

	<meta name="viewport" content="width=device-width, initial-scale=1.0">

	<link rel="stylesheet" href="http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.css" />

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

	<p>Generated using <a href="https://github.com/gregrs-uk/python-fhrs-osm">""" +
	"""python-fhrs-osm</a> on """ +
	datetime.strftime(datetime.now(), '%a %d %b %Y at %H:%M') + """</p>

	<script src="http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.js"></script>
	<script src="http://code.jquery.com/jquery-2.1.0.min.js"></script>

	<script>

        // create maps

		var overview_map = L.map('overview_map').setView([52.372, -1.263], 16);
        var suggest_matches_map = L.map('suggest_matches_map').setView([52.372, -1.263], 16);


        // add OSM tile layer to each map

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 18,
			attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
				'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
				'<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
				'data &copy Crown copyright and database right'
		}).addTo(overview_map);

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
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
