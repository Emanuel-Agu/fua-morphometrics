# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         2.1.5. Road Network
#
# Purpose:      Preprocessing steps and spatio-temporal analysis to extract
#               spatio-temporal metrics from IndiFrag (available at: http://cgat.webs.upv.es/software/)
#               This code collects a selection of spatial metrics from IndiFrag.
##                  IndiFrag is a processing tool used for the extraction of a set of indices and
##                  variables that describe quantitatively the level of fragmentation and spatial
##                  distribution of land uses in response to morphological, spatial and typological properties of cartographic objects
#
#               The code belongs to the publication doi: https://doi.org/10.3390/ijgi9070436
#
#               Data required: https://www.globio.info/download-grip-dataset.
#
# Required libraries:   ARCPY, GDAL, NUMPY
#
# Author:       Marta Sapena (https://orcid.org/0000-0003-3283-319X)
#
# Created:     08/03/2018
# Copyright:   (c)
# Licence:     In all distribution of or public communications made concerning the code,
#              the authors shall always be cited. In any case of publishing results,
#              the only strict obligation is to acknowledge the origin and ownership
#              of the code IndiFrag-
#-------------------------------------------------------------------------------
import os, sys, subprocess,time
import arcpy
from arcpy.sa import *
import arcpy.da
import arcpy.cartography as CA
arcpy.CheckOutExtension("3D")
arcpy.env.overwriteOutput = True
import numpy as np

def road_dens(capa_road,areaSO):
    len_road = np.sum(row[0] for row in arcpy.da.SearchCursor(capa_road, "SHAPE@LENGTH"))/1000
    density = len_road/areaSO
    return density

try:
    s1 = time.clock()

    # Download data at: https://www.globio.info/download-grip-dataset.
    # set path of the unzipped folders accordingly
    path = "...\\GRIP\\"

    # Set path accordingly
    path_data = "...\\Data_Codes\\DATA\\"
    path_temp = path_data + "Output_spatio_temporal_analysis\\"

    fuas_pj = path_data + "Boundaries_OECD_EU\\Boundaries_4326.shp"
    out_vec = path_data + "Output_spatio_temporal_analysis\\ROADs\\"
    out_vecpj = path_data + "Output_spatio_temporal_analysis\\ROADs_PJ\\"
    path_data_fua = path_data + "Output_spatio_temporal_analysis\\FUAs\\"
    proj_utm = path_data + "UTM_Zones\\UTM_Zone_EPSG_4326.shp"

    dirs = [os.path.join(path_data + "Output_spatio_temporal_analysis\\", f ) for f in os.listdir(path_data + "Output_spatio_temporal_analysis\\")]

    for i in [out_vec,out_vecpj]:
        if i[:-1] not in dirs:
            os.makedirs(i)

    fuas = path_data + "Output_spatio_temporal_analysis\\Boundaries_ROADs.shp"
    arcpy.CopyFeatures_management(path_data + "Boundaries_OECD_EU\\Boundaries_3857.shp", fuas)

    arcpy.AddField_management(fuas, "AreaFUA", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "D_road", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

    arcpy.Exists(fuas)
    listaFua = [row for row in arcpy.da.SearchCursor(fuas_pj, ["fuacode_si","SHAPE@"], "fuacode_si <> 'FR030'")]
    listaRoad = [f for f in os.listdir(path) if f.endswith("_shp")]

    # LOOP TO READ EACH FUA
    for road in listaRoad:
        s2 = time.clock()
        for row in listaFua:
            supobjetos = "sel_fua"
            arcpy.MakeFeatureLayer_management(fuas, supobjetos, "fuacode_si = '%s'"%(row[0]))
            input_file = path + road + "\\" + [f for f in os.listdir(path + road + "\\") if f.endswith(".shp")][0]
            output_file = out_vec + "ROADS_%s_4326.shp"%(row[0])

            desc = arcpy.Describe(input_file)
            if row[1].extent.XMax <= desc.extent.XMax:
                if row[1].extent.XMin >= desc.extent.XMin:
                    if row[1].extent.YMax <= desc.extent.YMax:
                        if row[1].extent.YMin >= desc.extent.YMin:
                            print row[0]
                            arcpy.FeatureClassToFeatureClass_conversion(fuas_pj, path_temp,"seleccion.shp", "fuacode_si = '%s'"%(row[0]))
                            sel_fua = path_temp+"seleccion.shp"
                            arcpy.Intersect_analysis([sel_fua, input_file],output_file)
                            # PROJECT TO UTM
                            input_file = output_file
                            arcpy.FeatureToPoint_management(input_file, path_temp  + "pto.shp", "CENTROID")
                            arcpy.MakeFeatureLayer_management(proj_utm, "proj_utm")
                            arcpy.SelectLayerByLocation_management ("proj_utm", "intersect", path_temp  + "pto.shp")
                            epsg = [int(code[0]) for code in arcpy.da.SearchCursor("proj_utm", "EPSG")][0]
                            output_file = out_vecpj + "ROAD_%s_%s.shp"%(row[0],epsg)
                            subprocess.call('"C:\\Program Files (x86)\\GDAL\\ogr2ogr.exe" -f "ESRI Shapefile" -s_srs EPSG:4326 -t_srs EPSG:%s %s %s' %(epsg, output_file, input_file))
                            arcpy.Delete_management(path_temp  + "pto.shp")
                            arcpy.Delete_management("proj_utm")

                            # Road metrics
                            capa_road = output_file
                            # select the FUA layer created in step 1
                            capa_FUA = path_data_fua + [f for f in os.listdir(path_data_fua) if f.endswith(".shp") and f.startswith("FUA_%s_"%(row[0]))][0]

                            areaSO = np.sum(row[0] for row in arcpy.da.SearchCursor(capa_FUA, "SHAPE@AREA"))/1000000
                            arcpy.CalculateField_management (supobjetos, "AreaFUA", areaSO , "PYTHON")

                            #	Density of road network (D road)
                            dens_R = road_dens(capa_road,areaSO)
                            arcpy.CalculateField_management (supobjetos, "D_road", dens_R , "PYTHON")

                            arcpy.Delete_management(sel_fua)
                            arcpy.Delete_management(supobjetos)

                            print "Time %s min." %(round((time.clock()-s2)/60, 2))



except Exception as e:
    print e.message

finally:
    print "Total processing time %s min." %(round((time.clock()-s1)/60, 2))


