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
import json
import requests
import re
from .constants import *

class EmapsDownloadApi():
    """
    This class calculate the emaps score
    """

    def __init__(self, feedback, kobo_url, kobo_user, kobo_password):
        self.kobo_url = kobo_url
        self.kobo_user = kobo_user
        self.kobo_password = kobo_password
        self.feedback = feedback
        self.parcel_index = 0
        self.res_parcels_columns = []
        self.columns = {}

    def get_form_columns(self, form_id):
        url = self.kobo_url + 'api/v2/assets/'+form_id+'.json'
        try:
            r = requests.get(url, auth=(self.kobo_user, self.kobo_password))
            r.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("Ha ocurrido un error, comprueba la URL, USUARIO y CONTRASEÑA...")
        except requests.exceptions.HTTPError as errh:
            raise Exception(errh)
        except requests.exceptions.ConnectionError as errc:
            raise Exception(errc)
        except requests.exceptions.Timeout as errt:
            raise Exception(errt)
        r.encoding = 'UTF-8'
        data = json.loads(r.text)
        columns_segment = {}
        columns_parcel = {}
        if data["content"]["survey"]:
            parcel_question = False
            for q in data["content"]["survey"]:
                if q["type"] in ["begin_group", "end_group", "acknowledge", "begin_repeat", "end_repeat"]:
                    if parcel_question and q["type"]== "end_repeat":
                        parcel_question = False
                    if "name" in q and q["name"] == "s2_lote" and q["type"]=="begin_repeat":
                        parcel_question = True
                else:
                    label = ""
                    if "label" in q:
                        label = q["label"][0]
                    if parcel_question:
                        columns_parcel[q["name"]] = label
                    else:
                        columns_segment[q["name"]] = label
            columns_segment["photo_1"] = "photo_1"
            columns_segment["photo_2"] = "photo_2"
            columns_segment["photo_3"] = "photo_3"
            columns_segment["photo_4"] = "photo_4"
            columns_segment["photo_5"] = "photo_5"
            return {
                "columns_segment" : columns_segment,
                "columns_parcel" : columns_parcel
            }
        else:
            raise Exception("Error al leer formulario,  por favor revise el ID del formulario")

    def get_form_data(self, params):
        self.columns = self.get_form_columns(params["form_id"])

        url = self.kobo_url + 'api/v2/assets/'+params["form_id"]+'/data.json'
        query_params_list = []
        if params["cod_estudio"]:
            query_params_list.append({"metadatos_ini/m_002":params["cod_estudio"]})
        if params["nombre_usuario"]:
            query_params_list.append({"metadatos_ini/m_001":params["nombre_usuario"]})
        if params["tipo_levantamiento"]:
            tipo_evaluacion = []
            for tipo in params["tipo_levantamiento"]:
                value = TIPOS_LEVANTAMIENTO[tipo]
                tipo_evaluacion.append(value)    
            query_tipo_evaluacion = []    
            if(len(tipo_evaluacion)==1):    
                query_params_list.append({"metadatos_ini/m_003":tipo_evaluacion[0]})
            else:
                query_tipo_evaluacion = {}
                query_tipo_evaluacion["$or"]=[]
                for q in tipo_evaluacion:
                    query_tipo_evaluacion["$or"].append({"metadatos_ini/m_003":q})
                query_params_list.append(query_tipo_evaluacion)        
        query = ""
        if len(query_params_list) >= 2:
            query = '?query={"$and":['
            cont = 0
            for q in query_params_list:
                if cont > 0:
                    query = query + ","
                query = query + str(q).replace("'", '"')
                cont = cont + 1
            query = query + ']}'
        else:    
            query = query + "?query="+str(query_params_list[0]).replace("'", '"')
        url = url + query
        print(url)
        self.feedback.pushInfo("URL QUERY: "+ url)
        try:
            r = requests.get(url, auth=(self.kobo_user, self.kobo_password))
            r.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("Ha ocurrido un error, comprueba la URL y su USUARIO y CONTRASEÑA...")
        except requests.exceptions.HTTPError as errh:
            raise Exception(errh)
        except requests.exceptions.ConnectionError as errc:
            raise Exception(errc)
        except requests.exceptions.Timeout as errt:
            raise Exception(errt)
        r.encoding = 'UTF-8'
        data = json.loads(r.text)
        if data["results"]:
            self.feedback.pushInfo("Se han encontrado: "+ str(len(data["results"])) + " registros")
            res_data = self.process_segments(data["results"], params)
            return res_data
        else:
            raise Exception("No se encontraron registros para los parámetros ingresados!")      
        
    def process_segments(self, results, params):
        index = 0
        res_segment_data = []
        res_parcels_data = []
        res_segments_columns = []
        for row in results:
            index = index+1
            keys = row.keys()
            quest_emaps = {}
            quest_meta = {}
            for key in keys:
                match = re.search(r'/+(\w*)$', key)
                if match:
                    value = match.group(1)
                    quest_emaps[value.lower()] = row[key]
                else:
                    if key in ('q_084', 'q_097'):
                        quest_emaps[key.lower()] = row[key]
                    elif key == "s2_lote":
                        parcels_dict_list = self.process_parcels(index, row["s2_lote"])
                        res_parcels_data = res_parcels_data + parcels_dict_list
                    elif key == "_attachments":
                        at_cont = 0
                        for photo in row["_attachments"]:
                            at_cont = at_cont+1
                            quest_emaps["photo_"+str(at_cont)] = photo["download_large_url"]
                    else:
                        quest_meta[key.lower()] = row[key]
            if row["_geolocation"]:
                quest_meta["lat"] = row["_geolocation"][0]
                quest_meta["lon"] = row["_geolocation"][1]
            quest_emaps_ordered = {}
            quest_meta_ordered = {}
            for i in sorted(quest_emaps.keys()):
                quest_emaps_ordered[i] = quest_emaps[i]
            for i in sorted(quest_meta.keys()):
                quest_meta_ordered["_index"] = index
                quest_meta_ordered[i] = quest_meta[i]
            quest_meta_ordered.update(quest_emaps_ordered)

            for k in self.columns["columns_segment"].keys():
                quest_meta_ordered.setdefault(k, "")

            res_segments_columns = list(set(res_segments_columns) | set(list(quest_meta_ordered.keys())))
            res_segment_data.append(quest_meta_ordered)

        results = self.process_column_titles(params["title_type"], res_segment_data, sorted(res_segments_columns), res_parcels_data, sorted(self.res_parcels_columns))
        return results

    def process_column_titles(self, title_type, segments_data, segments_columns, parcels_data, parcel_columns):
        if TIPOS_TITULO[title_type] == "cod":
            return {
                "segments_data": segments_data,
                "parcels_data": parcels_data,
                "segments_columns": segments_columns,
                "parcels_columns": parcel_columns
            }
        else:
            res_segment_data = []
            res_segments_columns = []
            for row in segments_data:
                new_row = {}
                keys = row.keys()
                for key in keys:
                    if key in  self.columns["columns_segment"]:
                        if not self.columns["columns_segment"][key] == "":
                            new_key = self.columns["columns_segment"][key].upper()
                            if new_key.startswith(key.upper()):
                                new_key = new_key.replace(key.upper(), "")
                            new_key = key.upper() + " " + new_key
                            new_row[new_key] = row[key]
                        else:
                            new_row[key] = row[key]
                    else:
                        new_row[key] = row[key]
                res_segment_data.append(new_row)
                res_segments_columns = list(set(res_segments_columns) | set(list(new_row.keys())))  

            res_parcels_data = []
            res_parcels_columns = []
            for row in parcels_data:
                new_row = {}
                keys = row.keys()
                for key in keys:
                    if key in  self.columns["columns_parcel"]:
                        if not self.columns["columns_parcel"][key] == "":
                            new_key = self.columns["columns_parcel"][key].upper()
                            if new_key.startswith(key.upper()):
                                new_key = new_key.replace(key.upper(), "")
                            new_key = key.upper() + " " + new_key
                            new_row[new_key] = row[key]
                        else:
                            new_row[key] = row[key]
                    else:
                        new_row[key] = row[key]
                res_parcels_data.append(new_row)
                res_parcels_columns = list(set(res_parcels_columns) | set(list(new_row.keys())))      

            return {
                "segments_data": res_segment_data,
                "parcels_data": res_parcels_data,
                "segments_columns": sorted(res_segments_columns),
                "parcels_columns": sorted(res_parcels_columns)
            }                





    def process_parcels(self, segment_index, parcels_list):
        res_parcels_list = []
        for row in parcels_list:
            self.parcel_index = self.parcel_index + 1
            keys = row.keys()
            quest_parcels = {}
            for key in keys:
                match = re.search(r'/+(\w*)$', key)
                if match:
                    value = match.group(1)
                    quest_parcels[value.lower()] = row[key]
                else:
                    quest_parcels[key.lower()] = row[key]
            
            quest_parcels_ordered = {}
            quest_parcels_ordered["_index"] = self.parcel_index
            quest_parcels_ordered["_parent_index"] = segment_index
            for i in sorted(quest_parcels.keys()):
                quest_parcels_ordered[i] = quest_parcels[i]
            res_parcels_list.append(quest_parcels_ordered)    
            self.res_parcels_columns = list(set(self.res_parcels_columns) | set(list(quest_parcels_ordered.keys())))        
        return res_parcels_list
