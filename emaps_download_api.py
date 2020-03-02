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

    def get_form_data(self, params):
        print(params)
        url = self.kobo_url + 'api/v2/assets/'+params["form_id"]+'/data.json'
        try:
            r = requests.get(url, auth=(self.kobo_user, self.kobo_password))
            r.raise_for_status()
        except requests.exceptions.RequestException as err:
            raise Exception("Ha ocurrido un error, comprueba la URL y su USUARIO y CONTRASEÑA...")
        except requests.exceptions.HTTPError as errh:
            raise Exception(errh)
        except requests.exceptions.ConnectionError as errc:
            raise Exception(errc )
        except requests.exceptions.Timeout as errt:
            raise Exception(errt)  
        # try:
        #     r.raise_for_status()
        # except requests.exceptions.HTTPError as e:
        #     print (e.response.text)
        r.encoding = 'UTF-8'
        data = json.loads(r.text)
        res_data = self.process_segments(data["results"])
        return res_data

    def process_segments(self, results):
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
                        quest_emaps[value.lower()] = row[key]
                    elif key == "s2_lote":
                        parcels_dict_list = self.process_parcels(index, row["s2_lote"])
                        res_parcels_data = res_parcels_data + parcels_dict_list
                    elif key == "_attachments":
                        at_cont = 0
                        for photo in row["_attachments"]:
                            at_cont = at_cont+1
                            quest_meta["photo_"+str(at_cont)] = photo["download_large_url"]
                    else:
                        quest_meta[key.lower()] = row[key]
            
            quest_emaps_ordered = {}
            quest_meta_ordered = {}
            for i in sorted(quest_emaps.keys()):
                quest_emaps_ordered[i] = quest_emaps[i]
            for i in sorted(quest_meta.keys()):
                quest_meta_ordered["_index"] = index
                quest_meta_ordered[i] = quest_meta[i]
            quest_meta_ordered.update(quest_emaps_ordered)
            res_segments_columns = list(set(res_segments_columns) | set(list(quest_meta_ordered.keys())))
            res_segment_data.append(quest_meta_ordered)
        return {
            "segments_data": res_segment_data,
            "parcels_data": res_parcels_data,
            "segments_columns": sorted(res_segments_columns),
            "parcels_columns": sorted(self.res_parcels_columns)
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
