# -*- coding: utf-8 -*-
import os
import sqlite3
from sqlite3 import Error
from contextlib import contextmanager

class EmapsDbModel(object):
    """sqlite3 database class that holds testers jobs"""

    def __init__(self, general_params, db_location=None):
        self.general_params = general_params
        if db_location is not None:
            if os.path.exists(db_location):
                os.remove(db_location)
            self.connection = sqlite3.connect(db_location)
        else:
            self.connection = sqlite3.connect(':memory:')
        #self.cur = self.connection.cursor()
        self.connection.enable_load_extension(True)
        self.connection.execute('SELECT load_extension("mod_spatialite")')
        self.connection.execute('SELECT InitSpatialMetaData(1);')
        self.connection.execute('''PRAGMA synchronous = OFF''')
        self.connection.execute('''PRAGMA journal_mode = OFF''')

        #self.connection.isolation_level = None
        self.connection.row_factory = sqlite3.Row
        print("Connection is established: Database is created in memory")

    def __del__(self):
        self.connection.close()

    def create_index(self):
        sql = ("CREATE INDEX emaps_parcels_score_index ON emaps_parcels_score (segment_index);")
        self.connection.execute(sql)
        sql = ("CREATE INDEX emaps_segments_score_index ON emaps_segments_score (_index);")
        self.connection.execute(sql)
        sql = ("CREATE INDEX emaps_segments_score_index2 ON emaps_segments_score (segment_id);")
        self.connection.execute(sql)
        self.connection.commit()

    def create_tables(self):
        self.connection.execute("CREATE TABLE emaps_variables(id INTEGER PRIMARY KEY AUTOINCREMENT, qid text,desc text, alias text, level text, section text, scale text, subscale text, aggregate text, aggregate_ref text, type text, required text, sum_type text, options text, max_positive_value text, max_negative_value text)")
        self.connection.execute("CREATE TABLE emaps_areas(area_id text, name text )")
        self.connection.execute("CREATE TABLE emaps_segments(segment_id text, area_id text, length, slope )")
        self.connection.execute("CREATE TABLE emaps_segments_score( _id integer, _index integer, area_id text, segment_id text, question_id text, question_qid text, answer text, value integer, aggregated bool )")
        self.connection.execute("CREATE TABLE emaps_parcels_score( parcel_id text, _index integer, segment_index text, segment_id text, question_id text, question_qid text, answer text, value integer )")
        sql = """
                create view emaps_segments_view as 
                    select seval.*, s.length as LENGTH, s.slope as SLOPE, 
                    ( select  count(*)
                    from emaps_parcels_eval
                    where {}=seval.{}
                    ) as NUM_PARCELS,
                    ( select  count(*)
                    from emaps_parcels_eval
                    where {}=seval.{} and {}>0
                    ) as NUM_PARCELS_BUILD
                    from (
                    SELECT {} as _ID, {} as _INDEX, {} as AREA_ID, {} as SEGMENT_ID, PHOTO_1, PHOTO_2, PHOTO_3,  PHOTO_4,  PHOTO_5
                    from  emaps_segments_eval 
                    where upper({})="{}" and {}=1 and upper({})=upper("{}")
                    ) seval, emaps_segments s
                    where seval.SEGMENT_ID=s.segment_id
            """.format(
                        self.general_params["parcel_parent_index"].upper(),
                        self.general_params["csv_index"].upper(),
                        self.general_params["parcel_parent_index"].upper(),
                        self.general_params["csv_index"].upper(),
                        self.general_params["parcel_build_question"].upper(),
                        self.general_params["csv_id"].upper(),
                        self.general_params["csv_index"].upper(),
                        self.general_params["area_id_question"], 
                        self.general_params["segment_id_question"], 
                        self.general_params["evaluation_type_question"],
                        self.general_params["evaluation_type_option"].upper(),
                        self.general_params["segment_exist_question"],
                        self.general_params["evaluation_code_question"].upper(),
                        self.general_params["evaluation_code"])
        self.connection.execute(sql)
        self.connection.commit()

    def create_output_views(self):
        sql = """
            select section, scale, subscale, sum_type,  sum(max_positive_value),  sum(max_negative_value)
            from emaps_variables
            group by section, scale, subscale
        """
        cursor = self.connection.cursor()
        cursor.execute(sql)
        variables_groups = cursor.fetchall()
        add_sql = ""
        add_sql_proportion = ""
        section_ant = None
        scale_ant = None
        subscale_ant = None
        for v in variables_groups:
            max_variable = "max_positive_value"
            
            if section_ant != v["section"]:
                section_ant = v["section"]
                add_sql += """ sum(CASE WHEN section = '{section}' THEN value END) AS section_{section},
	                           sum(CASE WHEN section = '{section}' THEN {max_variable} END) AS section_{section}_max,
                """.format(section=v["section"].strip(), max_variable = max_variable)

                add_sql_proportion += """
                  round( cast (section_{section} as float)  / cast ( section_{section}_max as float) , 3) as section_{section} ,
                """.format(section=v["section"].strip())

            if scale_ant != v["scale"]:
                    if v["sum_type"].lower() == 'negative':
                        max_variable = "max_negative_value"
                    scale_ant = v["scale"]
                    add_sql += """ sum(CASE WHEN section = '{section}' and scale = '{scale}' THEN value END) AS scale_{scale},
                                   sum(CASE WHEN section = '{section}' and scale = '{scale}' THEN {max_variable}  END) AS scale_{scale}_max,
                    """.format(section=v["section"].strip(), scale=v["scale"].strip(), max_variable = max_variable)

                    add_sql_proportion += """
                        round( cast ( scale_{scale} as float)  / cast ( scale_{scale}_max as float) , 3) as scale_{scale} ,
                    """.format(section=v["section"].strip(), scale=v["scale"].strip())

            if subscale_ant != v["subscale"]:
                    if v["sum_type"].lower() == 'negative':
                        max_variable = "max_negative_value"
                    subscale_ant = v["subscale"]
                    add_sql += """ sum(CASE WHEN section = '{section}' and scale = '{scale}' and subscale = '{subscale}' THEN value END) AS {scale}_{subscale},
                                sum(CASE WHEN section = '{section}' and scale = '{scale}' and subscale = '{subscale}' THEN {max_variable}  END) AS {scale}_{subscale}_max,
                    """.format(section=v["section"].strip(), scale=v["scale"].strip(), subscale=v["subscale"].strip(), max_variable = max_variable)

                    add_sql_proportion += """
                        round( cast ( {scale}_{subscale} as float)  / cast ( {scale}_{subscale}_max as float) , 3) as {scale}_{subscale} ,
                    """.format(section=v["section"].strip(), scale=v["scale"].strip(), subscale=v["subscale"].strip())
        
        sql = """
                create view emaps_segments_output as 
                select segment_id, sum(value) as emaps_score,
	                   sum(max_positive_value) as emaps_score_max,
                       {} 
                       date('now') as date,
                       ( select PHOTO_1
                         from emaps_segments_view
                         where SEGMENT_ID=s.segment_id
                       ) as PHOTO_1,
                       ( select PHOTO_2
                         from emaps_segments_view
                         where SEGMENT_ID=s.segment_id
                       ) as PHOTO_2,
                       ( select PHOTO_3
                         from emaps_segments_view
                         where SEGMENT_ID=s.segment_id
                       ) as PHOTO_3,
                       ( select PHOTO_4
                         from emaps_segments_view
                         where SEGMENT_ID=s.segment_id
                       ) as PHOTO_4,
                       ( select PHOTO_5
                         from emaps_segments_view
                         where SEGMENT_ID=s.segment_id
                       ) as PHOTO_5
                from emaps_segments_score s
                join emaps_variables v on
                        s.question_id = v.id 
                where (s.aggregated<>1 or s.aggregated is null) 
                group by segment_id;
            """.format(add_sql)
        self.connection.execute(sql)

        sql = """
                create view emaps_areas_output as 
                select area_id, sum(value) as emaps_score,
	                   sum(max_positive_value) as emaps_score_max,
                       {} 
                       date('now') as date
                from emaps_segments_score s
                join emaps_variables v on
                        s.question_id = v.id 
                where (s.aggregated<>1 or s.aggregated is null) 
                group by area_id;
              """.format(add_sql)
        self.connection.execute(sql)

        sql = """
                create view emaps_segments_output_prop as 
                select segment_id, round( cast (emaps_score as float)  / cast (emaps_score_max as float) , 3)  as emaps_score, 
                {}
                date('now') as date,
                ( select PHOTO_1
                    from emaps_segments_view
                    where SEGMENT_ID=emaps_segments_output.segment_id
                ) as PHOTO_1,
                ( select PHOTO_2
                    from emaps_segments_view
                    where SEGMENT_ID=emaps_segments_output.segment_id
                ) as PHOTO_2,
                ( select PHOTO_3
                    from emaps_segments_view
                    where SEGMENT_ID=emaps_segments_output.segment_id
                ) as PHOTO_3,
                ( select PHOTO_4
                    from emaps_segments_view
                    where SEGMENT_ID=emaps_segments_output.segment_id
                ) as PHOTO_4,
                ( select PHOTO_5
                    from emaps_segments_view
                    where SEGMENT_ID=emaps_segments_output.segment_id
                ) as PHOTO_5
                from emaps_segments_output
              """.format(add_sql_proportion)
        self.connection.execute(sql)

        sql = """
                create view emaps_areas_output_prop as 
                select area_id, round( cast (emaps_score as float)  / cast (emaps_score_max as float) , 3)  as emaps_score, 
                {}
                date('now') as date
                from emaps_areas_output
              """.format(add_sql_proportion)
        self.connection.execute(sql)


    def insert_variable(self, idx, desc, alias, level, section, scale, subscale, aggregate, aggregate_ref, vtype, required, sum_type, options, max_positive_value, max_negative_value):
        ''' Insert variables record '''
        entitie = (idx, desc, alias, level, section.strip(), scale.strip(), subscale.strip(), aggregate, aggregate_ref, vtype, required, sum_type, options, max_positive_value, max_negative_value)
        self.connection.execute('''INSERT INTO emaps_variables(qid, desc, alias, level, section, scale, subscale, aggregate, aggregate_ref, type, required, sum_type, options, max_positive_value, max_negative_value) 
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', entitie)

    def insert_segment(self, segment_id, area_id, length, slope):
        ''' Insert segment record '''
        entitie = (str(segment_id).strip(), str(area_id).strip(), length, slope)
        self.connection.execute('''INSERT INTO emaps_segments(segment_id, area_id, length, slope) VALUES(?,?,?,?)''', entitie)

    def insert_area(self, area_id, name):
        ''' Insert area record '''
        entitie = (str(area_id).strip(), str(name))
        self.connection.execute('''INSERT INTO emaps_areas(area_id, name) VALUES(?,?)''', entitie)

    def table_from_csv(self, table_name, fields, features):
        column_mask = ['?' for number in range(len(fields))]
        fieldset = []
        for field in fields:
            fieldset.append("'{0}' {1}".format(field.strip(), 'TEXT'))
        if len(fieldset) > 0:
            query = "CREATE TABLE IF NOT EXISTS {0} ({1})".format(table_name, ", ".join(fieldset))
        self.connection.execute(query)
        self.connection.commit()
        list_res = []
        for current, feature in enumerate(features):
            attributes = [str(i).strip() for i in feature]
            attributes = ['' if v == None else str(v).strip() for v in feature]
            dictionary_reg = dict(zip(fields, attributes))
            list_res.append(dictionary_reg)
            self.connection.execute("INSERT INTO "+table_name+" VALUES("+", ".join(column_mask)+")", tuple(attributes))
        self.connection.commit()
        return list_res

    def insert_segment_score(self, id, index, area_id, segment_id, question_id, question_qid, answer, value, aggregated):
        entitie = (id, index, area_id, segment_id, question_id, question_qid, answer, value, aggregated)
        self.connection.execute('''INSERT INTO emaps_segments_score( _id, _index, area_id, segment_id, question_id, question_qid, answer, value, aggregated ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)''', entitie)

    def insert_parcel_score(self, index, parcel_id, segment_index, segment_id, question_id, question_qid, answer, value):
        entitie = (parcel_id, index, segment_index, segment_id, question_id, question_qid, answer, value)
        self.connection.execute('''INSERT INTO emaps_parcels_score( parcel_id, _index, segment_index, segment_id, question_id, question_qid, answer, value ) VALUES(?,?,?, ?, ?, ?, ?, ?)''', entitie)

    def begin_transaction(self):
        self.connection.execute('BEGIN')

    def commit(self):
        self.connection.commit()

    def transaction2(self, lista):
        try:
            self.connection.executemany("insert into emaps_segments(segment_id, area_id) values (?,?)", lista)
        except:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()
            