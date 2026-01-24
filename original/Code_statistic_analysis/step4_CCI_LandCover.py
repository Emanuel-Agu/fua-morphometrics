# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         2.1.4. Climate Change Initiative Land Cover
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
#               Data required: ftp://anon-ftp.ceda.ac.uk/neodc/esacci/.
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

try:
    s1 = time.clock()

    # Set path accordingly
    path_data = "...\\Data_Codes\\DATA\\"

    path_temp = path_data + "Output_spatio_temporal_analysis\\"

    # Set path accordingly
    #Data source ftp://anon-ftp.ceda.ac.uk/neodc/esacci/
    input_cci ="...\\ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7\\scratch\\ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7.tif"

    # Set path accordingly
    # create one layer per year
    LC_cci_00 = "...\\ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7\\CCI_LC_2000.tif"
    LC_cci_14 = "...\\ESACCI-LC-L4-LCCS-Map-300m-P1Y-1992_2015-v2.0.7\\CCI_LC_2014.tif"

    # Export from the bands the Land cover for years 2000 and 2014
    subprocess.call('"C:\\Program Files (x86)\\GDAL\\gdal_translate.exe" -b 9 %s %s' %(input_cci, LC_cci_00))
    subprocess.call('"C:\\Program Files (x86)\\GDAL\\gdal_translate.exe" -b 23 %s %s' %(input_cci, LC_cci_14))

    dates_list =(2000,2014)
    raster_cci = (LC_cci_00,LC_cci_14)

    # Create output folfers
    fuas_pj = path_data + "Boundaries_OECD_EU\\Boundaries_4326.shp"
    ras_4326 = path_data + "Output_spatio_temporal_analysis\\CCI_4326\\"
    out_vec = path_data + "Output_spatio_temporal_analysis\\CCI_4326\\"
    out_vec_pj = path_data + "Output_spatio_temporal_analysis\\Vec_CCI\\"
    path_data_fua = path_data + "Output_spatio_temporal_analysis\\FUAs\\"

    proj_utm = path_data + "UTM_Zones\\UTM_Zone_EPSG_4326.shp"

    dirs = [os.path.join(path_data + "Output_spatio_temporal_analysis\\", f ) for f in os.listdir(path_data + "Output_spatio_temporal_analysis\\")]

    for i in [ras_4326,out_vec_pj]:
        if i[:-1] not in dirs:
            os.makedirs(i)

    fuas = path_data + "Output_spatio_temporal_analysis\\Boundaries_CCI_LC.shp"
    arcpy.CopyFeatures_management(path_data + "Boundaries_OECD_EU\\Boundaries_3857.shp", fuas)

    for i in [1,2,3,4,5,6,7]:
        arcpy.AddField_management(fuas, "D_LC%s_T1"%(i), "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
        arcpy.AddField_management(fuas, "D_LC%s_T2"%(i), "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
        arcpy.AddField_management(fuas, "CP_LC%s"%(i), "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

    # LOOP TO READ EACH FUA
    arcpy.Exists(fuas_pj)

    listaFua = [str(row[0]) for row in arcpy.da.SearchCursor(fuas_pj, "fuacode_si")]

    for fua in listaFua:
        s2 = time.clock()
        print fua
        supobjetos = "sel_fua"
        arcpy.MakeFeatureLayer_management(fuas, supobjetos, "fuacode_si = '%s'"%(fua))

        for date in [0,1]:
            # 1 - CLIP CCI_LC ESA 300M WITH THE AOI - FUAs
            arcpy.FeatureClassToFeatureClass_conversion(fuas_pj, path_temp,"seleccion.shp", "fuacode_si = '%s'"%(fua))
            sel_fua = path_temp +"seleccion.shp"
            entrada = raster_cci[date]
            output = ras_4326 + "CCI_%s_%s_4326.tif"%(fua,dates_list[date])
            subprocess.call('"C:\\Program Files (x86)\\GDAL\\gdalwarp.exe" -s_srs EPSG:4326 -t_srs EPSG:4326 -cutline %s -crop_to_cutline %s %s' %(sel_fua, entrada, output))

            reclass = ras_4326 + "LC_%s_%s_4326.tif"%(fua,dates_list[date])
            # 2 - RECLASSISY THE LEGEND
            arcpy.gp.Reclassify_sa(output, "Value", "10 30 1;40 100 2;110 153 3;160 180 2;190 4;200 202 5;210 6;220 7", reclass, "DATA")

            # 3 - CONVER RASTER DATA TO VECTOR
            entrada = reclass
            output = out_vec + "CCI_%s_%s_4326.shp"%(fua,dates_list[date])
            name = "CCI_%s_%s_4326"%(fua,dates_list[date])
            subprocess.call('"C:\\Program Files (x86)\\GDAL\\gdal_polygonize.py" %s -f "ESRI Shapefile" %s %s' %(entrada, output, name), shell=True)

            # 4 - PROJECT TO UTM
            entrada = output
            # buscar el epsg
            arcpy.FeatureToPoint_management(sel_fua, path_temp  + "pto.shp", "CENTROID")
            arcpy.MakeFeatureLayer_management(proj_utm, "proj_utm")
            arcpy.SelectLayerByLocation_management ("proj_utm", "intersect", path_temp  + "pto.shp")
            epsg = [code[0] for code in arcpy.da.SearchCursor("proj_utm", "EPSG")][0]
            sr = arcpy.SpatialReference(epsg)
            output = out_vec_pj + "CCI_%s_%s_%s.shp"%(fua,dates_list[date],epsg)
            subprocess.call('"C:\\Program Files (x86)\\GDAL\\ogr2ogr.exe" -f "ESRI Shapefile" -s_srs EPSG:4326 -t_srs EPSG:%s %s %s' %(epsg, output, entrada))
            arcpy.Delete_management(path_temp  + "pto.shp")
            arcpy.Delete_management("proj_utm")

            # 6 - SPATIAL METRICS FROM INDIFRAG for the BUILT-UP AREA
            CCI_layer = output
            capa_FUA = path_data_fua + [f for f in os.listdir(path_data_fua) if f.endswith(".shp") and f.startswith("FUA_%s_"%(fua))][0]
            areaSO = np.sum(row[0] for row in arcpy.da.SearchCursor(capa_FUA, "SHAPE@AREA"))/1000000

            for i in [1,2,3,4,5,6,7]:
                area_LC = np.sum(row[0] for row in arcpy.da.SearchCursor(CCI_layer, "SHAPE@AREA","DN = %s"%(i)))/1000000.0
                if dates_list[date] == 2000:
                    arcpy.CalculateField_management( supobjetos,  "D_LC%s_T1"%(i), (area_LC/areaSO*100) , "PYTHON")
                if dates_list[date] == 2014:
                    arcpy.CalculateField_management( supobjetos,  "D_LC%s_T2"%(i), (area_LC/areaSO*100) , "PYTHON")

        for i in [1,2,3,4,5,6,7]:
            area_T1 = np.sum(row[0] for row in arcpy.da.SearchCursor(out_vec_pj + "CCI_%s_2000_%s.shp"%(fua,epsg), "SHAPE@AREA","DN = %s"%(i)))/1000000.0
            area_T2 = np.sum(row[0] for row in arcpy.da.SearchCursor(out_vec_pj + "CCI_%s_2014_%s.shp"%(fua,epsg), "SHAPE@AREA","DN = %s"%(i)))/1000000.0
            arcpy.CalculateField_management( supobjetos,  "CP_LC%s"%(i), ((area_T2-area_T1)/areaSO*100) , "PYTHON")


        arcpy.Delete_management(sel_fua)
        print "Time %s min." %(round((time.clock()-s2)/60, 2))


except Exception as e:
    print e.message

finally:
    print "Total processing time %s min." %(round((time.clock()-s1)/60, 2))

