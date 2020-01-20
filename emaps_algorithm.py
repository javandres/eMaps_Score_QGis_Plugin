# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Emaps
                                 A QGIS plugin
 Herramienta de Evaluación a Microescala de Ambientes Peatonales
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
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
import time
import inspect
import qgis.core
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtCore import QCoreApplication, QVariant

from qgis.core import (QgsField,
                       QgsFields,
                       QgsProcessing,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFile,
                       QgsProcessingFeedback,
                       QgsMessageLog,
                       QgsVectorLayer,
                       QgsProcessingUtils)
import processing
from processing.core.Processing import Processing
from .emaps_score import EmapsScore
from .emaps_espec_processing import EmapsEspecificationProcessing
from .emaps_db_model import EmapsDbModel

class EmapsAlgorithm(QgsProcessingAlgorithm):
    """
    eMAPS Score Algorithm
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT_SEGMENTS_SCORE = 'OUTPUT_SEGMENTS_SCORE'
    OUTPUT_SEGMENTS_SCORE_PROPORTION = 'OUTPUT_SEGMENTS_SCORE_PROPORTION'
    OUTPUT_AREAS_SCORE = 'OUTPUT_AREAS_SCORE'
    OUTPUT_AREAS_SCORE_PROPORTION = 'OUTPUT_AREAS_SCORE_PROPORTION'
    SEGMENTS_GEOM = 'SEGMENTS_GEOM'
    AREAS_GEOM = 'AREAS_GEOM'
    SEGMENTS_EVAL = 'SEGMENTS_EVAL'
    PARCELS_EVAL = 'PARCELS_EVAL'
    DICTIONARY = 'DICTIONARY'
    GPARAMS = 'GPARAMS'

    dest_segments_score = None
    dest_segments_score_prop = None
    dest_areas_score = None
    dest_areas_score_prop = None

    default_general_params = {
        'version':'0.0.1',
        'author':'Llactalab',
        'emaps':'6.3',
        'segment_id':'seg_id',
        'segment_length_attribute':'length',
        'segment_slope_attribute':'slope',
        'area_id': 'cod_inst',
        'area_name_attribute':'nomb_inst',
        'evaluation_type_question':'M_003',
        'evaluation_type_option':'A',
        'evaluation_code_question':'M_002',
        'evaluation_code':'edpa_lev1',
        'area_id_question':"Q_000",
        'segment_id_question':'Q_001',
        'segment_exist_question':'Q_002',
        'parcel_id_question':'Q_015',
        'parcel_build_question':'Q_017',
        'csv_id':'_id',
        'csv_index': '_index',
        'parcel_parent_index': '_parent_index'
    }

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.AREAS_GEOM,
                self.tr('🗺 Areas evaluation layer \n(dataset with the geometry of the evaluated areas)'),
                [QgsProcessing.TypeVector ]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SEGMENTS_GEOM,
                self.tr('🗺 Segments evaluation layer \n(Line dataset with the geometry of the evaluated street segments)'),
                [QgsProcessing.TypeVectorLine ]
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name=self.SEGMENTS_EVAL,
                description=self.tr('📋 Segments Evaluation \n(csv file downloaded from the KoboToolbox plaform for the corresponding version)'),
                extension="csv",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name=self.PARCELS_EVAL,
                description=self.tr('📋 Parcels Evaluation \n(csv file downloaded from the KoboToolbox plaform for the corresponding version)'),
                extension="csv",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name=self.DICTIONARY,
                description=self.tr('📄 eMAPS Specification File \n(CSV file with a data dictionary which maps the question and answer labels and values)'),
                extension="csv",
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name=self.GPARAMS,
                description=self.tr('📄 eMAPS General Params File \n(CSV file with general parammeters)'),
                extension="csv",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_SEGMENTS_SCORE,
                self.tr('OUTPUT: Segment eMAPS-Score')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_SEGMENTS_SCORE_PROPORTION,
                self.tr('OUTPUT: Segment eMAPS-Score Proportion')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_AREAS_SCORE,
                self.tr('OUTPUT: Areas eMAPS-Score')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_AREAS_SCORE_PROPORTION,
                self.tr('OUTPUT: Areas eMAPS-Score Proportion')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        global_params_source = self.parameterAsSource(parameters, self.GPARAMS, context)
        feedback.pushInfo("⚙ Procesando parámetros generales...")
        if global_params_source:
            features_global_params = global_params_source.getFeatures()
            general_params = dict()
            for current, feature in enumerate(features_global_params):
                if feedback.isCanceled():
                    break
                attributes = feature.attributes()
                general_params.update({attributes[0]:attributes[1]})
                feedback.setProgress(int(current))
        else:
            general_params = self.default_general_params

        feedback.pushInfo("eMaps.ec Version: "+general_params["emaps"])
        feedback.pushInfo("eMaps.ec Author: "+general_params["author"])
        feedback.pushInfo("OK ✔")

        segment_id = general_params["segment_id"]
        area_id = general_params["area_id"]

        feedback.pushInfo("⚙ Procesando archivo especificación de protocolo eMAPS...")
        param_file = self.parameterAsFile(parameters, self.DICTIONARY, context)
        variables_especification = EmapsEspecificationProcessing.processCsvParamsFile(param_file)
        print("Num Variables:", len(variables_especification))
        feedback.pushInfo("✔ No. de Variables: "+str(len(variables_especification)))

        db=EmapsDbModel(general_params, r'/home/jagg/apps/ucuenca/emaps/mydatabase.db')
        db.create_tables()

        for v in variables_especification:
            variable = variables_especification[v]
            db.insert_variable(variable["variable"], variable["desc"], variable["alias"],
                               variable["level"], variable["section"], variable["scale"], variable["subscale"],
                               variable["aggregate"], variable["aggregate_ref"], variable["type"], variable["required"], variable["sum_type"], 
                               json.dumps(variable["options"]), variable["max_positive_value"], variable["max_negative_value"])
        db.commit()

        feedback.pushInfo("⚙ Cargando capa de áreas de estudio 🗺...")
        areas_geom = self.parameterAsSource(parameters, self.AREAS_GEOM, context)

        total = 100.0 / areas_geom.featureCount() if areas_geom.featureCount() else 0
        features = areas_geom.getFeatures()
        fieldnames = [field.name() for field in areas_geom.fields()]
        lista_areas = []
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            attributes = feature.attributes()
            attributes_replaced_null = [None if a == qgis.core.NULL else a for a in attributes]
            feedback.setProgress(int(current * total))
            lista_areas_dict = dict(zip(fieldnames, attributes_replaced_null ))
            lista_areas.append(lista_areas_dict)
            db.insert_area(lista_areas_dict[general_params["area_id"]], lista_areas_dict[general_params["area_name_attribute"]])
        feedback.pushInfo("✔ Areas de estudio cargadas: "+str(len(lista_areas)))

        feedback.pushInfo("⚙ Cargando capa de segmentos de calle 🗺...")
        segments_geom = self.parameterAsSource(parameters, self.SEGMENTS_GEOM, context)
        
        total = 100.0 / segments_geom.featureCount() if segments_geom.featureCount() else 0
        features = segments_geom.getFeatures()
        fieldnames = [field.name() for field in segments_geom.fields()]
        lista_segmentos = []
        t = time.time()
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            
            attributes = feature.attributes()
            attributes_replaced_null = [None if a == qgis.core.NULL else a for a in attributes]
            feedback.setProgress(int(current * total))
            lista_segmentos_dict = dict(zip(fieldnames, attributes_replaced_null ))
            lista_segmentos.append(lista_segmentos_dict)
            db.insert_segment(lista_segmentos_dict[segment_id], lista_segmentos_dict[area_id], 
                              lista_segmentos_dict[general_params["segment_length_attribute"]], 
                              lista_segmentos_dict[general_params["segment_slope_attribute"]])
        feedback.pushInfo("✔ Segmentos de calle cargados: "+str(len(lista_segmentos)))
        
        feedback.pushInfo("⚙ Cargando evaluaciones de segmentos de calle...")
        segments_eval = self.parameterAsSource(parameters, self.SEGMENTS_EVAL, context)
        features_segments_eval = segments_eval.getFeatures()
        fieldnames_segments_eval = [field.name().upper() for field in segments_eval.fields()]
        lista_segments_eval = db.table_from_csv("emaps_segments_eval", fieldnames_segments_eval, 
                                                features_segments_eval)
        feedback.pushInfo("✔ Evaluaciones a Segmentos de calle cargadas: "+str(len(lista_segments_eval)))

        feedback.pushInfo("⚙ Cargando evaluaciones de lotes...")
        parcels_eval = self.parameterAsSource(parameters, self.PARCELS_EVAL, context)
        features_parcels_eval = parcels_eval.getFeatures()
        fieldnames_parcels_eval = [field.name().upper() for field in parcels_eval.fields()]
        lista_parcels_eval = db.table_from_csv("emaps_parcels_eval", fieldnames_parcels_eval, 
                                               features_parcels_eval)
        feedback.pushInfo("✔ Evaluaciones a Lotes cargadas: "+str(len(lista_parcels_eval)))

        feedback.setProgress(0)
        db.create_index()
        feedback.pushInfo("⚙ Calculando eMAPS Score...")
        emaps = EmapsScore(feedback, db, general_params, variables_especification)
        emaps.score()
        feedback.setProgress(99)

        feedback.pushInfo("✔ eMAPS Score calculado")

        feedback.pushInfo("⚙ Generando capas eMAPS-Score de salida...")
        segments_score = emaps.get_segments_output()
        self.dest_segments_score = self.join_layer_list(segments_geom, segment_id, segments_score, "segment_id", 
                             self.OUTPUT_SEGMENTS_SCORE, parameters, context, feedback )

        segments_score_proportion = emaps.get_segments_output_proportion()
        self.dest_segments_score_prop = self.join_layer_list(segments_geom, segment_id, segments_score_proportion, "segment_id", 
                             self.OUTPUT_SEGMENTS_SCORE_PROPORTION, parameters, context, feedback )

        areas_score = emaps.get_areas_output()
        self.dest_areas_score = self.join_layer_list(areas_geom, area_id, areas_score, "area_id", 
                             self.OUTPUT_AREAS_SCORE, parameters, context, feedback )

        areas_score_proportion = emaps.get_areas_output_proportion()
        self.dest_areas_score_prop = self.join_layer_list(areas_geom, area_id, areas_score_proportion, "area_id", 
                             self.OUTPUT_AREAS_SCORE_PROPORTION, parameters, context, feedback )
        
        feedback.pushInfo("✔ Capas de salida generadas")

        print("Time:", (time.time()-t))
        return {
                  self.OUTPUT_SEGMENTS_SCORE: self.dest_segments_score, 
                  self.OUTPUT_SEGMENTS_SCORE_PROPORTION: self.dest_segments_score_prop, 
                  self.OUTPUT_AREAS_SCORE: self.dest_areas_score,
                  self.OUTPUT_AREAS_SCORE_PROPORTION: self.dest_areas_score_prop
               }

    def postProcessAlgorithm(self, context, feedback):
        '''
            Here we can apply styles
        '''
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

        segments_score_prop_layer = QgsProcessingUtils.mapLayerFromString(self.dest_segments_score_prop, context)
        segments_score_prop_layer.loadNamedStyle(os.path.join(os.path.join(cmd_folder, 'styles/style_segment_score.qml')))
        segments_score_prop_layer.renderer().updateClasses(segments_score_prop_layer, segments_score_prop_layer.renderer().EqualInterval, 4)
        segments_score_prop_layer.triggerRepaint()

        segments_score_layer = QgsProcessingUtils.mapLayerFromString(self.dest_segments_score, context)
        segments_score_layer.loadNamedStyle(os.path.join(os.path.join(cmd_folder, 'styles/style_segment_score.qml')))
        segments_score_layer.renderer().updateClasses(segments_score_layer, segments_score_layer.renderer().EqualInterval, 4)
        segments_score_layer.triggerRepaint()

        try:
            areas_score_layer = QgsProcessingUtils.mapLayerFromString(self.dest_areas_score, context)
            areas_score_layer.loadNamedStyle(os.path.join(os.path.join(cmd_folder, 'styles/style_area_score.qml')))
            areas_score_layer.renderer().updateClasses(areas_score_layer, areas_score_layer.renderer().EqualInterval, 5)
            areas_score_layer.triggerRepaint()
        except:
            pass

        try:
            areas_score_prop_layer = QgsProcessingUtils.mapLayerFromString(self.dest_areas_score_prop, context)
            areas_score_prop_layer.loadNamedStyle(os.path.join(os.path.join(cmd_folder, 'styles/style_area_score.qml')))
            areas_score_prop_layer.renderer().updateClasses(areas_score_prop_layer, areas_score_prop_layer.renderer().EqualInterval, 5)
            areas_score_prop_layer.triggerRepaint()
        except:
            pass

        return {
                  self.OUTPUT_SEGMENTS_SCORE: self.dest_segments_score, 
                  self.OUTPUT_SEGMENTS_SCORE_PROPORTION: self.dest_segments_score_prop, 
                  self.OUTPUT_AREAS_SCORE: self.dest_areas_score,
                  self.OUTPUT_AREAS_SCORE_PROPORTION: self.dest_areas_score_prop
               }

    def join_layer_list(self, layer, layer_attribute, sql_list, list_attribute, output, parameters, context, feedback):
        '''
            Join layer with sql fetch result by attributes
        '''
        total = 100.0 / layer.featureCount() if layer.featureCount() else 0
        fieldnames = [field.name() for field in layer.fields()]
        features = layer.getFeatures()
        result_fields = layer.fields()
        list_fields = QgsFields()
        list_keys = []
        if len(sql_list) > 0:
            list_keys = sql_list[0].keys()
        for key in list_keys:
            new_field = QgsField(key, QVariant.Double)
            list_fields.append(new_field)
            result_fields.append(new_field)
        (sink, dest_id) = self.parameterAsSink(parameters, output, context, result_fields,
                                               layer.wkbType(), layer.sourceCrs()) 
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            attributes = feature.attributes()
            attributes_replaced_null = [None if a == qgis.core.NULL else a for a in attributes]
            lista_dict = dict(zip(fieldnames, attributes_replaced_null ))
            list_row = [x for x in sql_list if str(x[list_attribute]) == str(lista_dict[layer_attribute]) ]
            feature_result = None
            if len(list_row) > 0:
                feature_result = feature
                feature_result.setFields(result_fields)
                for field in list_fields:
                    try:
                        feature_result[field.name()] = list_row[0][field.name()]
                    except:
                        pass
                for field in layer.fields():
                    try:
                        feature_result[field.name()] = lista_dict[field.name()]
                    except:
                        pass
                sink.addFeature(feature_result, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))
        return dest_id

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Score eMAPS'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ''
    
    def icon(self):
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        icon = QIcon(os.path.join(os.path.join(cmd_folder, 'logo.png')))
        return icon

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return EmapsAlgorithm()
