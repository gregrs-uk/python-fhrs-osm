from fhrs_osm import *

db = Database()
db.connect()

print "Getting list of districts which contain some data"
districts = db.get_inhabited_districts()

print "Creating GeoJSON and HTML files for each district"
for dist in districts:
    filename = 'html/json/overview-' + str(dist['id']) + '.json'
    f = open(filename, 'w')
    f.write(db.get_overview_geojson(district_id=dist['id']))
    f.close

    filename = 'html/json/suggest-matches-' + str(dist['id']) + '.json'
    f = open(filename, 'w')
    f.write(db.get_suggest_matches_geojson(district_id=dist['id']))
    f.close

    html = ("""
<!DOCTYPE html>
<html>
<head>
	<title>FHRS/OSM comparison for """ + dist['name'] + """</title>
	<meta charset="utf-8" />

	<meta name="viewport" content="width=device-width, initial-scale=1.0">

	<link rel="stylesheet" href="http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.css" />
</head>
<body>

    <h1>FHRS/OSM comparison</h1>
    <h2>""" + dist['name'] + """</h2>    

    <h3>Overview</h3>
	<div id="overview_map" style="width: 800px; height: 600px"></div>
	
	<h3>Suggested matches</h3>
	<div id="suggest_matches_map" style="width: 800px; height: 600px"></div>


	<script src="http://cdn.leafletjs.com/leaflet/v0.7.7/leaflet.js"></script>
	<script src="http://code.jquery.com/jquery-2.1.0.min.js"></script>

	<script>

		var overview_map = L.map('overview_map').setView([52.372, -1.263], 16);

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 18,
			attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
				'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
				'<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
				'data &copy Crown copyright and database right'
		}).addTo(overview_map);

        var geojsonMarkerOptions = {
            radius: 5,
            color: "#000",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.5
        }

        var jsonfile = './json/overview-""" + str(dist['id']) + """.json';

        $.getJSON(jsonfile, function(data) {
            var markerLayer = L.geoJson(data, {
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
            overview_map.fitBounds(markerLayer.getBounds());
        });
        
        
        var suggest_matches_map = L.map('suggest_matches_map').setView([52.372, -1.263], 16);

		L.tileLayer('http://a.tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 18,
			attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
				'Contains <a href="http://www.ordnancesurvey.co.uk">Ordnance Survey</a> and ' +
				'<a href="http://ratings.food.gov.uk/open-data/">Food Hygiene Rating Scheme</a> ' +
				'data &copy Crown copyright and database right'
		}).addTo(suggest_matches_map);

        var geojsonMarkerOptions = {
            radius: 5,
            color: "#000",
            fillColor: "#ff0",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.5
        }

        var jsonfile = './json/overview-""" + str(dist['id']) + """.json';

        $.getJSON(jsonfile, function(data) {
            var markerLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    return L.circleMarker(latlng, geojsonMarkerOptions);
                },
                onEachFeature: function (feature, layer) {
                    layer.bindPopup(feature.properties.text);
                }
            }).addTo(suggest_matches_map);
            suggest_matches_map.fitBounds(markerLayer.getBounds());
        });

	</script>
	
</body>
</html>
    """)
    
    filename = 'html/district-' + str(dist['id']) + '.html'
    f = open(filename, 'w')
    f.write(html)
    f.close
