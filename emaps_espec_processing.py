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
import csv
import re
from .constants import *
import yaml

class EmapsEspecificationProcessing():
    """
    Algoritmo para procesamiento de la especificación de protocolo eMAPS.ec
    desde archivo plano de texto en formato CSV.

    """

    def __init__(self):
        pass
     
    @classmethod    
    def processCsvParamsFile(cls, file):
        params = dict()
        with open(file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            j = 0
            for row in reader:
                if row["variable"][0:1] == "#" or row["variable"][0:1] == "" or row["required"]=="FALSE":
                    continue
                values = dict()
                end_options = False
                i = 1
                j = j + 1
                max_positive_value = 0
                max_negative_value = 0
                while not end_options:
                    try:
                        val = row["option_"+str(i)].strip()
                        if(val):
                            quest_option = cls.readQuestion(row["type"], row["option_"+str(i)])
                            d = quest_option["option"]
                            values.update(d)
                            if row["aggregate_ref"].strip() == "" and int(quest_option["value"]) > 0:
                                if int(quest_option["value"]) > max_positive_value:
                                    max_positive_value = int(quest_option["value"])
                            elif row["aggregate_ref"].strip() == "" and int(quest_option["value"]) < 0:
                                if int(quest_option["value"]) < max_negative_value:
                                    max_negative_value = int(quest_option["value"])  
                        else:
                            end_options = True
                    except Exception as error:
                        print("An error occurred: QUESTION: " + repr(row["variable"])+ ": ERROR:" + repr(error))   
                        end_options = True
                    i = i+1
                new_row = dict()
                condition = ""
                if ('condition' in row):
                    condition = row["condition"]
                new_row = {
                    "idx": j,
                    "id": str(j)+"|"+row["variable"],
                    "variable": row["variable"],
                    "desc": row["desc"],
                    "alias": row["alias"],
                    "level": row["level"],
                    "section": row["section"],
                    "scale": row["scale"],
                    "subscale": row["subscale"],
                    "aggregate": row["aggregate"],
                    "aggregate_ref": row["aggregate_ref"],
                    "type": row["type"],
                    "required": row["required"],
                    "condition": condition,
                    "sum_type": row["sum_type"],
                    "options" : values,
                    "max_positive_value" : max_positive_value,
                    "max_negative_value" : max_negative_value
                }
                new_dict = {str(j)+"|"+row["variable"] : new_row}
                params = dict(params, **new_dict)
        return params

    @classmethod
    def processYamlParamsFile(cls, param_file):
        params = {}
        with open(param_file) as pfile:
            params = yaml.safe_load(pfile)
            return params
        
    @classmethod    
    def readQuestion(cls,  qtype, question):
        dict_res = None
        question = question.replace(" ", "")
        if(qtype == "option" or qtype == "bool"):
            option_label = None
            value = None
            option_code = None
            match = re.search(r'^([a-zA-Z1-9*+]+)=(-?[\d]+)(:(.+))?$', question)
            if match:
                value = match.group(2)
                option_label = match.group(4)
                option_code = match.group(1)
                #print("Question:",match.group(1),"Value:",match.group(2),"Option:",match.group(3) )
            else:
                raise Exception('Error in expression format: {}'.format(question))
            d = dict()
            d = {
                "option":option_label,
                "value" : value
            }
            dict_res = {
                option_code : d
            }
        if(qtype.upper() == "NUMERIC" or qtype.upper() == "SLOPE" or qtype.upper() == PROPORTION_BUILDING or qtype.upper() == PROPORTION_PARCELS or qtype.upper() == NUM_IN_PARCELS or qtype.upper() == SHANNON_INDEX):
            match = re.search(r'((^\(?(,?(>|<|<=|>=)\d+(\.\d+)?){1,}\)?)|(^\(?\"?.+\"?\)?)|(^\(?\*\)?))=-?\d+$', question)
            res_exp = dict()
            if match:
                expressionRegex = re.compile(r',?(>|<|<=|>=)(\d+(\.\d+)?)')
                expressionsList = expressionRegex.findall(question)
                if (expressionsList):
                    for exp in expressionsList:
                        operator = cls.getOperator(exp[0])
                        res_exp.update({operator: exp[1]})
                else:
                    match = re.search(r'((\(?\"?)([^\)\"\*]+)(\"?\)?))=-?\d+$', question)
                    if(match):
                        exp = match.group(3)
                        res_exp.update({"eq": exp})
                    else:
                        match = re.search(r'((\(?\"?)(\*)(\"?\)?))=-?\d+$', question)
                        exp = match.group(3)
                        res_exp.update({"*": exp})
                matchValue = re.search(r'=(-?\d+)$', question)
                value = matchValue.group(1)
                res_exp.update({"value":value})
            else: 
                raise Exception('Error in numeric expression format: {}'.format(question))
            dict_res = {
                question : res_exp
            }
        if(qtype == "formula"):
            value = None
            d = dict()
            d = {
                "option":question,
                "value" : value
            }
            dict_res = {
                "fx" : d
            }
        if not dict_res:
            value = None
            d = {
                "option":None,
                "value" : value
            }
            dict_res = {
                "None" : d
            }
        return {
            "value":value,
            "option": dict_res
        }    

    @classmethod
    def getOperator(cls, i):
        switcher = {
            '<':'lt',
            '>':'gt',
            '<=':'lte',
            '>=':'gte'
        }
        return switcher.get(i, "Invalid operator")
        