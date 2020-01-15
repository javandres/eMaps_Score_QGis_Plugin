# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Emaps
 Herramienta de Evaluación a Microescala de Ambientes Peatonales
                              -------------------
        begin                : 2019-09-25
        copyright            : (C) 2019 by LlactaLab | Universidad de Cuenca
        email                : llactalab@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
__author__ = 'LlactaLab | Universidad de Cuenca'
__date__ = '2019-09-25'
__copyright__ = '(C) 2019 by LlactaLab | Universidad de Cuenca'

# This will get replaced with a git SHA1 when you do a git archive


__revision__ = '$Format:%H$'

import os
import sqlite3
import numpy as np
from sqlite3 import Error
from .emaps_db_model import EmapsDbModel
from .constants import *

class EmapsScore():
    """
    This class calculate the emaps score
    """

    def __init__(self, feedback, db, general_params, emaps_especification):
        self.db = db
        self.emaps_especification = emaps_especification
        self.general_params = general_params
        self.segment_id = general_params["segment_id"]
        self.area_id = general_params["area_id"]
        self.list_parcels_eval = None
        self.list_segments_eval = None
        self.feedback = feedback
        self.parcels_eval = None
        self.segments_eval = None

    def get_areas_output(self):
        cursor = self.db.connection.cursor()
        sql = '''
                select *
                from emaps_areas_output
            '''
        cursor.execute(sql)
        return cursor.fetchall()

    def get_areas_output_proportion(self):
        cursor = self.db.connection.cursor()
        sql = '''
                select *
                from emaps_areas_output_prop
            '''
        cursor.execute(sql)
        return cursor.fetchall()

    def get_segments_output(self):
        cursor = self.db.connection.cursor()
        sql = '''
                select *
                from emaps_segments_output
            '''
        cursor.execute(sql)
        return cursor.fetchall()

    def get_segments_output_proportion(self):    
        cursor = self.db.connection.cursor()
        sql = '''
                select *
                from emaps_segments_output_prop
            '''
        cursor.execute(sql)
        return cursor.fetchall()

    def score(self):
        variables = self.emaps_especification
        total = 95.0 / len(self.emaps_especification) if self.emaps_especification else 0
        current = 0
        self.fetch_parcels_eval()
        self.fetch_segments_eval()
        for q in self.emaps_especification:
            current += 1
            self.feedback.setProgress(int(current * total))
            if variables[q]["level"].upper() == "SEGMENT":
                self.process_segment_variable(variables[q]["variable"], variables[q])
            if variables[q]["level"].upper() == "PARCEL":
                self.process_parcel_variable(variables[q]["variable"], variables[q])
        self.process_segment_aggregated_variables()
        self.db.create_output_views()
    
    def fetch_parcels_eval(self):
        cursor = self.db.connection.cursor()
        sql = '''
                select seval.*, s.length, s.slope
                from (
                    SELECT s.{} as SEGMENT_INDEX, s.{} as AREA_ID, s.{} as SEGMENT_ID, p.*
                    from  emaps_segments_eval s, emaps_parcels_eval p
                    where upper({})="{}" and {}=1 and upper({})=upper("{}")
                    and p.{}=s.{}
                ) seval, emaps_segments s
                where seval.SEGMENT_ID=s.segment_id  
            '''.format(
                    self.general_params["csv_index"].upper(),
                    self.general_params["area_id_question"], 
                    self.general_params["segment_id_question"], 
                    self.general_params["evaluation_type_question"],
                    self.general_params["evaluation_type_option"].upper(),
                    self.general_params["segment_exist_question"],
                    self.general_params["evaluation_code_question"].upper(),
                    self.general_params["evaluation_code"],
                    self.general_params["parcel_parent_index"].upper(),
                    self.general_params["csv_index"].upper(),
                )
        cursor.execute(sql)
        res = cursor.fetchall()
        self.parcels_eval = res

    def fetch_segments_eval(self):
        cursor = self.db.connection.cursor()
        sql = '''
                select seval.*, s.length, s.slope
                from (
                  SELECT {} as _ID, {} as _INDEX, {} as AREA_ID, {} as SEGMENT_ID, emaps_segments_eval.*
                  from  emaps_segments_eval 
                  where upper({})="{}" and {}=1 and upper({})=upper("{}")
                ) seval, emaps_segments s
                where seval.SEGMENT_ID=s.segment_id  
            '''.format(
                    self.general_params["csv_id"].upper(),
                    self.general_params["csv_index"].upper(),
                    self.general_params["area_id_question"], 
                    self.general_params["segment_id_question"], 
                    self.general_params["evaluation_type_question"],
                    self.general_params["evaluation_type_option"].upper(),
                    self.general_params["segment_exist_question"],
                    self.general_params["evaluation_code_question"].upper(),
                    self.general_params["evaluation_code"]
            )
        cursor.execute(sql)
        res = cursor.fetchall()
        self.segments_eval = res

    def process_segment_variable(self, q_id, q):
        if q["aggregate"].upper() == "TRUE":
            pass
        else:
            if q["type"].lower() == "slope":
                res = self.get_segment_variable(self.general_params["segment_id_question"])
            else:
                res = self.get_segment_variable(q_id)
            if res:
                for r in res:
                    answer = r["VAR"]
                    if q["type"].lower() == "slope":
                        answer = r["slope"]
                    new_value = self.process_variable(q=q, value=r["VAR"], length=r["length"], slope=r["slope"])
                    self.db.insert_segment_score(id=r["_ID"], index=r["_INDEX"], area_id=r["AREA_ID"], segment_id=r["SEGMENT_ID"], 
                                                 question_id=q["idx"], question_qid=q_id, answer=answer, value=new_value, 
                                                 aggregated=bool(q["aggregate_ref"]))
                self.db.commit()
            else:
                if q["required"].upper() == "TRUE":
                    raise Exception('ERROR: The question: '+q_id+" is required")

    def process_parcel_variable(self, q_id, q):
        if q["aggregate"].upper() == "TRUE":
            pass
        else:
            parcel_variables = self.get_parcel_variable(q_id)
            if parcel_variables:
                for r in parcel_variables:
                    new_value = self.process_variable(q=q, value=r["VAR"], length=None, slope=None)
                    self.db.insert_parcel_score(index=r["_INDEX"], parcel_id=r["PARCEL_ID"], segment_index=r["_PARENT_INDEX"], segment_id=r["SEGMENT_ID"],
                                                question_id=q["idx"], question_qid=q_id, answer=r["VAR"], value=new_value)
                self.db.commit()
            else:
                if q["required"].upper() == "TRUE":
                    raise Exception('ERROR: The question: '+q_id+" is required")
        return

    def process_segment_aggregated_variables(self):
        cursor = self.db.connection.cursor()
        sql = '''
                 select *, id || "|" || qid as id_qid
                 from emaps_variables
                 where aggregate="TRUE" and aggregate_ref = '' and upper(level)=upper("SEGMENT")
              '''
        cursor.execute(sql)
        aggregated_vars = cursor.fetchall()
        for var in aggregated_vars:
            variable = self.emaps_especification[var["id_qid"]]
            if self.is_parcel_aggregated(variable["type"]):
                self.process_parcel_aggregated_variable(variable)
            else:    
                self.process_segment_aggregated_variable(variable)

    def process_parcel_aggregated_variable(self, variable):
        ref_variables = self.get_aggregated_ref_variables(variable["variable"])
        ref_list = []
        for ref in ref_variables:
            ref_list.append('\"'+ref["qid"]+'\"')
        if ref_list:
            cursor = self.db.connection.cursor()
            sql = '''
                select s.*, value, round(  value / NUM_PARCELS, 3)  as PARCELS_PROPORTION,  round( value / NUM_PARCELS_BUILD, 3 ) as PARCELS_BUILD_PROPORTION
                from emaps_segments_view s left join(
                    select segment_id, segment_index, cast(sum(value) as real) as value
                    from emaps_parcels_score
                    where question_qid in ( {} )
                    group by segment_id, segment_index
                ) v on s.segment_id = v.segment_id		
                '''.format(",".join(ref_list))
            cursor.execute(sql)
            segments_var = cursor.fetchall()
            for s in segments_var:
                if variable["type"].upper() == PROPORTION_BUILDING:
                    val = s["PARCELS_BUILD_PROPORTION"]
                elif variable["type"].upper() == PROPORTION_PARCELS:
                    val = s["PARCELS_PROPORTION"]
                elif variable["type"].upper() == NUM_IN_PARCELS:
                    val = s["value"]
                new_value = self.process_variable(q=variable, value=val, length=s["length"], slope=s["slope"])
                self.db.insert_segment_score(id=s["_id"], index=s["_index"], area_id=s["area_id"], segment_id=s["segment_id"], 
                                             question_id=variable["idx"], question_qid=variable["variable"], answer=val, value=new_value, 
                                             aggregated=None)
            self.db.commit()
        return True

    def process_segment_aggregated_variable(self, variable):
        ref_variables = self.get_aggregated_ref_variables(variable["variable"])
        ref_list = []
        for ref in ref_variables:
            if ref["aggregate"] == "TRUE":
                variable_ref = self.emaps_especification[ref["id_qid"]]
                self.process_segment_aggregated_variable(variable_ref)
            ref_list.append('\"'+ref["qid"]+'\"')
        if ref_list:
            operation = "sum"
            if variable["type"] == "numeric" or variable["type"] == "sum":
                operation = "sum"
            if variable["type"] == "max":
                operation = "max"
            if variable["type"] == "min":
                operation = "min"
            if variable["type"] == "count":
                operation = "count"
            cursor = self.db.connection.cursor()
            sql = '''
                select v.*, length, slope
                from (
                   select area_id,segment_id, _id, _index, {}(value) as value
                   from emaps_segments_score
                   where question_qid in ( {} )
                   group by area_id,segment_id,_id, _index
                ) v, emaps_segments s
                where v.segment_id = s.segment_id	   
                '''.format(operation, ",".join(ref_list))
            cursor.execute(sql)
            segments_var = cursor.fetchall()
            aggregated = None
            if variable["aggregate_ref"]:
                aggregated = True
            for s in segments_var:
                new_value = self.process_variable(q=variable, value=s["value"], length=s["length"], slope=s["slope"])
                self.db.insert_segment_score(id=s["_id"], index=s["_index"], area_id=s["area_id"], segment_id=s["segment_id"], 
                                             question_id=variable["idx"], question_qid=variable["variable"], answer=s["value"], value=new_value, 
                                             aggregated=aggregated)
            self.db.commit()
        return True

    def get_aggregated_ref_variables(self, vid):
        cursor = self.db.connection.cursor()
        sql = '''select *, id || "|" || qid as id_qid
                 from emaps_variables
                 where aggregate_ref="{}" 
            '''.format(vid)
        cursor.execute(sql)
        aggregated_vars = cursor.fetchall()
        return aggregated_vars

    def get_segment_variable(self, q_id):
        var = [{"_ID": row["_ID"], "_INDEX":row["_INDEX"], "AREA_ID":row["AREA_ID"], "SEGMENT_ID":row["SEGMENT_ID"], "length":row["length"], "slope":row["slope"],  "VAR":row[q_id]} for row in self.segments_eval]
        return var

    def get_parcel_variable(self, q_id):
        var = [{"PARCEL_ID": row[self.general_params["parcel_id_question"]], "_INDEX":row[self.general_params["csv_index"].upper()], "_PARENT_INDEX":row[ self.general_params["parcel_parent_index"]], "SEGMENT_ID":row["SEGMENT_ID"], "VAR":row[q_id]} for row in self.parcels_eval]
        return var

    def process_variable(self, q, value, length, slope):
        if q["type"] == "option":
            value = self.process_option_variable(q, value)
        elif q["type"] == "bool":
            value = self.process_bool_variable(q, value)
        elif q["type"] == "numeric":
            value = self.process_numeric_variable(q, value)
        elif q["type"] == "slope":
            value = self.process_numeric_variable(q, slope)    
        elif q["type"] == "formula":
            value = self.process_formula_variable(q, value, length, slope)    
        elif q["type"] == "sum" or q["type"] == "max" or q["type"] == "min" or q["type"] == "count":
            value = value
        elif self.is_parcel_aggregated(q["type"]):    
            value = self.process_numeric_variable(q, value)
        else:
            value = 0
        return value

    def process_formula_variable(self, q, value, length, slope):
        res = None
        expr = q["options"]["fx"]["option"]
        expr = expr.replace("[value]", str(value))
        expr = expr.replace("[segment_length]", str(length))
        expr = expr.replace("[segment_slope]", str(slope))
        try:
            res = eval(expr)
        except:
            res = None
        return res

    def process_option_variable(self, q, value):
        if(value.upper() == "NS_NA" or value is None):
            return 0
        for v in q["options"]:
            other_value = None
            if v == "*":
                other_value = q["options"][v]["value"]
            if str(value).upper() == str(v).upper():
                return q["options"][v]["value"]
        if other_value:
            return other_value
        return None

    def process_bool_variable(self, q, value):
        #print("BOOL:",q, value)
        if(value.upper() == "NS_NA" or value is None):
            return 0
        if str(value) == '1':
            return q["options"]["True"]["value"]
        elif str(value) == '0':
            return q["options"]["False"]["value"]
        return None

    def process_numeric_variable(self, q, value):
        if (isinstance(value, str) and value.upper() == "NS_NA")  or value is None:
            return 0
        for v in q["options"]:
            passed = False
            res_value = None
            other_value = None
            for cond in q["options"][v]:
                if cond != "value":
                    if cond == "*":
                        other_value = q["options"][v]["value"]
                    passed = self.process_range_condition(cond, q["options"][v][cond], value)
                    if not passed:
                        break
                else:
                    res_value = q["options"][v]["value"]
            if passed:
                return res_value
            else:
                if other_value:
                    return other_value
        return 0

    def process_range_condition(self, operator, condition, value):
        try:
            value = float(value)
            condition = float(condition)
        except ValueError:
            if operator.upper() == "EQ" and value == condition:
                return True
            else:
                return False
        if operator.upper() == "GT" and value > condition:
            return True
        elif operator.upper() == "GTE" and value >= condition:
            return True
        elif operator.upper() == "LT" and value < condition:
            return True
        elif operator.upper() == "LTE" and value <= condition:
            return True
        elif operator.upper() == "EQ" and value == condition:
            return True
        return False

    def is_parcel_aggregated(self, vtype):
        if vtype.upper() == PROPORTION_BUILDING or vtype.upper() == PROPORTION_PARCELS or vtype.upper() == NUM_IN_PARCELS:
            return True
        return False
