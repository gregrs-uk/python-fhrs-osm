import overpy
import psycopg2
from psycopg2.extras import DictCursor
from collections import OrderedDict
import urllib2
import xml.etree.ElementTree
from xml.sax.saxutils import escape
from shapely.geometry import Polygon
from shapely.geometry import MultiPoint
from time import sleep


class Database(object):
    """A class which represents our PostgreSQL comparison database, which
    will consist of an OSM table, an FHRS table and a comparison view.

    connection (object): database connection, created with connect()
    """

    connection = None
    osm_url_prefix = 'http://www.openstreetmap.org/'
    fhrs_est_url_prefix = 'http://ratings.food.gov.uk/business/en-GB/'
    fhrs_est_url_suffix = '/'
    josm_url_prefix = 'http://localhost:8111/'

    def __init__(self, dbname='fhrs'):
        """Constructor

        dbname (string): name of PostgreSQL database
        """

        self.dbname = dbname

    def connect(self):
        """Create a database connection"""
        self.connection = psycopg2.connect(database=self.dbname)
        return self.connection

    def add_fhrs_districts(self, fhrs_table='fhrs_establishments',
                           districts_table='districts', district_id_col='gid'):
        """(Re-)add district_id columns to FHRS establishments table and fill
        with the ID of the district in which the FHRS establishment is located.
        """

        cur = self.connection.cursor()

        # (re-)add column to FHRS establishments table
        try:
            cur.execute('ALTER TABLE ' + fhrs_table + '\n' +
                        'DROP COLUMN IF EXISTS district_id CASCADE\n')
            cur.execute('ALTER TABLE ' + fhrs_table + '\n' +
                        'ADD COLUMN district_id SMALLINT\n'
                        'REFERENCES ' + districts_table + '(' + district_id_col + ')')
        except psycopg2.ProgrammingError:
            self.connection.rollback()
            print "Could not drop or add district_id column to table " + fhrs_table + "."
            print ("Does the " + districts_table + " table exist and contain the " +
                   district_id_col + " column?")
            return False
        # N.B. not committed yet in case next stage fails

        # get matching district ID for each establishment
        sql = ('SELECT "FHRSID", ' + district_id_col + ' as dist_id ' +
               'FROM ' + fhrs_table + ' fhrs\n' +
               'LEFT JOIN ' + districts_table + ' dist\n'
               'ON ST_Contains(dist.geom, fhrs.geog::geometry)\n' +
               'WHERE fhrs.geog IS NOT NULL')
        cur.execute(sql)

        # update each FHRS establishment with its district ID
        for est in cur.fetchall():
            fhrsid, dist_id = est
            sql = ('UPDATE ' + fhrs_table + ' SET district_id = %s\n'
                   'WHERE "FHRSID" = %s')
            values = (dist_id, fhrsid)
            try:
                cur.execute(sql, values)
            except psycopg2.ProgrammingError:
                self.connection.rollback()
                print "Couldn't update district_id column in " + fhrs_table + " table."
                print "SQL statement and values for last attempted execute:"
                print sql, values
                return False

        # create index to speed up comparison with OSM district_ids
        cur.execute('CREATE INDEX ON ' + fhrs_table + ' (district_id);')

        self.connection.commit()
        return True

    def add_osm_districts(self, osm_table='osm', districts_table='districts',
                          district_id_col='gid'):
        """(Re-)add district_id columns to OSM table and fill with the ID of
        the district in which the OSM entity is located.
        """

        cur = self.connection.cursor()

        # (re-)add column to OSM table
        try:
            cur.execute('ALTER TABLE ' + osm_table + '\n' +
                        'DROP COLUMN IF EXISTS district_id CASCADE\n')
            cur.execute('ALTER TABLE ' + osm_table + '\n' +
                        'ADD COLUMN district_id SMALLINT\n'
                        'REFERENCES ' + districts_table + '(' + district_id_col + ')')
        except psycopg2.ProgrammingError:
            self.connection.rollback()
            print "Could not drop or add district_id column to table " + osm_table + "."
            print ("Does the " + districts_table + " table exist and contain the " +
                   district_id_col + " column?")
            return False
        # N.B. not committed yet in case next stage fails

        # get matching district ID for each establishment
        sql = ('SELECT id, type, ' + district_id_col + ' as dist_id ' +
               'FROM ' + osm_table + ' AS osm\n' +
               'LEFT JOIN ' + districts_table + ' AS dist\n'
               'ON ST_Contains(dist.geom, osm.geog::geometry)\n' +
               'WHERE osm.geog IS NOT NULL')
        cur.execute(sql)

        # update each OSM entity with its district ID
        for est in cur.fetchall():
            osm_id, osm_type, dist_id = est
            sql = ('UPDATE ' + osm_table + ' SET district_id = %s\n'
                   'WHERE id = %s AND type = %s')
            values = (dist_id, osm_id, osm_type)
            try:
                cur.execute(sql, values)
            except psycopg2.ProgrammingError:
                self.connection.rollback()
                print "Couldn't update district_id column in " + osm_table + " table."
                print "SQL statement and values for last attempted execute:"
                print sql, values
                return False

        # create index to speed up comparison with FHRS district_ids
        cur.execute('CREATE INDEX ON ' + osm_table + ' (district_id);')

        self.connection.commit()
        return True

    def get_inhabited_districts(self, fhrs_table='fhrs_establishments',
                                districts_table='districts', threshold=10):
        """Return a list of dicts of Boundary Line districts for which the
        database contains greater than a threshold number of FHRS
        establishments.

        fhrs_table (string): name of FHRS establishments database table
        districts_table (string): name of districts database table
        threshold (integer): minimum number of establishments for district to
            be included
        Returns list of dicts e.g. {'id': 1, 'name': 'District'}
        """

        cur = self.connection.cursor()

        sql = ('SELECT district_id,\n' +
               # clean up the name of the district
               'regexp_replace(name, \'^County of |^City of |^The City of | City$|' +
                   '^City and County of the | District| \(B\)$| London Boro$\',' +
                   '\'\', \'g\') AS new_name\n' +
               'FROM (\n' +
               '    SELECT district_id, count(district_id) AS num\n'
               '    FROM ' + fhrs_table + '\n' +
               '    GROUP BY district_id\n' +
               ') AS f\n' +
               'LEFT JOIN ' + districts_table + ' as d ON f.district_id = d.gid\n' +
               'WHERE num >= %s\n' +
               'ORDER BY new_name')
        values = (threshold,)
        cur.execute(sql, values)

        districts = []
        for dist in cur.fetchall():
            districts.append({'id': dist[0], 'name': dist[1]})
        return districts

    def create_comparison_view(self, view_name='compare', osm_table='osm',
                               fhrs_table='fhrs_establishments'):
        """(Re)create database view to compare OSM and FHRS data. Drop any
        dependent views first.

        view_name (string): name for the view we're creating e.g. 'compare'
        osm_table (string): name of OSM database table
        fhrs_table (string): name of FHRS establishments database table
        """

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        sql = ('CREATE VIEW ' + view_name + ' AS\n' +
               'SELECT o."name" as osm_name, f."BusinessName" as fhrs_name,\n' +
               'CASE\n' +
               '    WHEN o."id" IS NULL AND f."FHRSID" IS NOT NULL THEN \'FHRS\'\n' +
               '    WHEN o."id" IS NOT NULL AND f."FHRSID" IS NULL THEN\n' +
               '    CASE\n' +
               '        WHEN o."fhrs:id" IS NOT NULL THEN \'mismatch\'\n' +
               '        WHEN o."addr:postcode" IS NOT NULL THEN \'OSM_with_postcode\'\n' +
               '        ELSE \'OSM_no_postcode\'\n' +
               '    END\n' +
               '    WHEN o."fhrs:id" IS NOT NULL AND f."FHRSID" IS NOT NULL THEN\n' +
               '    CASE\n' +
               '        WHEN (o."addr:postcode" != f."PostCode" AND\n' +
               '                (o."not:addr:postcode" != f."PostCode"\n' +
               '                OR "not:addr:postcode" IS NULL))\n' +
               '            OR o."addr:postcode" IS NULL\n' +
               '            THEN \'matched_postcode_error\'\n' +
               '        ELSE \'matched\'\n' +
               '    END\n' +
               'END AS status,\n' +
               'f."PostCode" AS fhrs_postcode, o."addr:postcode" AS osm_postcode,\n' +
               'o."not:addr:postcode" AS osm_not_postcode,\n' +
               'o."geog" AS osm_geog, f."geog" AS fhrs_geog,\n' +
               'o.id AS osm_id, o.type AS osm_type,\n' +
               'f."FHRSID" AS fhrs_fhrsid, o."fhrs:id" AS osm_fhrsid,\n' +
               'o.district_id AS osm_district_id, f.district_id AS fhrs_district_id\n' +
               'FROM ' + fhrs_table + ' AS f\n' +
               'FULL OUTER JOIN ' + osm_table + ' AS o ON f."FHRSID"::text = o."fhrs:id"\n' +
               'WHERE COALESCE(o.geog, f.geog) IS NOT NULL')
        cur.execute(sql)
        self.connection.commit()

    def create_suggest_matches_view(self, view_name='suggest_matches',
                                    osm_table='osm', fhrs_table='fhrs_establishments',
                                    distance_metres=250, levenshtein_distance=3):
        """(Re)create database view to suggest possible matches between OSM and
        FHRS entities, examining names for exact substring match or Levenshtein
        distance-based fuzzy match as well as physical distance apart. Drop any
        dependent views first.

        view_name (string): name for the view we're creating e.g. 'compare'
        osm_table (string): name of OSM database table
        fhrs_table (string): name of FHRS establishments database table
        distance_metres (numeric): max distance apart for points to be matched
        levenshtein_distance (integer): max Levenshtein distance for names to be matched
        """

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        sql = ('CREATE VIEW ' + view_name + ' AS\n' +
               'SELECT o.name AS osm_name, f."BusinessName" AS fhrs_name,\n' +
               'o.id AS osm_id, o.type AS osm_type, f."FHRSID",\n' +
               'f."AddressLine1", f."AddressLine2", \n' +
               'f."AddressLine3", f."AddressLine4", \n' +
               'f."PostCode", o."addr:postcode", \n' +
               'o.geog AS osm_geog, f.geog AS fhrs_geog,\n' +
               'o.district_id AS osm_district_id, f.district_id AS fhrs_district_id\n' +
               'FROM ' + osm_table + ' AS o\n' +
               'INNER JOIN ' + fhrs_table + ' AS f\n' +
               'ON o.district_id = f.district_id\n' +
               # escape % with another %
               'AND (f."BusinessName" LIKE \'%%\' || o.name || \'%%\'\n' +
               '     OR o.name LIKE \'%%\' || f."BusinessName" || \'%%\'\n' +
               '     OR levenshtein_less_equal(o.name, f."BusinessName", %s) < %s)\n' +
               'AND ST_DWithin(o.geog, f.geog, %s, false)\n' + # false = don't use spheroid
               'WHERE o."fhrs:id" IS NULL\n' +
               # check that FHRS ID not already used by another OSM entity
               # only check this district to speed up query
               'AND NOT EXISTS\n' +
               '    (SELECT "fhrs:id" FROM osm\n' +
               '     WHERE district_id = o.district_id\n' +
               '     AND "fhrs:id" = CAST(f."FHRSID" AS TEXT))\n' +
               'ORDER BY o.name')
        values = (levenshtein_distance, levenshtein_distance, distance_metres)

        cur.execute(sql, values)
        self.connection.commit()

    def create_distant_matches_view(self, view_name='distant_matches',
                                    osm_table='osm', fhrs_table='fhrs_establishments',
                                    distance_metres=500):
        """(Re)create database view to compare the OSM and FHRS locations for
        matched establishments. Filters out matches using distance_metres to
        show only distant matches. Drop any dependent views first.

        view_name (string): name for the view we're creating e.g. 'match_lines'
        osm_table (string): name of OSM database table
        fhrs_table (string): name of FHRS establishments database table
        distance_metres (numeric): minimum distance between OSM/FHRS locations
        """

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        sql = ('CREATE VIEW ' + view_name + ' AS\n' +
               'SELECT o.id AS osm_id, TRIM(TRAILING \' \' FROM o.type) AS osm_type,\n' +
               'f."FHRSID" AS fhrs_id, o.name AS osm_name, f."BusinessName" AS fhrs_name,\n' +
               'o.district_id, ST_MakeLine(o.geog::geometry, f.geog::geometry) AS geom,\n' +
               'ST_Distance(o.geog, f.geog) AS distance\n' +
               'FROM ' + osm_table + ' o\n' +
               'FULL OUTER JOIN ' + fhrs_table + ' f ON o."fhrs:id"::text = f."FHRSID"::text\n' +
               'WHERE o.geog IS NOT NULL AND f.geog IS NOT NULL\n' +
               # first false = don't use spheroid for a faster calculation
               'AND ST_DWithin(o.geog, f.geog, ' + str(distance_metres) + ', FALSE) IS FALSE;')

        cur.execute(sql)
        self.connection.commit()

    def get_overview_geojson(self, view_name='compare', fhrs_table='fhrs_establishments',
                             district_id=182, cluster_metres=3.5):
        """Create GeoJSON-formatted string for a single district using
        comparison view. This can be used to display data on a Leaflet slippy
        map. Establishments within cluster_metres of each other are
        aggregated into a list. (This distance variable is approximate as it
        has to be converted into degrees of lat/lon.)

        view_name (string): name of view from which to gather data
        fhrs_table (string): name of FHRS establishments database table
        district_id (integer): gid of district to use for filtering
        cluster_metres (numeric): cluster distance in metres (approx.)
        Returns string
        """

        cur = self.connection.cursor()

        # need to cast JSON as text to prevent result being interpreted into
        # Python structures (psycopg2 issue #172)
        sql = ("SELECT CAST(row_to_json(the_feature_collection) AS TEXT)\n" +
               "FROM (\n" +
               "    SELECT 'FeatureCollection' AS type,\n" +
               "    array_to_json(array_agg(the_features)) AS features\n" +
               "    FROM (\n" +
               "        SELECT 'Feature' AS type,\n" +
               "        ST_AsGeoJSON(\n" +
               "            ST_Centroid(ST_Collect(pref_geog::geometry))\n" +
               "        )::json AS geometry,\n" +
               "        row_to_json((\n" +
               "            SELECT properties_row FROM (\n" +
               "                SELECT string_agg(\n" +
                                    # when FHRS establishment not in OSM
               "                    CASE WHEN fhrs_fhrsid IS NOT NULL AND osm_fhrsid IS NULL THEN\n" +
               "                        CONCAT(pref_name,\n" +
               "                               ' (<a href=\"" + self.fhrs_est_url_prefix + "',\n" +
               "                               fhrs_fhrsid, '" + self.fhrs_est_url_suffix + "\"" +
                                              "target=\"_blank\">', status, '</a>)')\n" +
                                    # when FHRS establishment matched in OSM but addr:postcode missing
               "                    WHEN status = 'matched_postcode_error' AND osm_postcode IS NULL THEN\n" +
               "                        CONCAT(pref_name,\n" +
               "                               ' (<a href=\"" + self.osm_url_prefix + "',\n" +
               "                               TRIM(TRAILING ' ' FROM osm_type),\n" +
               "                               '/', osm_id, '\" target=\"_blank\">',\n" +
               "                               status, '</a>)<br />',\n" +
               "                               '<a href=\"" + self.josm_url_prefix +
                                              "load_object?objects=',\n" +
               "                               substring(osm_type from 1 for 1), osm_id,\n" +
               "                               '&addtags=',\n" +
               "                               CASE WHEN \"AddressLine1\" IS NOT NULL THEN\n" +
               "                                   CONCAT('%7Cfixme:addr1=', \"AddressLine1\") END,\n" +
               "                               CASE WHEN \"AddressLine2\" IS NOT NULL THEN\n" +
               "                                   CONCAT('%7Cfixme:addr2=', \"AddressLine2\") END,\n" +
               "                               CASE WHEN \"AddressLine3\" IS NOT NULL THEN\n" +
               "                                   CONCAT('%7Cfixme:addr3=', \"AddressLine3\") END,\n" +
               "                               CASE WHEN \"AddressLine4\" IS NOT NULL THEN\n" +
               "                                   CONCAT('%7Cfixme:addr4=', \"AddressLine4\") END,\n" +
               "                               CASE WHEN \"PostCode\" IS NOT NULL THEN\n" +
               "                                   CONCAT('%7Caddr:postcode=', \"PostCode\") END,\n" +
               "                               '%7Csource:addr=FHRS Open Data',\n" +
               "                               '\" target=\"_blank\">Add tags in JOSM</a>')\n" +
                                    # when in OSM and possibly FHRS too
               "                    ELSE\n" +
               "                        CONCAT(pref_name,\n" +
               "                               ' (<a href=\"" + self.osm_url_prefix + "',\n" +
               "                               TRIM(TRAILING ' ' FROM osm_type),\n" +
               "                               '/', osm_id, '\" target=\"_blank\">',\n" +
               "                               status, '</a>)<br />',\n" +
               "                               '<a href=\"" + self.josm_url_prefix +
                                              "load_object?objects=',\n" +
               "                               substring(osm_type from 1 for 1), osm_id,\n" +
               "                               '\" target=\"_blank\">Edit in JOSM</a>')\n" +
               "                    END, '<br />'\n" +
               "                ) AS list,\n" +
               "                COUNT(CASE WHEN status = 'matched' THEN 1 END) AS matched,\n" +
               "                COUNT(CASE WHEN status = 'matched_postcode_error' THEN 1 END)\n" +
               "                    AS matched_postcode_error,\n" +
               "                COUNT(CASE WHEN status = 'mismatch' THEN 1 END) AS mismatch,\n" +
               "                COUNT(CASE WHEN status = 'FHRS' THEN 1 END) AS fhrs,\n" +
               "                COUNT(CASE WHEN status = 'OSM_with_postcode' THEN 1 END)\n" +
               "                    AS osm_with_postcode,\n" +
               "                COUNT(CASE WHEN status = 'OSM_no_postcode' THEN 1 END)\n" +
               "                    AS osm_no_postcode\n" +
               "            ) AS properties_row\n" +
               "        )) AS properties\n" +
               "        FROM (\n" +
               "            SELECT *, ST_ClusterDBSCAN(COALESCE(osm_geog, fhrs_geog)::geometry,\n" +
               "               " + str(cluster_metres) + "/111111, 1) OVER () AS cl_id,\n" +
               "            COALESCE(osm_geog, fhrs_geog) as pref_geog,\n" +
               "            COALESCE(osm_name, fhrs_name) as pref_name\n" +
               "            FROM " + view_name + "\n" +
               "            LEFT JOIN " + fhrs_table + " ON fhrs_fhrsid = \"FHRSID\"\n" +
               "            WHERE coalesce(osm_district_id, fhrs_district_id) = " + str(district_id) + "\n" +
               "        ) AS all_points\n" +
               "        GROUP BY cl_id\n" +
               "    ) AS the_features\n" +
               ") AS the_feature_collection;")

        cur.execute(sql)
        return cur.fetchone()[0]

    def get_suggest_matches_geojson(self, view_name='suggest_matches', district_id=182):
        """Create GeoJSON-formatted string for a single district using the
        suggest matches view. This can be used to display data on a Leaflet
        slippy map.

        view_name (string): name of view from which to gather data
        district_id (integer): gid of district to use for filtering
        Returns string
        """

        cur = self.connection.cursor()

        # need to cast JSON as text to prevent result being interpreted into
        # Python structures (psycopg2 issue #172)
        sql = ("SELECT CAST(row_to_json(fc) AS TEXT)\n" +
               "FROM (\n" +
               "   SELECT 'FeatureCollection' AS type, array_to_json(array_agg(f)) AS features\n" +
               "   FROM (\n" +
               "       SELECT 'Feature' AS type,\n" +
               "       ST_AsGeoJSON(osm_geog)::json AS geometry,\n" +
               "       row_to_json((\n" +
               "           SELECT l FROM (\n" +
               "               SELECT CONCAT('OSM: <a href=\"" + self.osm_url_prefix + "',\n" +
               "                   TRIM(TRAILING ' ' FROM osm_type),\n" +
               "                   '/', osm_id, '\" target=\"_blank\">', osm_name, '</a>'\n" +
               "                   '<br />FHRS: <a href=\"" + self.fhrs_est_url_prefix + "',\n" +
               "                   \"FHRSID\", '" + self.fhrs_est_url_suffix + "\"\n" +
               "                   target=\"_blank\">', fhrs_name,\n" +
               "                   '</a><br /><a href=\"" + self.josm_url_prefix + "',"
               "                   'load_object?objects=', substring(osm_type from 1 for 1),\n" +
               "                   osm_id, '&addtags=fhrs:id=', \"FHRSID\",\n" +
               "                   CASE WHEN \"AddressLine1\" IS NOT NULL THEN\n" +
               "                       CONCAT('%7Cfixme:addr1=', \"AddressLine1\") END,\n" +
               "                   CASE WHEN \"AddressLine2\" IS NOT NULL THEN\n" +
               "                       CONCAT('%7Cfixme:addr2=', \"AddressLine2\") END,\n" +
               "                   CASE WHEN \"AddressLine3\" IS NOT NULL THEN\n" +
               "                       CONCAT('%7Cfixme:addr3=', \"AddressLine3\") END,\n" +
               "                   CASE WHEN \"AddressLine4\" IS NOT NULL THEN\n" +
               "                       CONCAT('%7Cfixme:addr4=', \"AddressLine4\") END,\n" +
               "                   CASE WHEN \"PostCode\" IS NOT NULL THEN\n" +
               "                       CONCAT('%7Caddr:postcode=', \"PostCode\") END,\n" +
               "                   '%7Csource:addr=FHRS Open Data',\n" +
               "                   '\" target=\"_blank\">Add tags in JOSM</a>') AS text,\n" +
               "               \"addr:postcode\" as osm_postcode \n" +
               "           ) AS l\n" +
               "       )) AS properties\n" +
               "       FROM " + view_name + " AS lg\n" +
               "       WHERE osm_district_id = " + str(district_id) + "\n" +
               "   ) AS f\n" +
               ") AS fc;")

        cur.execute(sql)
        return cur.fetchone()[0]

    def get_distant_matches_geojson(self, view_name='distant_matches', district_id=182):
        """Create GeoJSON-formatted string for a single district using distant
        matches view. This can be used to display data on a Leaflet slippy map.

        view_name (string): name of view from which to gather data
        district_id (integer): gid of district to use for filtering
        Returns string
        """

        cur = self.connection.cursor()

        # need to cast JSON as text to prevent result being interpreted into
        # Python structures (psycopg2 issue #172)
        sql = ("SELECT CAST(row_to_json(fc) AS TEXT)\n" +
               "FROM (\n" +
               "   SELECT 'FeatureCollection' AS type, array_to_json(array_agg(f)) AS features\n" +
               "   FROM (\n" +
               "       SELECT 'Feature' AS type,\n" +
               "       ST_AsGeoJSON(geom)::json AS geometry\n" +
               "       FROM " + view_name + " AS lg\n" +
               "       WHERE district_id = %s\n" +
               "   ) AS f\n" +
               ") AS fc;")
        values = (district_id,)

        cur.execute(sql, values)
        return cur.fetchone()[0]

    def get_district_boundary_geojson(self, districts_table='districts', district_id=182):
        """Create GeoJSON-formatted string for a single district's boundary.
        This can be used to display data on a Leaflet slippy map.

        districts_table (string): name of districts database table
        district_id (integer): gid of district
        Returns string
        """

        cur = self.connection.cursor()

        # need to cast JSON as text to prevent result being interpreted into
        # Python structures (psycopg2 issue #172)
        sql = ("SELECT CAST(row_to_json(fc) AS TEXT)\n" +
               "FROM (\n" +
               "   SELECT 'FeatureCollection' AS type, array_to_json(array_agg(f)) AS features\n" +
               "   FROM (\n" +
               "       SELECT 'Feature' AS type,\n" +
               "       ST_AsGeoJSON(ST_Boundary(poly_geom))::json AS geometry FROM (\n" +
               "           SELECT gid, geom AS poly_geom\n" +
               "           FROM " + districts_table + " AS lg\n" +
               "       ) AS polygons\n" +
               "       WHERE gid = %s\n" +
               "   ) AS f\n" +
               ") AS fc;")
        values = (district_id,)

        cur.execute(sql, values)
        return cur.fetchone()[0]

    def get_district_stats(self, district_id=182):
        """Get statistics regarding the matching of FHRS establishments and
        OSM entities for the specified district.

        district_id (integer): Boundary Line district ID
        Returns dict
        """

        cur = self.connection.cursor()

        sql = ('SELECT status, COUNT(status) FROM compare\n' +
               'WHERE COALESCE(osm_district_id, fhrs_district_id) = %s\n' +
               'GROUP BY status')
        values = (district_id,)
        cur.execute(sql, values)

        # default values
        s = {'OSM_with_postcode': 0, # OSM without valid fhrs:id but with postcode
             'OSM_no_postcode': 0, # OSM without valid fhrs:id or postcode
             'FHRS': 0, # FHRS establishment without matching OSM node/way
             'matched': 0, # OSM with fhrs:id that matches an FHRS establishment
             'matched_postcode_error': 0, # OSM with fhrs:id that matches an FHRS establishment
                                         # but has no postcode or a mismatching one
             'mismatch': 0} # OSM with fhrs:id that doesn't match an FHRS establishment

        # set values in dict
        for row in cur.fetchall():
            s[row[0]] = row[1]

        s['total_OSM'] = (s['OSM_with_postcode'] + s['OSM_no_postcode'] +
                          s['matched'] + s['matched_postcode_error'] + s['mismatch'])
        s['OSM_matched_or_postcode'] = s['matched'] + s['OSM_with_postcode']
        s['total_FHRS'] = s['FHRS'] + s['matched'] + s['matched_postcode_error']

        # avoid dividing by zero
        if s['total_FHRS'] != 0:
            # cast to float to prevent result of division being rounded to integer
            s['FHRS_matched_pc'] = float(s['matched']) / s['total_FHRS'] * 100
        else:
            s['FHRS_matched_pc'] = float(0)

        # avoid dividing by zero
        if s['total_OSM'] != 0:
            # cast to float to prevent result of division being rounded to integer
            s['OSM_matched_or_postcode_pc'] = float(s['OSM_matched_or_postcode']) / s['total_OSM'] * 100
        else:
            s['OSM_matched_or_postcode_pc'] = float(0)

        return s

    def get_district_postcode_errors(self, comparison_view='compare',
                                     fhrs_table='fhrs_establishments', district_id=182):
        """Get OSM entities which have an fhrs:id that matches an FHRS
        establishment but has no postcode or a mismatching one.

        comparison_view (string): name of comparison database view
        fhrs_table (string): name of FHRS establishments database table
        district_id (integer): Boundary Line district ID
        Returns dict
        """

        dict_cur = self.connection.cursor(cursor_factory=DictCursor)

        sql = ('SELECT osm_name, osm_id, osm_fhrsid, osm_postcode, fhrs_postcode,\n' +
               'TRIM(TRAILING \' \' FROM osm_type) AS osm_type,\n' +
               'CONCAT(substring(osm_type FROM 1 FOR 1), osm_id) AS osm_ident,\n' +
               'CONCAT(\n' +
               'CASE WHEN "AddressLine1" IS NOT NULL THEN\n' +
               '    CONCAT(\'%7Cfixme:addr1=\', "AddressLine1") END,\n' +
               'CASE WHEN "AddressLine2" IS NOT NULL THEN\n' +
               '    CONCAT(\'%7Cfixme:addr2=\', "AddressLine2") END,\n' +
               'CASE WHEN "AddressLine3" IS NOT NULL THEN\n' +
               '    CONCAT(\'%7Cfixme:addr3=\', "AddressLine3") END,\n' +
               'CASE WHEN "AddressLine4" IS NOT NULL THEN\n' +
               '    CONCAT(\'%7Cfixme:addr4=\', "AddressLine4") END,\n' +
               'CASE WHEN "PostCode" IS NOT NULL THEN\n' +
               '    CONCAT(\'%7Caddr:postcode=\', "PostCode") END,\n' +
               '\'%7Csource:addr=FHRS Open Data\') AS add_tags_string\n' +
               'FROM compare\n' +
               'LEFT JOIN ' + fhrs_table + ' ON fhrs_fhrsid = "FHRSID"\n' +
               'WHERE status = \'matched_postcode_error\' AND '
               'osm_district_id = ' + str(district_id))
        dict_cur.execute(sql)

        result = []
        for row in dict_cur.fetchall():
            result.append(row)

        return result

    def get_district_mismatches(self, comparison_view='compare', district_id=182):
        """Get OSM entities which have an fhrs:id for which there is no match
        in the database.

        district_id (integer): Boundary Line district ID
        Returns dict
        """

        dict_cur = self.connection.cursor(cursor_factory=DictCursor)

        sql = ('SELECT osm_name, osm_fhrsid, TRIM(TRAILING ' ' FROM osm_type) as osm_type,\n' +
               'osm_id, CONCAT(substring(osm_type FROM 1 FOR 1), osm_id) AS osm_ident\n' +
               'FROM compare\n' +
               'WHERE status = \'mismatch\' AND osm_district_id = %s')
        values = (district_id,)
        dict_cur.execute(sql, values)

        result = []
        for row in dict_cur.fetchall():
            result.append(row)

        return result

    def get_district_duplicates(self, osm_table='osm', fhrs_table='fhrs_establishments',
                                district_id=182):
        """Get OSM entities which have an fhrs:id shared by at least one OSM
        entity within the specified district.

        osm_table (string): name of OSM database table
        fhrs_table (string): name of FHRS establishments database table
        district_id (integer): Boundary Line district ID
        Returns dict
        """

        dict_cur = self.connection.cursor(cursor_factory=DictCursor)

        sql = ('SELECT id, TRIM(TRAILING ' ' FROM type) as type,\n' +
               'CONCAT(substring(type FROM 1 FOR 1), id) AS osm_ident, "fhrs:id",\n' +
               osm_table + '.district_id, name AS osm_name, "BusinessName" AS fhrs_name\n' +
               'FROM ' + osm_table + '\n' +
               'LEFT JOIN ' + fhrs_table + ' ON "fhrs:id" = CAST("FHRSID" AS TEXT)\n' +
               'WHERE "fhrs:id" IN (\n' +
               '    SELECT "fhrs:id" FROM osm\n' +
               '    WHERE district_id = %s\n' +
               '    GROUP BY "fhrs:id" HAVING COUNT("fhrs:id") > 1)\n' +
               'ORDER BY "fhrs:id";')
        values = (district_id,)
        dict_cur.execute(sql, values)

        result = []
        for row in dict_cur.fetchall():
            result.append(row)

        return result

    def get_district_distant_matches(self, distant_matches_view='distant_matches',
                                     district_id=182):
        """Get OSM entities that are matched to an FHRS establishment where
        the OSM/FHRS locations are distant.

        distant_matches_view (string): name of distant matches database view
        district_id (integer): Boundary Line district ID
        Returns dict
        """

        dict_cur = self.connection.cursor(cursor_factory=DictCursor)

        sql = ('SELECT osm_id, osm_type,\n' +
               'CONCAT(SUBSTRING(osm_type FROM 1 FOR 1), osm_id) AS osm_ident, fhrs_id,\n' +
               'osm_name, fhrs_name, distance\n' +
               'FROM ' + distant_matches_view + '\n' +
               'WHERE district_id = %s' +
               'ORDER BY distance;')
        values = (district_id,)
        dict_cur.execute(sql, values)

        result = []
        for row in dict_cur.fetchall():
            result.append(row)

        return result

    def get_gpx(self, geog_col='fhrs_geog', name_col='fhrs_name',
                view_name='compare', district_id_col='fhrs_district_id',
                district_id=182, status=None):
        """Return a GPX representation of waypoints from the database using
        the specified parameters.

        geog_col (string): name of column containing waypoint geography
        name_col (string): name of column containing waypoint name
        view_name (string): name of view which contains the data
        district_id_col (string): name of column containing Boundary Line
            district id
        district_id (integer): Boundary Line district ID
        status (string): status of waypoints to be selected e.g. 'matched'
        Returns string
        """

        # use supplied variables to get waypoints from database
        dict_cur = self.connection.cursor(cursor_factory=DictCursor)

        sql = ("SELECT ST_Y(" + geog_col + "::geometry) as lat, " +
               "ST_X(" + geog_col + "::geometry) as lon,\n" +
               name_col + " as name\n" +
               "FROM " + view_name + "\n" +
               "WHERE " + district_id_col + "=%s")
        if status:
            sql += " AND status=%s"
            values = (district_id, status)
        else:
            values = (district_id,)
        dict_cur.execute(sql, values)

        waypoints = [] # empty list to hold waypoint dicts
        for row in dict_cur.fetchall():
            if row['name']:
                waypoints.append({'lat': str(row['lat']), 'lon': str(row['lon']),
                                  'name': escape(row['name'])})
            else:
                waypoints.append({'lat': str(row['lat']), 'lon': str(row['lon']),
                                  'name': '???'})

        # create GPX file
        output = ('<?xml version="1.0" encoding="UTF-8"?>\n' +
            '<gpx version="1.0" creator="python-fhrs-osm"\n' +
            '    xmlns="http://www.topografix.com/GPX/1/0">\n')
        for waypoint in waypoints:
            output += ('<wpt lat="' + waypoint['lat'] + '" lon="' + waypoint['lon'] + '">\n' +
                '    <name>' + waypoint['name'] + '</name>\n' +
                '</wpt>\n')
        output += '</gpx>'
        return output


class OSMDataset(object):
    """A class which represents the OSM data we are using."""

    def __init__(self, tag_value_list=[{'t': 'amenity', 'v': 'bar'},
                                       {'t': 'amenity', 'v': 'cafe'},
                                       {'t': 'amenity', 'v': 'care_home'},
                                       {'t': 'amenity', 'v': 'childcare'},
                                       {'t': 'amenity', 'v': 'church_hall'},
                                       {'t': 'amenity', 'v': 'cinema'},
                                       {'t': 'amenity', 'v': 'college'},
                                       {'t': 'amenity', 'v': 'community_centre'},
                                       {'t': 'amenity', 'v': 'community_hall'},
                                       {'t': 'amenity', 'v': 'fast_food'},
                                       {'t': 'amenity', 'v': 'fuel'},
                                       {'t': 'amenity', 'v': 'hospital'},
                                       {'t': 'amenity', 'v': 'ice_cream'},
                                       {'t': 'amenity', 'v': 'kindergarten'},
                                       {'t': 'amenity', 'v': 'nightclub'},
                                       {'t': 'amenity', 'v': 'nursing_home'},
                                       {'t': 'amenity', 'v': 'pharmacy'},
                                       {'t': 'amenity', 'v': 'place_of_worship'},
                                       {'t': 'amenity', 'v': 'post_office'},
                                       {'t': 'amenity', 'v': 'pub'},
                                       {'t': 'amenity', 'v': 'restaurant'},
                                       {'t': 'amenity', 'v': 'school'},
                                       {'t': 'amenity', 'v': 'social_club'},
                                       {'t': 'amenity', 'v': 'social_facility'},
                                       {'t': 'amenity', 'v': 'theatre'},
                                       {'t': 'amenity', 'v': 'village_hall'},
                                       {'t': 'club', 'v': 'scouts'},
                                       {'t': 'club', 'v': 'social'},
                                       {'t': 'club', 'v': 'sport'},
                                       {'t': 'craft', 'v': 'brewery'},
                                       {'t': 'craft', 'v': 'caterer'},
                                       {'t': 'craft', 'v': 'confectionery'},
                                       {'t': 'craft', 'v': 'distillery'},
                                       {'t': 'craft', 'v': 'winery'},
                                       {'t': 'shop', 'v': 'alcohol'},
                                       {'t': 'shop', 'v': 'bakery'},
                                       {'t': 'shop', 'v': 'butcher'},
                                       {'t': 'shop', 'v': 'cheese'},
                                       {'t': 'shop', 'v': 'chemist'},
                                       {'t': 'shop', 'v': 'confectionery'},
                                       {'t': 'shop', 'v': 'convenience'},
                                       {'t': 'shop', 'v': 'deli'},
                                       {'t': 'shop', 'v': 'delicatessen'},
                                       {'t': 'shop', 'v': 'discount'},
                                       {'t': 'shop', 'v': 'farm'},
                                       {'t': 'shop', 'v': 'fishmonger'},
                                       {'t': 'shop', 'v': 'greengrocer'},
                                       {'t': 'shop', 'v': 'grocery'},
                                       {'t': 'shop', 'v': 'health_food'},
                                       {'t': 'shop', 'v': 'newsagent'},
				       {'t': 'shop', 'v': 'pastry'},
				       {'t': 'shop', 'v': 'seafood'},
                                       {'t': 'shop', 'v': 'supermarket'},
                                       {'t': 'shop', 'v': 'variety_store'},
                                       {'t': 'tourism', 'v': 'hotel'},
                                       {'t': 'tourism', 'v': 'guest_house'}],
                 tag_exists_list=['fhrs:id'],
                 field_list=[{'name': 'fhrs:id', 'format': 'VARCHAR(50)'},
                             {'name': 'name', 'format': 'VARCHAR(100)'},
                             {'name': 'addr:postcode', 'format': 'VARCHAR(50)'},
                             {'name': 'not:addr:postcode', 'format': 'VARCHAR(50)'}],
                 table_name='osm'):
        """Constructor

        tag_value_list (list of dicts): tag/value pairs to use in Overpass query
        tag_exists_list (list of strings): tags to use in Overpass query
        field_list (list of dicts): field/format dicts representing DB fields
        table_name (string): database table name to use for storing OSM entities
        """
        self.tag_value_list = tag_value_list
        self.tag_exists_list = tag_exists_list
        self.field_list = field_list
        self.table_name = table_name

    def create_table(self, connection):
        """(Re)create the OSM database table, first dropping any existing table
        with the same name and any views dependent on it.

        connection (object): database connection object
        """

        cur = connection.cursor()
        cur.execute('DROP VIEW IF EXISTS compare CASCADE')
        connection.commit()
        cur.execute('DROP TABLE IF EXISTS ' + self.table_name + ' CASCADE')
        connection.commit()

        sql = 'CREATE TABLE ' + self.table_name + '\n'
        # N.B. field names case sensitive because surrounded by ""
        sql += '(id BIGINT, geog GEOGRAPHY(POINT, 4326), type CHAR(8),\n'
        for this_field in self.field_list:
            sql += '"' + this_field['name'] + '" ' + this_field['format'] + ','
        sql += '\nPRIMARY KEY (id, type))'
        cur.execute(sql)
        connection.commit()

    def run_overpass_query(self, bbox=[52.314,-1.356,52.412,-1.178], timeout=180):
        """Run Overpass API query based on bounding box and tag list supplied.

        bbox (list of 4 decimals): bounding box co-ordinates [S,W,N,E]
        Returns overpy.Result object
        """
        # header elements
        query = '[out:xml][timeout:' + str(timeout) + ']'
        query += '[bbox:'
        query += ','.join(map(str, bbox)) # comma separated list of bbox co-ordinates
        query += '];\n'

        # tag/value list
        query += '(\n'
        for this in self.tag_value_list:
            query += '\tnwr["' + this['t'] + '"="' + this['v'] + '"];\n'

        # tag exists list
        for this in self.tag_exists_list:
            query += '\tnwr["' + this + '"];\n'

        query += ');\n'

        # closing elements
        query += ('(._;>;);\n' + # include nodes used in ways
                  'out;')

        # run the query
        api = overpy.Overpass()
        return api.query(query)

    def parse_xml_file(self, filename):
        """Parse XML file

        Returns overpy.Result object
        """
        api = overpy.Overpass()
        f = open(filename)
        xml = f.read()
        f.close()

        return api.parse_xml(xml)

    def write_entity(self, entity, lat, lon, connection):
        """Write a single OSM node or way to the database

        entity (object): object representing the node or way
        lat/lon (decimals): latitude and longitude of point
        connection (object): database connection
        """

        # create list of fields still to match for this OSM entity
        fields_to_check = []
        for this_field in self.field_list:
            fields_to_check.append(this_field['name'])

        # create a blank dict to store relevant data for this OSM node/way/relation
        # need to keep it in order so we can write it to the database
        record = OrderedDict()

        record['id'] = entity.id
        record['geog'] = ("ST_GeogFromText('SRID=4326;POINT(" +
                          str(lon) + " " + str(lat) + ")')")
        record['type'] = None
        if (type(entity) == overpy.Node):
            record['type'] = 'node'
        elif (type(entity) == overpy.Way):
            record['type'] = 'way'
        elif (type(entity) == overpy.Relation):
            record['type'] = 'relation'

        # start with this record's tags set to None
        for this_field in fields_to_check:
            record[this_field] = None

        # iterate through this entity's OSM tags
        for entity_key, entity_value in entity.tags.iteritems():
            # if the OSM tag is in list of fields to check, store its value in dict
            if entity_key in fields_to_check:
                record[entity_key] = entity_value
                # if we found a matching tag, we don't need to check for it again
                fields_to_check.remove(entity_key)

        # create an SQL statement and matching tuple of values to insert
        values_list = []
        sql = "INSERT INTO " + self.table_name + " VALUES ("
        for key in record.keys():
            if key == 'geog':
                sql += record['geog']
            else:
                values_list.append(record[key])
                sql += "%s"
            # if not last key/value pair in record, add a comma
            if (key != record.keys()[-1]):
                sql += ","
        values = tuple(values_list)
        sql += ")"

        cur = connection.cursor()

        try:
            cur.execute(sql, values)
        except (psycopg2.DataError, psycopg2.IntegrityError) as e:
            connection.rollback()
            print "\nCouldn't insert the following OSM data:"
            print record
            print "The reason given was:"
            print repr(e)
            print "Continuing..."
        else:
            connection.commit()

    def write_result_nodes_and_ways(self, result, connection, filter_ways=True):
        """Filter the OSM nodes and ways from the query result and write
        matching entities to the database

        result (object): result object from query
        connection (object): database connection
        filter_ways (boolean): do we need to filter ways based on tag/value list?
        """

        # nodes could be relevant or just contain geometry info for a way
        # so in any case we need to filter them based on our tag_value_list
        for node in result.get_nodes():
            # iterate through this node's tags/values
            for tag, value in node.tags.iteritems():
                # if this tag/value or tag match our criteria
                if {'t': tag, 'v': value} in self.tag_value_list or tag in self.tag_exists_list:
                    # write to DB and stop checking this node's tags/values
                    self.write_entity(entity=node, lat=node.lat, lon=node.lon, connection=connection)
                    break

        for way in result.get_ways():
            # if filter_ways is True:
            # iterate through this way's tags/values
            for tag, value in way.tags.iteritems():
                # if this tag/value or tag match our criteria
                if {'t': tag, 'v': value} in self.tag_value_list or tag in self.tag_exists_list:
                    # write to DB and stop checking this way's tags/values
                    centroid = self.get_way_centroid(way)
                    self.write_entity(entity=way, lat=centroid['lat'],
                                      lon=centroid['lon'], connection=connection)
                    break
            # else:
            #     centroid = self.get_way_centroid(way)
            #     self.write_entity(entity=way, lat=centroid['lat'],
            #                       lon=centroid['lon'], connection=connection)

        for relation in result.get_relations():
            if filter_ways is True:
                for tag, value in relation.tags.iteritems():
                    # if this tag/value or tag match our criteria
                    if {'t': tag, 'v': value} in self.tag_value_list or tag in self.tag_exists_list:
                        # write to DB and stop checking this relation's tags/values
                        centroid = self.get_relation_centroid(relation)
                        self.write_entity(entity=relation, lat=centroid['lat'],
                                      lon=centroid['lon'], connection=connection)
                        break
            else:
                centroid = self.get_relation_centroid(relation)
                self.write_entity(entity=relation, lat=centroid['lat'],
                                  lon=centroid['lon'], connection=connection)

        cur = connection.cursor()
        cur.execute('CREATE INDEX ON ' + self.table_name + ' USING GIST (geog);')
        connection.commit()

    def get_way_centroid(self, way):
        """Calculate the centroid of a way

        way (object): overpy.Way object
        Returns dict of lat/lon
        """
        # Polygon has to have at least 3 points
        if len(way.nodes) >= 3:
            geom = []
            for node in way.nodes:
                geom.append((node.lon, node.lat))
            poly = Polygon(geom)
            cent = poly.centroid
            return {'lat': cent.y, 'lon': cent.x}
        elif len(way.nodes) == 2:
            # if way has 2 nodes, use average position
            lat = (way.nodes[0].lat + way.nodes[1].lat) / 2
            lon = (way.nodes[0].lon + way.nodes[1].lon) / 2
            return {'lat': lat, 'lon': lon}
        elif len(way.nodes) == 1:
            # if way has 1 node, use that position
            # (unusual and certainly a bug but possible)
            return {'lat': way.nodes[0].lat, 'lon': way.nodes[0].lon}
        else:
            raise RuntimeError

    def get_relation_centroid(self, relation):
        """Calculate a representative centre-point for a relation

        relation (object): overpy.Relation object
        Returns dict of lat/lon
        """
        geom = []
        for member in relation.members:
            if isinstance(member, overpy.RelationWay):
                way = member.resolve()
                for node in way.nodes:
                    geom.append((node.lon, node.lat))
            elif isinstance(member, overpy.RelationNode):
                node = member.resolve()
                geom.append((node.lon, node.lat))

        if len(geom) > 0:
            mp = MultiPoint(geom)
            bbox = mp.bounds
            return {'lat': 0.5*(bbox[1]+bbox[3]), 'lon': 0.5*(bbox[0]+bbox[2])}
        else:
            return {'lat': 0, 'lon': 0}


class FHRSDataset(object):
    """A class which represents the FHRS data we are using.

    api_base_url (string): base url for FHRS API
    api_headers (list of tuples): headers to add to HTTP request
    xmlns (string): namespace which prefixes tags when parsed with ElementTree
    xmlns_meta (string): namespace which prefixes meta tags
    """

    api_base_url = 'http://api.ratings.food.gov.uk/'
    api_headers = [('x-api-version', 2),
                   ('accept', 'application/xml'),
                   ('content-type', 'application/xml'),
                   ('user-agent', 'python-fhrs-osm')]
    xmlns = '{http://schemas.datacontract.org/2004/07/FHRS.Model.Detailed}'
    xmlns_meta = '{http://schemas.datacontract.org/2004/07/FHRS.Model.MetaLinks}'

    def __init__(self,
                 est_field_list=[{'name': 'BusinessName', 'format': 'VARCHAR(100)'},
                                 {'name': 'AddressLine1', 'format': 'VARCHAR(200)'},
                                 {'name': 'AddressLine2', 'format': 'VARCHAR(100)'},
                                 {'name': 'AddressLine3', 'format': 'VARCHAR(100)'},
                                 {'name': 'AddressLine4', 'format': 'VARCHAR(100)'},
                                 {'name': 'PostCode', 'format': 'CHAR(10)'}],
                 auth_field_list=[{'name': 'Name', 'format': 'VARCHAR(100)'},
                                  {'name': 'RegionName', 'format': 'VARCHAR(100)'}],
                 est_table_name='fhrs_establishments', auth_table_name='fhrs_authorities'):
        """Constructor

        est_field_list (list of dicts): field/format dicts for establishment DB fields
        auth_field_list (list of dicts): field/format dicts for authority DB fields
        est_table_name (string): database table name to use for storing establishments
        auth_table_name (string): database table name to use for storing authorities
        """
        # list of field/format dicts representing database fields
        self.est_field_list = est_field_list
        self.auth_field_list = auth_field_list
        # database table name to use for storing FHRS establishments
        self.est_table_name = est_table_name
        self.auth_table_name = auth_table_name

    def api_download(self, endpoint, max_attempts = 7, first_sleep_time = 3):
        """
        Use the FHRS API to download XML data. If first attempt fails, wait
        and try again. The sleep time progressively increases using the
        formula first_sleep_time ** attempt.

        endpoint (string): endpoint part of URL
        max_attempts (integer): max number of attempts
        first_sleep_time (integer): sleep time (secs) after 1st bad attempt

        Returns XML string
        """
        url = self.api_base_url + endpoint
        request = urllib2.Request(url)
        for header, content in self.api_headers:
            request.add_header(header, content)

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                response = urllib2.urlopen(request)
                break # exit while loop if successful
            except:
                print "Error when trying to get data from FHRS API"
                print "URL: " + url
                print "Headers: " + repr(request.header_items())
                if attempt == max_attempts: # final attempt
                    print "Exception from final attempt:"
                    raise
                else:
                    # wait before trying again
                    sleep_time = first_sleep_time ** attempt
                    print "Sleeping {} secs before next attempt".format(
                        sleep_time
                    )
                    sleep(sleep_time)

        return response.read()

    def download_authorities(self):
        """Calls api_download to download authorities

        Returns XML string
        """
        return self.api_download('Authorities')

    def download_establishments_for_authority(self, authority_id=371):
        """Calls api_download to download establishments for a single authority

        authority_id (integer): ID of authority
        Returns XML string
        """

        page = 1
        total_pages = 1 # assume 1 page for now
        xml_list = [] # list to hold xml strings

        # if this is the first page or there is another to download
        while (page == 1 or page <= total_pages):
            # download this page (max 200 establishments) and add to list
            endpoint = ('Establishments?localAuthorityId=' + str(authority_id) +
                        '&pageNumber=' + str(page) + '&pageSize=200') 
            xml_list.append(self.api_download(endpoint=endpoint))
            if (page == 1):
                # after the first page has been downloaded, get total number of pages
                root = xml.etree.ElementTree.fromstring(xml_list[page - 1])
                total_pages = int(root.findtext(self.xmlns_meta + 'meta/' +
                                                self.xmlns_meta + 'totalPages'))
            page += 1

        return xml_list

    def create_authority_table(self, connection):
        """(Re)create the FHRS authority table, first dropping any existing
        table with the same name and any views dependent on it.

        connection (object): database connection object
        """

        cur = connection.cursor()
        cur.execute('drop table if exists ' + self.auth_table_name + ' cascade')
        connection.commit()

        # N.B. field names case sensitive because surrounded by ""
        sql = ('CREATE TABLE ' + self.auth_table_name + '\n' +
               '("LocalAuthorityId" SMALLINT PRIMARY KEY, "LocalAuthorityIdCode" SMALLINT UNIQUE,\n')
        for this_field in self.auth_field_list:
            sql += '"' + this_field['name'] + '" ' + this_field['format']
            if this_field != self.auth_field_list[-1]: # i.e. not the last field in the list
                sql += ', '
        sql += ')'
        cur.execute(sql)
        connection.commit()

    def create_establishment_table(self, connection):
        """(Re)create the FHRS establishment table, first dropping any existing
        table with the same name and any views dependent on it.

        connection (object): database connection object
        """

        cur = connection.cursor()
        cur.execute('drop table if exists ' + self.est_table_name + ' cascade')
        connection.commit()

        # N.B. field names case sensitive because surrounded by ""
        sql = ('CREATE TABLE ' + self.est_table_name + '\n'
               '("FHRSID" INT PRIMARY KEY, geog GEOGRAPHY(POINT, 4326),\n' +
               '"LocalAuthorityCode" SMALLINT REFERENCES ' +
               self.auth_table_name + '("LocalAuthorityIdCode")\n')
        for this_field in self.est_field_list:
            sql += ', "' + this_field['name'] + '" ' + this_field['format']
        sql += ')'

        cur.execute(sql)
        connection.commit()

    def write_authorities(self, xml_string, connection):
        """Write the FHRS authorities from the XML string to the database

        xml_string (string): XML containing authority info
        connection (object): database connection
        """

        root = xml.etree.ElementTree.fromstring(xml_string)

        for auth in root.iter(self.xmlns + 'authority'):
            # create a blank dict to store relevant data for this establishment
            # need to keep it in order so we can write it to the database
            record = OrderedDict()

            # put LocalAuthorityId and LocalAuthorityIdCode into record dict
            record['LocalAuthorityId'] = auth.find(self.xmlns + 'LocalAuthorityId').text
            record['LocalAuthorityIdCode'] = auth.find(self.xmlns + 'LocalAuthorityIdCode').text

            # start with this record's other fields set to None
            for this_field in self.auth_field_list:
                record[this_field['name']] = None

            # fill record dict from XML using field list
            for this_field in self.auth_field_list:
                if auth.find(self.xmlns + this_field['name']).text is not None:
                    record[this_field['name']] = auth.find(self.xmlns + this_field['name']).text

            # create an SQL statement and matching tuple of values to insert
            values_list = []
            sql = "INSERT INTO " + self.auth_table_name + " VALUES ("
            for key in record.keys():
                values_list.append(record[key])
                sql += "%s"
                # if not last key/value pair in record, add a comma
                if (key != record.keys()[-1]):
                    sql += ","
            values = tuple(values_list)
            sql += ")"

            cur = connection.cursor()

            try:
                cur.execute(sql, values)
            except (psycopg2.DataError, psycopg2.IntegrityError) as e:
                connection.rollback()
                print "\nCouldn't insert the following FHRS authority data:"
                print record
                print "The reason given was:"
                print repr(e)
                print "Continuing..."
            else:
                connection.commit()

    def write_establishments(self, xml_list, connection):
        """Write the FHRS establishments from a list of XML strings to the database

        xml_list (list of strings): list of XML strings containing
            establishment info
        connection (object): database connection
        """

        for xml_string in xml_list: # i.e. for each page of results for this authority

            root = xml.etree.ElementTree.fromstring(xml_string)

            for est in root.iter(self.xmlns + 'establishment'):
                # create a blank dict to store relevant data for this establishment
                # need to keep it in order so we can write it to the database
                record = OrderedDict()

                # put FHRSID, position and LocalAuthorityCode into record dict
                record['FHRSID'] = est.find(self.xmlns + 'FHRSID').text
                record['geog'] = None
                geocode = est.find(self.xmlns + 'geocode')
                lon = geocode.find(self.xmlns + 'longitude').text
                lat = geocode.find(self.xmlns + 'latitude').text
                if lon is not None and lat is not None:
                    record['geog'] = ("ST_GeogFromText('SRID=4326;POINT(" +
                                      str(lon) + " " + str(lat) + ")')")
                record['LocalAuthorityCode'] = est.find(self.xmlns + 'LocalAuthorityCode').text

                # start with this record's other fields set to None
                for this_field in self.est_field_list:
                    record[this_field['name']] = None

                # fill record dict from XML using field list
                for this_field in self.est_field_list:
                    if est.find(self.xmlns + this_field['name']).text is not None:
                        record[this_field['name']] = est.find(self.xmlns + this_field['name']).text

                # create an SQL statement and matching tuple of values to insert
                values_list = []
                sql = "INSERT INTO " + self.est_table_name + " VALUES ("
                for key in record.keys():
                    if key == 'geog' and record['geog'] is not None:
                        sql += record['geog']
                    else:
                        values_list.append(record[key])
                        sql += "%s"
                    # if not last key/value pair in record, add a comma
                    if (key != record.keys()[-1]):
                        sql += ","
                values = tuple(values_list)
                sql += ")"

                cur = connection.cursor()

                try:
                    cur.execute(sql, values)
                except (psycopg2.DataError, psycopg2.IntegrityError) as e:
                    connection.rollback()
                    print "\nCouldn't insert the following FHRS establishment data:"
                    print record
                    print "The reason given was:"
                    print repr(e)
                    print "Continuing..."
                else:
                    connection.commit()

    def create_fhrs_indexes(self, connection):
        """Create database indexes for FHRS establishments table

        connection (object): database connection
        """
        cur = connection.cursor()
        cur.execute('CREATE INDEX ON ' + self.est_table_name + ' (CAST ("FHRSID" AS TEXT));')
        cur.execute('CREATE INDEX ON ' + self.est_table_name + ' USING GIST (geog);')
        connection.commit()

    def get_authorities(self, connection, region_name=None):
        """Return a list of FHRS authority IDs (without those for Northern
        Ireland because OS Boundary Line does not cover Northern Ireland)

        connection (object): database connection
        region_name (string): if supplied, only return the IDs of local
            authorities within this region
        Returns local authority IDs as a list of integers
        """

        cur = connection.cursor()

        sql = ('SELECT "LocalAuthorityId" FROM ' + self.auth_table_name + '\n' +
               'WHERE "RegionName" != \'Northern Ireland\'\n')
        if region_name is not None:
            sql += 'AND "RegionName" = \'' + region_name + '\''
        cur.execute(sql)
        authority_ids = []
        for auth in cur.fetchall():
            authority_ids.append(auth[0])
        return authority_ids

    def get_bbox(self, connection, region_name=None, authority_id=None):
        """Return a bounding box for FHRS establishments. If region_name is
        specified, filter establishments based on this. If authority_id is
        specified, filter establishments based on this. The presence of an
        authority_id disables filtering by region name.

        Returns list of 4 decimals: bounding box co-ordinates [S,W,N,E]
        """

        cur = connection.cursor()

        sql = 'SELECT ST_Extent(geog::geometry) FROM ' + self.est_table_name + ' est\n'
        if authority_id is not None or region_name is not None:
            sql += ('LEFT JOIN fhrs_authorities auth\n' +
                    'ON est."LocalAuthorityCode" = auth."LocalAuthorityIdCode"\n')
        if authority_id is not None:
            sql += 'WHERE "LocalAuthorityId" = ' + str(authority_id)
        elif region_name is not None:
            sql += 'WHERE "RegionName" = \'' + region_name + '\''

        cur.execute(sql)
        result = cur.fetchone()[0][4:-1] # remove BOX( and trailing )

        # split string into four co-ordinates
        w_s, e_n = result.split(',')
        w, s = w_s.split(' ')
        e, n = e_n.split(' ')

        # return list of co-ordinates in correct order
        return [s, w, n, e]

    def get_stats(self, connection, column, table, fence_multiplier=3):
        """Get statistical minimum, maximum, Q1, Q3, interquartile distance
        and inner/outer fence (based on multiplier provided) for a set of
        values from a column within a database table.

        column (string): name of database column
        table (string): name of database table
        fence_multiplier (numeric): value to use in calculating fence, usually
            3 for outer fence and 1.5 for inner fence
        Returns dict of values
        """

        cur = connection.cursor()
        values = OrderedDict()

        sql = ('SELECT MIN(' + column + ') AS min\n' +
	           'FROM ' + table + '\n' +
	           'WHERE ' + column + ' IS NOT NULL')
        cur.execute(sql)
        values['min'] = cur.fetchone()[0]

        sql = ('SELECT MAX(num) AS q1 FROM (\n' +
	           '    SELECT ' + column + ' AS num\n' +
	           '    FROM ' + table + '\n' +
	           '    WHERE ' + column + ' IS NOT NULL\n' +
	           '    ORDER BY num asc\n' +
	           '    LIMIT (\n' +
	           '        SELECT count(' + column + ')/4\n' +
	           '        FROM ' + table + '\n' +
	           '        WHERE ' + column + ' IS NOT NULL\n' +
	           '    )\n' +
               ') AS num')
        cur.execute(sql)
        values['Q1'] = cur.fetchone()[0]

        sql = ('SELECT MAX(num) AS med FROM (\n' +
	           '    SELECT ' + column + ' as num\n' +
	           '    FROM ' + table + '\n' +
	           '    WHERE ' + column + ' IS NOT NULL\n' +
	           '    ORDER BY num asc\n' +
	           '    LIMIT (\n' +
	           '        SELECT count(' + column + ')/2\n' +
	           '        FROM ' + table + '\n' +
	           '        WHERE ' + column + ' IS NOT NULL\n' +
	           '    )\n' +
               ') AS num')
        cur.execute(sql)
        values['med'] = cur.fetchone()[0]

        sql = ('SELECT MIN(num) AS q3 FROM (\n' +
	           '    SELECT ' + column + ' as num\n' +
	           '    FROM ' + table + '\n' +
	           '    WHERE ' + column + ' IS NOT NULL\n' +
	           '    ORDER BY num desc\n' +
	           '    LIMIT (\n' +
	           '        SELECT count(' + column + ')/4\n' +
	           '        FROM ' + table + '\n' +
	           '        WHERE ' + column + ' IS NOT NULL\n' +
	           '    )\n' +
               ') AS num')
        cur.execute(sql)
        values['Q3'] = cur.fetchone()[0]

        sql = ('SELECT max(' + column + ') as max\n' +
	           'FROM ' + table + '\n' +
	           'WHERE ' + column + ' IS NOT NULL')
        cur.execute(sql)
        values['max'] = cur.fetchone()[0]

        values['iq_range'] = values['Q3'] - values['Q1']
        values['fence_low'] = values['Q1'] - (values['iq_range'] * fence_multiplier)
        values['fence_high'] = values['Q3'] + (values['iq_range'] * fence_multiplier)

        return values

    def get_corrected_bbox(self, connection, fence_multiplier=3):
        """Return a bounding box for FHRS establishments, ignoring outliers.

        Returns list of 4 decimals: bounding box co-ordinates [S,W,N,E]
        """

        lon = self.get_stats(connection=connection, column='ST_X(geog::geometry)',
                             table=self.est_table_name,
                             fence_multiplier=fence_multiplier)
        lat = self.get_stats(connection=connection, column='ST_Y(geog::geometry)',
                             table=self.est_table_name,
                             fence_multiplier=fence_multiplier)

        cur = connection.cursor()

        sql = ('SELECT min(ST_Y(geog::geometry)) as min_lat\n' +
               'FROM ' + self.est_table_name + '\n' +
               'WHERE geog IS NOT NULL\n' +
               'AND ST_Y(geog::geometry) > %s')
        values = (lat['fence_low'],)
        cur.execute(sql, values)
        s = cur.fetchone()[0]

        sql = ('SELECT min(ST_X(geog::geometry)) as min_lon\n' +
               'FROM ' + self.est_table_name + '\n' +
               'WHERE geog IS NOT NULL\n' +
               'AND ST_X(geog::geometry) > %s')
        values = (lon['fence_low'],)
        cur.execute(sql, values)
        w = cur.fetchone()[0]

        sql = ('SELECT max(ST_Y(geog::geometry)) as max_lat\n' +
               'FROM ' + self.est_table_name + '\n' +
               'WHERE geog IS NOT NULL\n' +
               'AND ST_Y(geog::geometry) < %s')
        values = (lat['fence_high'],)
        cur.execute(sql, values)
        n = cur.fetchone()[0]

        sql = ('SELECT max(ST_X(geog::geometry)) as max_lon\n' +
               'FROM ' + self.est_table_name + '\n' +
               'WHERE geog IS NOT NULL\n' +
               'AND ST_X(geog::geometry) < %s')
        values = (lon['fence_high'],)
        cur.execute(sql, values)
        e = cur.fetchone()[0]

        return [s,w,n,e]
