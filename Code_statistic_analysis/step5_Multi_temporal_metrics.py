# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         2.1.1. Global Human Settlement Layer (GHSL)
#                      Multi-temporal metrics (2000-2014)
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
#               Data required: https://doi.org/10.2905/jrc-ghsl-10007.
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
import numpy as np
from arcpy.sa import *
import arcpy.da
import arcpy.cartography as CA
arcpy.CheckOutExtension("3D")
import time
arcpy.env.overwriteOutput = True

def Calc_Are_Per ( capa, nomare, nomper):
    arcpy.AddField_management( capa, nomare, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( capa, nomper, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.CalculateField_management( capa, nomare, "!shape.area!", "PYTHON_9.3")
    arcpy.CalculateField_management( capa, nomper, "!shape.length!", "PYTHON_9.3")
    return

def Clasif_growth(capa, name):
    arcpy.PolygonToLine_management(capa, out_vec + "line.shp","IDENTIFY_NEIGHBORS")
    arcpy.AddField_management(capa, "LEI", "DOUBLE", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.CalculateField_management( capa, "LEI", 0, "PYTHON")
    arcpy.AddField_management(capa, "Growth_t", "TEXT", 20)
    arcpy.CalculateField_management( capa, "Growth_t", "''", "PYTHON")
    arcpy.AddField_management(out_vec + "line.shp", "longitud","DOUBLE", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.CalculateField_management( out_vec + "line.shp", "longitud", "!shape.length!", "PYTHON")
    arcpy.AddField_management(capa, "lon_col","DOUBLE", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.MakeFeatureLayer_management (out_vec + "line.shp" , "sel_lines", "LEFT_FID = -1")
    arcpy.Statistics_analysis ("sel_lines", out_vec + "stat1", [["longitud", "SUM"]],"RIGHT_FID")
    arcpy.MakeFeatureLayer_management ( capa, "selecc")
    arcpy.AddJoin_management( "selecc", "FID", out_vec + "stat1", "RIGHT_FID")
    arcpy.SelectLayerByAttribute_management("selecc", "NEW_SELECTION", "%s.Temp_Class = 'New' AND stat1:FID IS NOT NULL"%(name))
    arcpy.CalculateField_management( "selecc", "%s.lon_col"%(name), "!stat1:SUM_LONGITUD!", "PYTHON")
    arcpy.Delete_management("selecc")
    arcpy.Delete_management(out_vec + "line.shp")
    arcpy.Delete_management(out_vec + "stat1")
    #  calcular los campos
    arcpy.MakeFeatureLayer_management (capa, "new", "Temp_Class = 'New'")
    arcpy.CalculateField_management( "new", "LEI", "(!shape.length!-!lon_col!)/!shape.length!", "PYTHON")
    arcpy.MakeFeatureLayer_management (capa, "out", "LEI < 0.0001 AND Temp_Class = 'New'")
    arcpy.MakeFeatureLayer_management (capa, "edg", "LEI <= 0.499 AND LEI >= 0.0001 AND Temp_Class = 'New'")
    arcpy.MakeFeatureLayer_management (capa, "inf", "LEI > 0.499 AND Temp_Class = 'New'")
    arcpy.CalculateField_management( "inf","Growth_t", "'Infilling'", "PYTHON")
    arcpy.CalculateField_management( "edg","Growth_t", "'Edge-Expansive'", "PYTHON")
    arcpy.CalculateField_management( "out","Growth_t", "'Outlying'", "PYTHON")
    arcpy.Delete_management("new")
    arcpy.Delete_management("inf")
    arcpy.Delete_management("edg")
    arcpy.Delete_management("out")
    arcpy.Delete_management("sel_lines")

    #corregir los que tocan solo una esquina
    arcpy.MakeFeatureLayer_management (capa , "outly", "Growth_t = 'Outlying'")
    arcpy.MakeFeatureLayer_management (capa , "newly", "Temp_Class = 'Unchanged' OR Growth_t = 'Edge-Expansive' OR Growth_t = 'Infilling'")
    arcpy.Intersect_analysis(["newly", "outly"], out_vec + "int_esqui.shp","ONLY_FID","#","POINT")
    arcpy.Delete_management("newly")
    arcpy.Delete_management("outly")
    lista_esq = [low[0] for low in arcpy.da.SearchCursor(out_vec + "int_esqui.shp", "FID_BUILT1")]
    if len(lista_esq) > 1:
        query= "FID IN {0}".format(str(tuple(lista_esq)))
        arcpy.MakeFeatureLayer_management (capa , "esq", query)
        arcpy.CalculateField_management( "esq", "Growth_t", "'Edge-Expansive'", "PYTHON")
        arcpy.Delete_management("esq")
    arcpy.Delete_management(out_vec + "int_esqui.shp")
    return

# comprobar los fid habra que cambiarlos

def Clas_Fecha (capa):
    arcpy.AddField_management(capa, "Temp_Class", "TEXT", 20)
    arcpy.MakeFeatureLayer_management (capa , "Obj_Class", "FID_BUILT_ <> -1 AND FID_BUILT1 = -1")
    arcpy.CalculateField_management( "Obj_Class", "Temp_Class", "'Lost'", "PYTHON")
    arcpy.MakeFeatureLayer_management (capa, "Obj_Class",  "FID_BUILT_ = -1 AND FID_BUILT1 <> -1")
    arcpy.CalculateField_management( "Obj_Class", "Temp_Class", "'New'", "PYTHON")
    arcpy.MakeFeatureLayer_management (capa, "Obj_Class", "FID_BUILT_ <> -1 AND FID_BUILT1 <> -1")
    arcpy.CalculateField_management( "Obj_Class", "Temp_Class", "'Unchanged'", "PYTHON")
    arcpy.Delete_management("Obj_Class")
    return

def Accessibility(capa_out,capa_adj,capa_road,areaN, cntN):
    arcpy.SpatialJoin_analysis(capa_out,capa_road, path_data + "dist_road.shp","JOIN_ONE_TO_ONE","KEEP_ALL","#","CLOSEST","#","D_ROAD")
    distW_out = np.sum( ((row[1]*100)/((row[0] + 1)*areaN)) for row in arcpy.da.SearchCursor(path_data + "dist_road.shp", ("D_ROAD", "SHAPE@AREA")))
    distW_adj = np.sum( ((row[0]*100)/areaN) for row in arcpy.da.SearchCursor(capa_adj, "SHAPE@AREA"))
    awmai = (distW_out+distW_adj)
    arcpy.Delete_management(path_data + "dist_road.shp")
    return awmai

def cleanlayer(capa):
    arcpy.DeleteField_management(capa, "Growth_t")
    arcpy.DeleteField_management(capa, "LEI")

try:
    s1 = time.clock()

    # Set path accordingly
    path_data = "...\\Data_Codes\\DATA\\"

    path_temp = path_data + "Output_spatio_temporal_analysis\\"

    fuas = path_data + "Output_spatio_temporal_analysis\\Boundaries_MT_2000_2014.shp"
    arcpy.CopyFeatures_management(path_data + "Boundaries_OECD_EU\\Boundaries_3857.shp", fuas)

    inp_vecT1 = path_data + "Output_spatio_temporal_analysis\\Vec_00\\"
    inp_vecT2 = path_data + "Output_spatio_temporal_analysis\\Vec_14\\"
    out_vec = path_data + "Output_spatio_temporal_analysis\\Vec_00_14\\"
    inp_road = path_data + "Output_spatio_temporal_analysis\\ROADs_PJ\\"

    dirs = [os.path.join(path_data + "Output_spatio_temporal_analysis\\", f ) for f in os.listdir(path_data + "Output_spatio_temporal_analysis\\")]
    if out_vec[:-1] not in dirs:
        os.makedirs(out_vec)

    arcpy.AddField_management(fuas, "UCR", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "AWMEI", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "AWMAI", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

    # 1 - CALCULAR LAS METRICAS MUTLITEMPORALES

    arcpy.Exists(fuas)
    listaFua = [str(row[0]) for row in arcpy.da.SearchCursor(fuas, "fuacode_si")]

    # LOOP TO READ EACH FUA
    for fua in listaFua:
        arcpy.Delete_management("in_memory")
        s2 = time.clock()
        print fua
        supobjetos = "sel_fua"
        arcpy.MakeFeatureLayer_management(fuas,supobjetos, "fuacode_si = '%s'"%(fua))

        capa1 = inp_vecT1 + [f for f in os.listdir(inp_vecT1) if f.endswith(".shp") and f.startswith("BUILT_%s_"%(fua))][0]
        capa2 = inp_vecT2 + [f for f in os.listdir(inp_vecT2) if f.endswith(".shp") and f.startswith("BUILT_%s_"%(fua))][0]

        # CREATE CHANGE MAP and clasify into NEW/OLD
        objetos = out_vec + "BUILT_%s_00_14.shp"%(fua)
        arcpy.Union_analysis ([capa1, capa2], out_vec + "union.shp", "ALL")
        arcpy.MultipartToSinglepart_management(out_vec + "union.shp",objetos)
        arcpy.Delete_management(out_vec + "union.shp")
        arcpy.DeleteField_management(objetos ,"Area")
        arcpy.DeleteField_management(objetos ,"Perim")
        arcpy.DeleteField_management(objetos ,"Area_1")
        arcpy.DeleteField_management(objetos ,"Perim_1")
        Calc_Are_Per(objetos, "Area", "Perim")
        Clas_Fecha(objetos)

        # MULTI-TEMPORAL METRICS INDIFRAG
        areaT1 = np.sum(fila[0] for fila in arcpy.da.SearchCursor(capa1, "SHAPE@AREA"))
        areaT2 = np.sum(fila[0] for fila in arcpy.da.SearchCursor(capa2, "SHAPE@AREA"))
        arcpy.MakeFeatureLayer_management(objetos, "Sel_new", "Temp_Class = 'New' AND Area > 100")
        areaN = np.sum(fila[0] for fila in arcpy.da.SearchCursor("Sel_new", "SHAPE@AREA"))

        #	Urban change rate (UCR)
        arcpy.CalculateField_management( supobjetos, "UCR", ((areaT2-areaT1)/areaT1)*100 , "PYTHON")

        # 	Area-weighted mean expansion index (AWMEI)
        Clasif_growth(objetos, "BUILT_%s_00_14"%(fua))
        sumaAWLEI= np.sum([(fila[1] * (fila[0]/areaN)* 100) for fila in arcpy.da.SearchCursor("Sel_new",["SHAPE@AREA", "LEI"])])
        arcpy.CalculateField_management (supobjetos, "AWMEI", (sumaAWLEI) , "PYTHON")

        #	Area-weighted mean accessibility index (AWMAI)
        contnew = int(str(arcpy.GetCount_management("Sel_new")))
        if contnew <> 0:
            capa_road = inp_road + [f for f in os.listdir(inp_road) if f.endswith(".shp") and fua in f][0]
            arcpy.FeatureClassToFeatureClass_conversion(objetos, path_data, "Sel_out.shp", "Growth_t = 'Outlying' AND Area > 100")
            arcpy.FeatureClassToFeatureClass_conversion(objetos, path_data, "Sel_adj.shp", "Temp_Class = 'New' AND Growth_t <> 'Outlying' AND Area > 100")
            awmai1 = Accessibility(path_data+"Sel_out.shp", path_data+"Sel_adj.shp",capa_road, areaN, contnew)
            arcpy.CalculateField_management (supobjetos, "AWMAI", awmai1 , "PYTHON")
            arcpy.Delete_management(path_data+"Sel_out.shp")
            arcpy.Delete_management(path_data+"Sel_adj.shp")

        cleanlayer(objetos)
        arcpy.Delete_management("Sel_new")

        print "Time %s min." %(round((time.clock()-s2)/60, 2))

except Exception as e:
    print e.message

finally:
    print "Total processing time %s min." %(round((time.clock()-s1)/60, 2))


