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
	        <td style='color: #0f0;'>OSM nodes/ways with valid fhrs:id</td>
	        <td>""" + str(stats['matched']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: #f00;'>OSM nodes/ways with invalid fhrs:id</td>
	        <td>""" + str(stats['mismatch']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: #00f;'>FHRS establishments with no matching OSM node/way</td>
	        <td>""" + str(stats['FHRS']) + """</td>
	    </tr>
	    <tr>
	        <td style='color: #0f0;'>Percentage of FHRS establishments matched</td>
	        <td>""" + '%.1f' % stats['FHRS_matched_pc'] + """%</td>
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

        // defaults for both maps
		var geojsonMarkerOptions = {
            radius: 5,
            color: "#000",
            fillColor: "#ff0",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.5
        }


		var overview_map = L.map('overview_map').setView([52.372, -1.263], 16);

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 18,
			attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
				'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
				'<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
				'data &copy Crown copyright and database right'
		}).addTo(overview_map);

        var overview_json = './json/overview-""" + str(dist['id']) + """.json';

        $.getJSON(overview_json, function(data) {
            var overviewMarkerLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, geojsonMarkerOptions);
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(feature.properties.list);
                },
                style: function(feature) {
                    if (feature.properties.mismatch > 0) {
                        // at least one mismatch
                        return {fillColor: "#f00"};
                    } else if (feature.properties.osm > 0) {
                        // at least one OSM to be matched
                        return {fillColor: "#ff0"};
                    } else if (feature.properties.fhrs > 0) {
                        // at least one FHRS to be matched
                        return {fillColor: "#00f"};
                    } else {
                        // all matched
                        return {fillColor: "#0f0"};
                    }
                }
            }).addTo(overview_map);
            overview_map.fitBounds(overviewMarkerLayer.getBounds());
        });
        
        
        var suggest_matches_map = L.map('suggest_matches_map').setView([52.372, -1.263], 16);

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 18,
			attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
				'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
				'<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
				'data &copy Crown copyright and database right'
		}).addTo(suggest_matches_map);

        var suggest_matches_json = './json/suggest-matches-""" + str(dist['id']) + """.json';

        $.getJSON(suggest_matches_json, function(data) {
            var matchesMarkerLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, geojsonMarkerOptions);
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(feature.properties.text);
                }
            }).addTo(suggest_matches_map);
            suggest_matches_map.fitBounds(matchesMarkerLayer.getBounds());
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
