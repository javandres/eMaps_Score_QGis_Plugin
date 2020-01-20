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
import pyproj

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
                       QgsProcessingParameterRasterLayer,
                       QgsMessageLog,
                       QgsVectorLayer,
                       QgsProcessingUtils,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPointXY)
import processing
from processing.core.Processing import Processing

epsg4326 = QgsCoordinateReferenceSystem('EPSG:4326')

class EmapsPreprocessingAlgorithm(QgsProcessingAlgorithm):
    """
    eMAPS Pre processing Algorithm
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT_SEGMENTS= 'OUTPUT_SEGMENTS'
    OUTPUT_AREAS = 'OUTPUT_AREAS'

    SEGMENTS_GEOM = 'SEGMENTS_GEOM'
    AREAS_GEOM = 'AREAS_GEOM'

    dest_segments = None
    dest_areas = None

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

        self.addParameter(QgsProcessingParameterRasterLayer(
            'raster', 
            'Ráster DEM file', 
            defaultValue=None)
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_SEGMENTS,
                self.tr('OUTPUT: Segments eMAPS')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_AREAS,
                self.tr('OUTPUT: Areas eMAPS')
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """


        t = time.time()
        feedback.pushInfo("⚙ Cargando capa de áreas de estudio 🗺...")
        areas_geom = self.parameterAsSource(parameters, self.AREAS_GEOM, context)

        total = 100.0 / areas_geom.featureCount() if areas_geom.featureCount() else 0
        features = areas_geom.getFeatures()
        fieldnames = [field.name() for field in areas_geom.fields()]
        lista_areas = []
        (sink, self.dest_areas) = self.parameterAsSink(parameters, self.OUTPUT_AREAS, context, areas_geom.fields(),
                                               areas_geom.wkbType(), areas_geom.sourceCrs()) 
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            attributes = feature.attributes()
            attributes_replaced_null = [None if a == qgis.core.NULL else a for a in attributes]
            feedback.setProgress(int(current * total))
            lista_areas_dict = dict(zip(fieldnames, attributes_replaced_null ))
            lista_areas.append(lista_areas_dict)
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
           
        feedback.pushInfo("✔ Areas de estudio cargadas: "+str(len(lista_areas)))


            
        feedback.pushInfo("⚙ Cargando capa de segmentos de calle 🗺...")
        #segments_geom = self.parameterAsSource(parameters, self.SEGMENTS_GEOM, context)
        segments_geom = self.parameterAsVectorLayer(parameters, self.SEGMENTS_GEOM, context)

        raster_layer = self.parameterAsRasterLayer(parameters, "raster", context)
        
        result_z_value = processing.run("native:setzfromraster", {'BAND' : 1, 'INPUT' : segments_geom, 'NODATA' : 0, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'RASTER' : raster_layer, 'SCALE' : 1})

        result_z_stats = processing.run("native:extractzvalues", { 'COLUMN_PREFIX' : 'z_', 'INPUT' : result_z_value["OUTPUT"], 'OUTPUT' : 'TEMPORARY_OUTPUT', 'SUMMARIES' : [0,1,2] })["OUTPUT"]
        

        result_z_stats.dataProvider().addAttributes([QgsField("emaps_len", QVariant.Double)])
        result_z_stats.dataProvider().addAttributes([QgsField("emaps_slo", QVariant.Double)])
        result_z_stats.updateFields()
        result_z_stats.startEditing()

        total = 100.0 / result_z_stats.featureCount() if result_z_stats.featureCount() else 0
        (sink, self.dest_segmentos) = self.parameterAsSink(parameters, self.OUTPUT_SEGMENTS, context, result_z_stats.fields(),
                                        result_z_stats.wkbType(), result_z_stats.sourceCrs()) 

        for feature in result_z_stats.getFeatures():
            if feedback.isCanceled():
                break
            geom = feature.geometry()
            attributes = feature.attributes()
            feature.setFields(result_z_stats.fields())
            feature.setAttributes(attributes)
            emaps_length = round(geom.length(), 3)
            emaps_slope = round (  abs( feature["z_first"] - feature["z_last"] ) / emaps_length , 3)
            feature.setAttribute('emaps_len', emaps_length )
            feature.setAttribute('emaps_slo', emaps_slope)
            result_z_stats.updateFeature(feature)
            sink.addFeature(feature, QgsFeatureSink.FastInsert)
            
        result_z_stats.commitChanges()


        # segment_init_point = processing.run("qgis:extractspecificvertices", {"INPUT": segments_geom, "VERTICES":0, "OUTPUT":"init_point" })["OUTPUT"]
        # segment_final_point = processing.run("qgis:extractspecificvertices", {"INPUT": segments_geom, "VERTICES":-1, "OUTPUT":"final_point" })["OUTPUT"]

        # segment_init_layer = QgsProcessingUtils.mapLayerFromString(segment_init_point, context)
        # segment_final_layer = QgsProcessingUtils.mapLayerFromString(segment_final_point, context)

        # segment_init_point = processing.run('qgis:assignprojection', { "INPUT": segment_init_layer, "CRS":segments_geom.sourceCrs(), "OUTPUT": "memory3"})["OUTPUT"]
        # segment_final_point = processing.run('qgis:assignprojection', { "INPUT": segment_final_layer, "CRS":segments_geom.sourceCrs(), "OUTPUT": "memory4"})["OUTPUT"]

        # segment_init_layer = QgsProcessingUtils.mapLayerFromString(segment_init_point, context)
        # segment_final_layer = QgsProcessingUtils.mapLayerFromString(segment_final_point, context)

        # segment_init_point = processing.run('qgis:reprojectlayer', {"INPUT": segment_init_layer, 'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'), "OUTPUT": "memory5"})["OUTPUT"]
        # segment_final_point = processing.run('qgis:reprojectlayer', {"INPUT": segment_final_point, 'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:4326'), "OUTPUT": "memory6"})["OUTPUT"]

        # segment_init_layer_4326 = QgsProcessingUtils.mapLayerFromString(segment_init_point, context)
        # segment_final_layer_4326 = QgsProcessingUtils.mapLayerFromString(segment_final_point, context)

        # total = 100.0 / segments_geom.featureCount() if segments_geom.featureCount() else 0
        # features = segments_geom.getFeatures()
        # fieldnames = [field.name() for field in segments_geom.fields()]
        # lista_segmentos = []
        # (sink, self.dest_segmentos) = self.parameterAsSink(parameters, self.OUTPUT_SEGMENTS, context, segments_geom.fields(),
        #                                        segments_geom.wkbType(), segments_geom.sourceCrs()) 
        # for current, feature in enumerate(features):
        #     #self.get_vertices_list(segments_geom, feature)
        #     if feedback.isCanceled():
        #         break
        #     attributes = feature.attributes()
        #     attributes_replaced_null = [None if a == qgis.core.NULL else a for a in attributes]
        #     feedback.setProgress(int(current * total))
        #     lista_segmentos_dict = dict(zip(fieldnames, attributes_replaced_null ))
        #     lista_segmentos.append(lista_segmentos_dict)
        #     sink.addFeature(feature, QgsFeatureSink.FastInsert)
        # feedback.pushInfo("✔ Segmentos de calle cargados: "+str(len(lista_segmentos)))
        

        print("Time:", (time.time()-t))
        return {
                  self.OUTPUT_SEGMENTS: self.OUTPUT_SEGMENTS, 
                  self.OUTPUT_AREAS: self.dest_areas
               }

    def get_vertices_list(self, layer, feature):
        polilines = []
        if feature.geometry().isMultipart(): # new part for multipolylines
            multipolilines = feature.geometry().asMultiPolyline()
            for m in multipolilines:
                polilines.append(m)
            #print [len(v) for v in vertices]
        else:
            polilines = feature.geometry().asPolyline()
        
        init_point = polilines[0][0]
        final_point = polilines[0][len(polilines[0]) -1 ]
        for p in polilines:
            print(p)

        # vertices = feature.geometry().asPolyline()
        # points = []

        # for v in vertices:
        #     points.append(v)
        # return points    


    def get_geographic_xypoint(self, layer, xy_point, context):
        crsSrc = layer.sourceCrs()
        crsDest = QgsCoordinateReferenceSystem(4326)
        xform = QgsCoordinateTransform()
        xform.setDestinationCrs(crsDest)
        xform.setSourceCrs(crsSrc)
        pt = xform.transform(xy_point)
        return pt

        

    def postProcessAlgorithm(self, context, feedback):
        '''
            Here we can apply styles
        '''
        cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
        return {
                  self.OUTPUT_SEGMENTS: self.dest_segments, 
                  self.OUTPUT_AREAS: self.dest_areas
               }

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Pre-processing eMAPS'

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
        return EmapsPreprocessingAlgorithm()
