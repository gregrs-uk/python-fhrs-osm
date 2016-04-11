import overpy_mod as overpy
import psycopg2
from collections import OrderedDict
import urllib2
import xml.etree.ElementTree


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
        query = ('SELECT "FHRSID", ' + district_id_col + ' as dist_id ' +
                 'FROM ' + fhrs_table + ' fhrs\n' +
                 'LEFT JOIN ' + districts_table + ' dist\n'
                 'ON ST_Contains(dist.geom, fhrs.geog::geometry)\n' +
                 'WHERE fhrs.geog IS NOT NULL')
        cur.execute(query)

        # update each FHRS establishment with its district ID
        for est in cur.fetchall():
            fhrsid, dist_id = est
            statement = ('UPDATE ' + fhrs_table + ' SET district_id = %s\n'
                         'WHERE "FHRSID" = %s')
            values = (dist_id, fhrsid)
            try:
                cur.execute(statement, values)
            except psycopg2.ProgrammingError:
                self.connection.rollback()
                print "Couldn't update district_id column in " + fhrs_table + " table."
                print "SQL statement and values for last attempted execute:"
                print statement, values
                return False
        
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
        query = ('SELECT id, type, ' + district_id_col + ' as dist_id ' +
                 'FROM ' + osm_table + ' osm\n' +
                 'LEFT JOIN ' + districts_table + ' dist\n'
                 'ON ST_Contains(dist.geom, osm.geog::geometry)\n' +
                 'WHERE osm.geog IS NOT NULL')
        cur.execute(query)

        # update each OSM entity with its district ID
        for est in cur.fetchall():
            osm_id, osm_type, dist_id = est
            statement = ('UPDATE ' + osm_table + ' SET district_id = %s\n'
                         'WHERE id = %s AND type = %s')
            values = (dist_id, osm_id, osm_type)
            try:
                cur.execute(statement, values)
            except psycopg2.ProgrammingError:
                self.connection.rollback()
                print "Couldn't update district_id column in " + osm_table + " table."
                print "SQL statement and values for last attempted execute:"
                print statement, values
                return False
        
        self.connection.commit()
        return True

    def create_comparison_view(self, view_name='compare', osm_table='osm',
                               fhrs_table='fhrs_establishments'):
        """(Re)create database view to compare OSM and FHRS data. Drop any
        dependent views first.

        view_name (string): name for the view we're creating e.g. 'compare'
        osm_table (string): name of OSM database table
        fhrs_table (string): name of FHRS establishments database table
        """

        # shorten names for convenience
        o = osm_table
        f = fhrs_table

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        statement = ('create view ' + view_name + ' as\n' +
            'select ' + o + '."name" as osm_name, ' + f + '."BusinessName" as fhrs_name,\n' +
            'case when ' + o + '."fhrs:id" is not null and ' + f + '."FHRSID" is not null then \'matched\'\n'
            'when ' + o + '."fhrs:id" is not null and ' + f + '."FHRSID" is null then \'mismatch\'\n'
            'when ' + o + '."id" is null and ' + f + '."FHRSID" is not null then \'FHRS\'\n'
            'when ' + o + '."id" is not null and ' + f + '."FHRSID" is null then \'OSM\'\n'
            'end as status,\n' +
            f + '."PostCode" as fhrs_postcode, ' + o + '."addr:postcode" as osm_postcode,\n' +
            o + '."geog" as osm_geog, ' + f + '."geog" as fhrs_geog,\n' +
            f + '."FHRSID",\n' +
            o + '.district_id as osm_district_id, ' + f + '.district_id as fhrs_district_id\n' +
            'from ' + f + '\n' +
            'full outer join ' + o + ' on ' + f + '."FHRSID" = ' + o + '."fhrs:id"\n' +
            'where coalesce(' + o + '.geog, ' + f + '.geog) is not null')
        cur.execute(statement)
        self.connection.commit()

    def create_postcode_mismatch_view(self, view_name='postcode_mismatch',
                                      comparison_view='compare'):
        """(Re)create database view to show postcode mismatches between FHRS
        establishments and OSM entities with an fhrs:id tag. Drop any dependent
        views first.

        view_name (string): name for the view we're creating e.g. 'compare'
        comparison_view (string): name of the comparison view created using
            create_comparison_view()
        """

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        statement = ('create view ' + view_name + ' as ' +
            'SELECT osm_name, osm_postcode, fhrs_postcode\n'
            'FROM ' + comparison_view + '\n'
            'WHERE status = \'matched\' AND osm_postcode != fhrs_postcode\n'
            'ORDER BY osm_postcode')

        cur.execute(statement)
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

        # shorten names for convenience
        o = osm_table
        f = fhrs_table
        lev_dist = str(levenshtein_distance)

        cur = self.connection.cursor()
        cur.execute('drop view if exists ' + view_name + ' cascade')
        self.connection.commit()

        statement = ('create view ' + view_name + ' as ' +
            'SELECT ' + o + '.name AS osm_name, ' + f + '."BusinessName" AS fhrs_name,\n' +
            o + ".id as osm_id, " + o + ".type as osm_type, " + f + '."FHRSID",\n' +
            f + '."AddressLine1", ' + f + '."AddressLine2", \n' +
            f + '."AddressLine3", ' + f + '."AddressLine4", ' + f + '."PostCode", \n' +
            'ST_Distance(' + o + '.geog, ' + f + '.geog) AS distance_metres,\n' +
            o + '.geog AS osm_geog, ' + f + '.geog AS fhrs_geog,\n' +
            o + '.district_id AS osm_district_id, ' + f + '.district_id AS fhrs_district_id\n' +
            'FROM ' + o + '\n' +
            'INNER JOIN ' + fhrs_table + '\n' +
            'ON (' + f + '."BusinessName" LIKE \'%\' || ' + o + '.name || \'%\'\n' +
            '    OR levenshtein_less_equal(' + o + '.name, ' + f + '."BusinessName", ' +
                                           lev_dist + ') < ' + lev_dist + ')\n' +
            'AND ST_Distance(' + o + '.geog, ' + f + '.geog) < 250\n' +
            'WHERE ' + o + '."fhrs:id" IS NULL\n' +
            'ORDER BY ' + o + '.name')

        cur.execute(statement)
        self.connection.commit()

    def get_overview_geojson(self, view_name='compare', district_id=182):
        """Create GeoJSON-formatted string for a single district using
        comparison view. This can be used to display data on a Leaflet slippy
        map. Establishments with the same lat/lon are aggregated into a list.

        view_name (string): name of view from which to gather data
        district_id (integer): gid of district to use for filtering
        Returns string
        """

        cur = self.connection.cursor()

        # need to cast JSON as text to prevent result being interpreted into
        # Python structures (psycopg2 issue #172)
        query = ("SELECT CAST(row_to_json(fc) AS TEXT)\n" +
        "FROM (\n" +
        "   SELECT 'FeatureCollection' as type, array_to_json(array_agg(f)) as features\n" +
        "   FROM (\n" +
        "       SELECT 'Feature' as type,\n" +
        "       ST_AsGeoJSON(coalesce(osm_geog, fhrs_geog))::json as geometry,\n" +
        "       row_to_json((\n" +
        "           SELECT l FROM (\n" +
        "               SELECT string_agg(\n" +
        "                   case when \"FHRSID\" is not null then\n" +
        "                       concat('<a href=\"" + self.fhrs_est_url_prefix + "',\n" +
        "                           \"FHRSID\", '" + self.fhrs_est_url_suffix + "\">',\n" +
        "                           coalesce(osm_name, fhrs_name),\n" +
        "                           '</a> (', status, ')')\n" +
        "                   when \"FHRSID\" is null then\n" +
        "                       concat(coalesce(osm_name, fhrs_name),\n" +
        "                           ' (', status, ')')\n" +
        "                   end, '<br />'\n" +
        "               ) as list,\n" +
        "               count(case when status = 'matched' then 1 end) as matched,\n" +
        "               count(case when status = 'mismatch' then 1 end) as mismatch,\n" +
        "               count(case when status = 'FHRS' then 1 end) as fhrs,\n" +
        "               count(case when status = 'OSM' then 1 end) as osm\n" +
        "           ) as l\n" +
        "       )) as properties\n" +
        "       FROM " + view_name + " as lg\n" +
        "       WHERE COALESCE(osm_district_id, fhrs_district_id) = " + str(district_id) + "\n" +
        "       GROUP BY coalesce(osm_geog, fhrs_geog)\n" +
        "   ) as f\n" +
        ") as fc;")

        cur.execute(query)
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
        query = ("SELECT CAST(row_to_json(fc) AS TEXT)\n" +
        "FROM (\n" +
        "   SELECT 'FeatureCollection' as type, array_to_json(array_agg(f)) as features\n" +
        "   FROM (\n" +
        "       SELECT 'Feature' as type,\n" +
        "       ST_AsGeoJSON(osm_geog)::json as geometry,\n" +
        "       row_to_json((\n" +
        "           SELECT l FROM (\n" +
        "               SELECT (\n" +
        "                   concat('OSM: <a href=\"" + self.osm_url_prefix + "', osm_type,\n" +
        "                       '/', osm_id, '\">', osm_name, '</a>'\n" +
        "                       '<br />FHRS: <a href=\"" + self.fhrs_est_url_prefix + "',\n" +
        "                       \"FHRSID\", '" + self.fhrs_est_url_suffix + "\">', fhrs_name,\n" +
        "                       '</a><br /><a href=\"" + self.josm_url_prefix + "',"
        "                       'load_object?objects=', substring(osm_type from 1 for 1), osm_id,\n" +
        "                       '&addtags=fhrs:id=', \"FHRSID\",\n" +
        "                       case when \"AddressLine1\" is not null then\n" +
        "                       concat('%7Cfixme:addr1=', \"AddressLine1\") end,\n" +
        "                       case when \"AddressLine2\" is not null then\n" +
        "                       concat('%7Cfixme:addr2=', \"AddressLine2\") end,\n" +
        "                       case when \"AddressLine3\" is not null then\n" +
        "                       concat('%7Cfixme:addr3=', \"AddressLine3\") end,\n" +
        "                       case when \"AddressLine4\" is not null then\n" +
        "                       concat('%7Cfixme:addr3=', \"AddressLine4\") end,\n" +
        "                       case when \"PostCode\" is not null then\n" +
        "                       concat('%7Caddr:postcode=', \"PostCode\") end,\n" +
        "                       '%7Csource:addr=FHRS Open Data',\n" +
        "                       '\">Add tags in JOSM</a>')\n" +
        "               ) as text\n" +
        "           ) as l\n" +
        "       )) as properties\n" +
        "       FROM " + view_name + " as lg\n" +
        "       WHERE osm_district_id = " + str(district_id) + "\n" +
        "   ) as f\n" +
        ") as fc;")

        cur.execute(query)
        return cur.fetchone()[0]


class OSMDataset(object):
    """A class which represents the OSM data we are using."""

    def __init__(self, tag_value_list=[{'t': 'amenity', 'v': 'fast_food'},
                                       {'t': 'amenity', 'v': 'restaurant'},
                                       {'t': 'amenity', 'v': 'cafe'},
                                       {'t': 'amenity', 'v': 'pub'},
                                       {'t': 'amenity', 'v': 'bar'},
                                       {'t': 'amenity', 'v': 'nightclub'},
                                       {'t': 'amenity', 'v': 'hospital'},
                                       {'t': 'amenity', 'v': 'school'},
                                       {'t': 'amenity', 'v': 'college'},
                                       {'t': 'tourism', 'v': 'hotel'},
                                       {'t': 'tourism', 'v': 'guest_house'}],
                 tag_exists_list=['fhrs:id'],
                 field_list=[{'name': 'fhrs:id', 'format': 'INT'},
                             {'name': 'name', 'format': 'VARCHAR(100)'},
                             {'name': 'addr:postcode', 'format': 'CHAR(10)'}],
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
        cur.execute('drop view if exists compare cascade')
        connection.commit()
        cur.execute('drop table if exists ' + self.table_name + ' cascade')
        connection.commit()

        statement = 'create table ' + self.table_name + '\n'
        # N.B. field names case sensitive because surrounded by ""
        statement += '(id BIGINT, geog GEOGRAPHY(POINT, 4326), type CHAR(8),\n'
        for this_field in self.field_list:
            statement += '"' + this_field['name'] + '" ' + this_field['format'] + ','
        statement += '\nPRIMARY KEY (id, type))'
        cur.execute(statement)
        connection.commit()

    def run_overpass_query(self, bbox=[52.314,-1.356,52.412,-1.178]):
        """Run Overpass API query based on bounding box and tag list supplied.

        bbox (list of 4 decimals): bounding box co-ordinates [S,W,N,E]
        Returns overpy.Result object
        """
        # header elements
        query = '[out:xml][timeout:60]'
        query += '[bbox:'
        query += ','.join(map(str, bbox)) # comma separated list of bbox co-ordinates
        query += '];\n'

        # tag/value list
        query += '(\n'
        for this in self.tag_value_list:
            query += '\tnode["' + this['t'] + '"="' + this['v'] + '"];\n'
            query += '\tway["' + this['t'] + '"="' + this['v'] + '"];\n'
            # TODO: not supporting relations until we can parse them properly
            # query += '\trelation["' + this['t'] + '"="' + this['v'] + '"];\n\n'
        # tag exists list
        for this in self.tag_exists_list:
            query += '\tnode["' + this + '"];\n'
            query += '\tway["' + this + '"];\n'
            # TODO: not supporting relations until we can parse them properly
            # query += '\trelation["' + this + '"];\n\n'

        query += ');\n'

        # closing elements
        query += 'out center;\n' # provide centroid for ways and relations

        # run the query
        api = overpy.Overpass()
        return api.query(query)

    def write_entity(self, entity, lat, lon, connection):
        """Write a single OSM node or way to the database

        entity (object): object representing the node or way
        lat/lon (decimals): latitude and longitude of point
        connection (object): database connection
        """

        # create list of fields still to match for this OSM entity
        # we need list() to avoid creating an alias to the original list
        fields_to_check = list(self.field_list)

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

        # start with this record's tags set to None
        for this_field in fields_to_check:
            record[this_field['name']] = None

        # iterate through this entity's OSM tags
        for entity_key, entity_value in entity.tags.iteritems():
            # check list of database fields
            for this_field in fields_to_check:
                # if the OSM tag we're checking matches field name, store value in dict
                if (entity_key == this_field['name']):
                    record[this_field['name']] = entity_value
                    # if we found a matching tag, we don't need to check for it again
                    fields_to_check.remove(this_field)

        # create an SQL statement and matching tuple of values to insert
        values_list = []
        statement = "insert into " + self.table_name + " values ("
        for key in record.keys():
            if key == 'geog':
                statement += record['geog']
            else:
                values_list.append(record[key])
                statement += "%s"
            # if not last key/value pair in record, add a comma
            if (key != record.keys()[-1]):
                statement += ","
        values = tuple(values_list)
        statement += ")"

        cur = connection.cursor()

        try:
            cur.execute(statement, values)
        except psycopg2.DataError:
            connection.rollback()
            print "Couldn't insert the following OSM data:"
            print record
            print "Continuing..."
        else:
            connection.commit()

    def write_result_nodes_and_ways(self, result, connection):
        """Write the OSM nodes and ways from the query result to the database

        result (object): result object from query
        connection (object): database connection
        """

        cur = connection.cursor()
        for node in result.get_nodes():
            self.write_entity(entity=node, lat=node.lat,
                             lon=node.lon, connection=connection)
        for way in result.get_ways():
            self.write_entity(entity=way, lat=way.center_lat,
                             lon=way.center_lon, connection=connection)


class FHRSDataset(object):
    """A class which represents the FHRS data we are using.

    api_base_url (string): base url for FHRS API
    api_headers (list of tuples): headers to add to HTTP request
    xmlns (string): namespace which prefixes tags when parsed with ElementTree
    """

    api_base_url = 'http://api.ratings.food.gov.uk/'
    api_headers = [('x-api-version', 2),
                   ('accept', 'application/xml'),
                   ('content-type', 'application/xml')]
    xmlns = '{http://schemas.datacontract.org/2004/07/FHRS.Model.Detailed}'
    #xmlns_basic = '{http://schemas.datacontract.org/2004/07/FHRS.Model.Basic}'

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

    def api_download(self, endpoint):
        """Use the FHRS API to download XML data

        Returns XML string
        """
        url = self.api_base_url + endpoint
        request = urllib2.Request(url)
        for header, content in self.api_headers:
            request.add_header(header, content)
        response = urllib2.urlopen(request)
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
        endpoint = 'Establishments?localAuthorityId=' + str(authority_id)
        return self.api_download(endpoint=endpoint)

    def create_authority_table(self, connection):
        """(Re)create the FHRS authority table, first dropping any existing
        table with the same name and any views dependent on it.

        connection (object): database connection object
        """

        cur = connection.cursor()
        cur.execute('drop table if exists ' + self.auth_table_name + ' cascade')
        connection.commit()

        # N.B. field names case sensitive because surrounded by ""
        statement = ('create table ' + self.auth_table_name + ' ' +
                     '("LocalAuthorityId" SMALLINT PRIMARY KEY, "LocalAuthorityIdCode" SMALLINT UNIQUE,\n')
        for this_field in self.auth_field_list:
            statement += '"' + this_field['name'] + '" ' + this_field['format']
            if this_field != self.auth_field_list[-1]: # i.e. not the last field in the list
                statement += ', '
        statement += ')'
        cur.execute(statement)
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
        statement = ('create table ' + self.est_table_name + ' '
                     '("FHRSID" INT PRIMARY KEY, geog GEOGRAPHY(POINT, 4326),\n' +
                     '"LocalAuthorityCode" SMALLINT REFERENCES ' +
                     self.auth_table_name + '("LocalAuthorityIdCode")\n')
        for this_field in self.est_field_list:
            statement += ', "' + this_field['name'] + '" ' + this_field['format']
        statement += ')'

        cur.execute(statement)
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
            statement = "insert into " + self.auth_table_name + " values ("
            for key in record.keys():
                values_list.append(record[key])
                statement += "%s"
                # if not last key/value pair in record, add a comma
                if (key != record.keys()[-1]):
                    statement += ","
            values = tuple(values_list)
            statement += ")"

            cur = connection.cursor()

            try:
                cur.execute(statement, values)
            except psycopg2.DataError:
                connection.rollback()
                print "Couldn't insert the following FHRS authority data:"
                print record
                print "Continuing..."
            else:
                connection.commit()

    def write_establishments(self, xml_string, connection):
        """Write the FHRS establishments from the XML string to the database

        xml_string (string): XML containing establishment info
        connection (object): database connection
        """

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
            statement = "insert into " + self.est_table_name + " values ("
            for key in record.keys():
                if key == 'geog' and record['geog'] is not None:
                    statement += record['geog']
                else:
                    values_list.append(record[key])
                    statement += "%s"
                # if not last key/value pair in record, add a comma
                if (key != record.keys()[-1]):
                    statement += ","
            values = tuple(values_list)
            statement += ")"

            cur = connection.cursor()

            try:
                cur.execute(statement, values)
            except psycopg2.DataError:
                connection.rollback()
                print "Couldn't insert the following FHRS establishment data:"
                print record
                print "Continuing..."
            else:
                connection.commit()

    def get_authorities(self, connection, region_name=None):
        """Return a list of FHRS authority IDs

        connection (object): database connection
        region_name (string): if supplied, only return the IDs of local
            authorities within this region
        Returns local authority IDs as a list of integers
        """

        cur = connection.cursor()

        query = 'SELECT "LocalAuthorityId" from ' + self.auth_table_name + '\n'
        if region_name is not None:
            query += 'WHERE "RegionName" = \'' + region_name + '\''
        cur.execute(query)
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

        query = 'SELECT ST_Extent(geog::geometry) FROM ' + self.est_table_name + ' est\n'
        if authority_id is not None or region_name is not None:
            query += ('LEFT JOIN fhrs_authorities auth\n' +
                      'ON est."LocalAuthorityCode" = auth."LocalAuthorityIdCode"\n')
        if authority_id is not None:
            query += 'WHERE "LocalAuthorityId" = ' + str(authority_id)
        elif region_name is not None:
            query += 'WHERE "RegionName" = \'' + region_name + '\''

        cur.execute(query)
        result = cur.fetchone()[0][4:-1] # remove BOX( and trailing )

        # split string into four co-ordinates
        w_s, e_n = result.split(',')
        w, s = w_s.split(' ')
        e, n = e_n.split(' ')

        # return list of co-ordinates in correct order
        return [s, w, n, e]
