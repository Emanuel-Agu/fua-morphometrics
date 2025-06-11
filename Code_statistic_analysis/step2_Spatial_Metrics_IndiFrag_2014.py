# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         2.1.1. Global Human Settlement Layer (GHSL)
#                       Spatio-temporal analysis GHSL 2014
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
import arcpy
arcpy.env.overwriteOutput = True
import numpy as np
arcpy.CheckOutExtension("3D")

def Calc_Are_Per ( capa, nomare, nomper):
    arcpy.AddField_management( capa, nomare, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( capa, nomper, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.CalculateField_management( capa, nomare, "!shape.area!", "PYTHON_9.3")
    arcpy.CalculateField_management( capa, nomper, "!shape.length!", "PYTHON_9.3")
    return

try:
    s1 = time.clock()

    # Set path accordingly
    path_data = "...\\Data_Codes\\DATA\\"
    date=2014
    # Read boundaries and copy shape to save results
    proj_utm = path_data + "UTM_Zones\\UTM_Zone_EPSG_3857.shp"
    fuas = path_data + "Output_spatio_temporal_analysis\\Boundaries_SM_2014.shp"
    arcpy.CopyFeatures_management(path_data + "Boundaries_OECD_EU\\Boundaries_3857.shp", fuas)

    # Set path accordingly
    #Data source GHSL: https://doi.org/10.2905/jrc-ghsl-10007.
    input_ghsl ="...\\GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0\\V2-0\\GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0.vrt"

    # Create output folfers
    vec_3857 = path_data + "Output_spatio_temporal_analysis\\Vec_3857\\"
    out_ras_all = path_data + "Output_spatio_temporal_analysis\\Ras_3857\\"
    path_data_fua = path_data + "Output_spatio_temporal_analysis\\FUAs\\"
    out_vec = path_data + "Output_spatio_temporal_analysis\\Vec_14\\"
    out_ras = path_data + "Output_spatio_temporal_analysis\\Ras_14\\"
    dirs = [os.path.join(path_data + "Output_spatio_temporal_analysis\\", f ) for f in os.listdir(path_data + "Output_spatio_temporal_analysis\\")]

    for i in [out_vec,out_ras]:
        if i[:-1] not in dirs:
            os.makedirs(i)
    path_temp = path_data + "Output_spatio_temporal_analysis\\"
    arcpy.Exists(fuas)

    arcpy.AddField_management(fuas, "AreaFUA", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    # metrics for the built-up area
    arcpy.AddField_management(fuas, "UA_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "C_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "DI_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "AWSD_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "DU_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    # metrics for the urban core
    arcpy.AddField_management(fuas, "L_UC_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "C_UC_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "SL_UC_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "ER_UC_T2", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    #
    arcpy.AddField_management(fuas, "Clouds", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

    # LOOP TO READ EACH FUA

    listaFua = [str(row[0]) for row in arcpy.da.SearchCursor(fuas, "fuacode_si")]

    for fua in listaFua:
        cloud = 0
        s2 = time.clock()
        print fua

        # 1 - CLIP GHSL LANDSAT 30M WITH THE AOI - FUAs
        arcpy.FeatureClassToFeatureClass_conversion(fuas, path_data_fua, "FUA_%s.shp"%(fua), "fuacode_si = '%s'"%(fua))

        # 2- PROJECT THE BOUNDARY OF THE FUA TO UTM
        entrada = path_data_fua+ "FUA_%s.shp"%(fua)

        # look for the correct EPSG
        arcpy.FeatureToPoint_management(entrada, out_vec  + "pto.shp", "CENTROID")
        arcpy.MakeFeatureLayer_management(proj_utm, "proj_utm")
        arcpy.SelectLayerByLocation_management ("proj_utm", "intersect", out_vec  + "pto.shp")
        epsg = [int(code[0]) for code in arcpy.da.SearchCursor("proj_utm", "EPSG")][0]
        sel_fua = path_data_fua + "FUA_%s_%s.shp"%(fua,epsg)
        arcpy.Delete_management(path_data_fua+ "FUA_%s.shp"%(fua))
        arcpy.Delete_management(out_vec  + "pto.shp")
        arcpy.Delete_management("proj_utm")
        areaSO = np.sum(row[0] for row in arcpy.da.SearchCursor(sel_fua, "SHAPE@AREA"))/1000000

        output_all = out_ras_all + "BUILT_%s_3857.tif"%(fua)

        n_null = [code[0] for code in arcpy.da.SearchCursor(output_all, "count", "value = 0")]
        if len(n_null) > 0:
            n_total = sum([code[0] for code in arcpy.da.SearchCursor(output_all, "count")])
            cloud = n_null[0]*100/n_total

        if cloud < 1:
            output = out_ras + "BUILT_%s_%s_3857.tif"%(fua,date)

            # 3 - RECLASSIFY TO GET A BUILT-UP MAP FOR THE YEAR 2014
            arcpy.gp.Reclassify_sa(output_all, "Value", "0 NODATA;1 NODATA;2 NODATA;3 1;4 1;5 1;6 1", output, "DATA")

            n_pixels = [code[0] for code in arcpy.da.SearchCursor(output, "count")][0]

            # 4- CONVER RASTER DATA TO VECTOR
            input_ghsl = output
            output = vec_3857 + "BUILT_%s_%s_3857.shp"%(fua,date)
            name = "BUILT_%s_%s_3857"%(fua,date)
            subprocess.call('"C:\\Program Files (x86)\\GDAL\\gdal_polygonize.py" %s -f "ESRI Shapefile" %s' %(input_ghsl, output),shell=True)

            # 5 - PROJECT TO UTM
            input_ghsl = output
            output = out_vec + "BUILT_%s_%s_%s.shp"%(fua,date,epsg)
            subprocess.call('"C:\\Program Files (x86)\\GDAL\\ogr2ogr.exe" -f "ESRI Shapefile" -s_srs EPSG:3857 -t_srs EPSG:%s %s %s' %(epsg, output, input_ghsl))

            # 6 - SPATIAL METRICS FROM INDIFRAG for the BUILT-UP AREA
            arcpy.MakeFeatureLayer_management(fuas, "sel_fua", "fuacode_si = '%s'"%(fua))
            supobjetos = "sel_fua"
            objetos = output

            arcpy.CalculateField_management (supobjetos, "Clouds", cloud , "PYTHON")
            arcpy.CalculateField_management (supobjetos, "AreaFUA", areaSO , "PYTHON")

            Calc_Are_Per(objetos, "Area", "Perim")

            areaU = np.sum(fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@AREA"))
            perimU = np.sum(fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@LENGTH"))
            cont1 =  int(str(arcpy.GetCount_management(objetos)))

            # Urban area (UA)
            arcpy.CalculateField_management (supobjetos, "UA_T2", areaU/1000000 , "PYTHON")
            arcpy.CalculateField_management (supobjetos, "DU_T2", (areaU/1000000)/areaSO*100 , "PYTHON")

            # Normalized area-weighted standard distance (AWSD)
            arcpy.StandardDistance_stats( objetos, out_vec  + "sdist.shp", "1_STANDARD_DEVIATION", "Area")
            distEstSO = [fila[0] for fila in arcpy.da.SearchCursor( out_vec  + "sdist.shp", "StdDist")][0]
            arcpy.Delete_management(out_vec  + "sdist.shp")
            # normalization with the "maximum distance"
            lado = 2000
            desc = arcpy.Describe(sel_fua)
            netw = arcpy.CreateFishnet_management(path_temp + "grid.shp",str(desc.extent.lowerLeft),str(desc.extent.XMin) + " " + str(desc.extent.YMax + lado),lado,lado,"0","0","%s %s Nan Nan"%(desc.extent.upperRight.X+lado, desc.extent.upperRight.Y+lado), "LABELS",sel_fua,"POLYLINE")
            arcpy.Intersect_analysis([path_temp + "grid_label.shp", sel_fua], path_temp + "grid_sel.shp", "")
            arcpy.Delete_management(path_temp + "grid.shp")
            arcpy.Delete_management(path_temp + "grid_label.shp")
            arcpy.StandardDistance_stats( path_temp + "grid_sel.shp", path_temp  + "SD_grid.shp", "1_STANDARD_DEVIATION")
            DS_max = [fila[0] for fila in arcpy.da.SearchCursor(path_temp  + "SD_grid.shp", "StdDist")][0]
            arcpy.Delete_management(path_temp + "grid_sel.shp")
            arcpy.Delete_management(path_temp  + "SD_grid.shp")
            arcpy.CalculateField_management( supobjetos, "AWSD_T2", (distEstSO*100/DS_max), "PYTHON_9.3")

            # Urban compactness (CU)
            compac = (2*math.sqrt(math.pi*areaU))/perimU
            arcpy.CalculateField_management (supobjetos, "C_T2", compac*100, "PYTHON")

            #Dispersion index (DI)
            Amax = np.amax([(fila[0],fila[1]) for fila in arcpy.da.SearchCursor(objetos, ["SHAPE@AREA","SHAPE@LENGTH"])], axis=0)
            Lpi = Amax[0]/areaU*100
            form_DI = ((((cont1-1)/(n_pixels-1))*100) +(100-Lpi))/2
            arcpy.CalculateField_management (supobjetos, "DI_T2", form_DI , "PYTHON")

            # 7 - SPATIAL METRICS FROM INDIFRAG for the URBAN CORE
            if not arcpy.ListFields(objetos, "UMZ"):
                arcpy.AddField_management(objetos, "UMZ", "SHORT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

            # seleccionar el Largest Patch
            Amax = np.max([fila[0] for fila in arcpy.da.SearchCursor(objetos, "Area")])
            arcpy.MakeFeatureLayer_management(objetos, "lpi", "Area = %s"%(Amax))
            arcpy.CopyFeatures_management("lpi", path_temp+"umz.shp")

            # loop to select the patches in 200 meters from the LP. Urban Morphological Zone can be defined as “A set of urban areas laying less than 200m apart”
            arcpy.MakeFeatureLayer_management(objetos, "selec_umz")
            for i in range(0,3):
                arcpy.SelectLayerByLocation_management(in_layer="selec_umz", overlap_type="WITHIN_A_DISTANCE", select_features=path_temp+"umz.shp", search_distance="200 Meters", selection_type="ADD_TO_SELECTION", invert_spatial_relationship="NOT_INVERT")
                arcpy.CopyFeatures_management("selec_umz", path_temp+"umz.shp")

            arcpy.CalculateField_management ("selec_umz", "UMZ", 1 , "PYTHON")

            # Area of the urban core
            A_UMZ = np.sum([fila[0] for fila in arcpy.da.SearchCursor("selec_umz", "Area")])

            # Elongation ratio (ER_UC) for the Largest urban core
            arcpy.MinimumBoundingGeometry_management("selec_umz", path_temp+"lpi_MBG.shp", geometry_type="RECTANGLE_BY_WIDTH", group_option="ALL", group_field="", mbg_fields_option="MBG_FIELDS")
            lados = [(fila[0],fila[1]) for fila in arcpy.da.SearchCursor(path_temp+"lpi_MBG.shp", ["MBG_Width","MBG_Length"])][0]
            diamArea = 2*(math.sqrt(A_UMZ/math.pi))
            arcpy.CalculateField_management (supobjetos, "ER_UC_T2", diamArea/lados[1] , "PYTHON")

            # compactness (C_UC) for the Largest urban core
            PerUMZ = np.sum([fila[0] for fila in arcpy.da.SearchCursor("selec_umz", "Perim")])
            c_UMZ = (2*math.sqrt(math.pi*A_UMZ))/PerUMZ
            arcpy.CalculateField_management (supobjetos, "C_UC_T2", c_UMZ*100 , "PYTHON")

            # Largest the urban core (L_UC)
            LP_umz = A_UMZ/areaU*100
            arcpy.CalculateField_management (supobjetos, "L_UC_T2", LP_umz , "PYTHON")

            # Second largest urban core (SL_UC)
            Amax2nd = np.max([fila[0] for fila in arcpy.da.SearchCursor(objetos, "Area", "UMZ <> 1")])
            arcpy.MakeFeatureLayer_management(objetos, "lpi2nd", "Area = %s"%(Amax2nd))
            arcpy.CopyFeatures_management("lpi2nd", path_temp+"umz2.shp")

            arcpy.MakeFeatureLayer_management(objetos, "selec_umz2")
            for i in range(0,3):
                arcpy.SelectLayerByLocation_management(in_layer="selec_umz2", overlap_type="WITHIN_A_DISTANCE", select_features=path_temp+"umz2.shp", search_distance="200 Meters", selection_type="ADD_TO_SELECTION", invert_spatial_relationship="NOT_INVERT")
                arcpy.CopyFeatures_management("selec_umz2", path_temp+"umz2.shp")

            arcpy.CalculateField_management ("selec_umz2", "UMZ", 2 , "PYTHON")

            A_UMZ2 = np.sum([fila[0] for fila in arcpy.da.SearchCursor("lpi2nd", "Area")])

            LP2_umz = A_UMZ2/areaU*100
            arcpy.CalculateField_management (supobjetos, "SL_UC_T2", LP2_umz , "PYTHON")


            # delete temporal datasets
            arcpy.Delete_management(supobjetos)
            arcpy.Delete_management("LUCob")

            arcpy.Delete_management(path_temp+"lpi_MBG.shp")
            arcpy.Delete_management("lpi")
            arcpy.Delete_management("selec_umz")
            arcpy.Delete_management("selec_umz2")
            arcpy.Delete_management("lpi2nd")
            arcpy.Delete_management(path_temp+"umz.shp")
            arcpy.Delete_management(path_temp+"umz2.shp")
            print "Time %s min." %(round((time.clock()-s2)/60, 2))

        if cloud > 1:
            arcpy.MakeFeatureLayer_management(fuas, "sel_fua", "fuacode_si = '%s'"%(fua))
            supobjetos = "sel_fua"
            arcpy.CalculateField_management (supobjetos, "Clouds", cloud , "PYTHON")

except Exception as e:
    print e.message

finally:
    print "Total processing time %s min." %(round((time.clock()-s1)/60, 2))


