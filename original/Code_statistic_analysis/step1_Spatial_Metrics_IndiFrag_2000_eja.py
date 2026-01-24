# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         2.1.1. Global Human Settlement Layer (GHSL)
#                       Spatio-temporal analysis GHSL 2000
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

import os, sys, subprocess, time
import arcpy
import numpy as np
import math

# Import GDAL from the Python that is on ArcGIS Pro
from osgeo import gdal, ogr, osr, gdal_array, gdalconst    
help(gdal.Polygonize)

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("3D")

# 1. Install GDAL and change the paths accordingly
# 2. Instruct the compiler where is tms_NZTM2000.json
# Ensure that the GDAL_DATA environment variable is correctly set before any GDAL utilities are called.
# Replace "json_dir" with the actual path to the directory containing tms_NZTM2000.json.
json_dir = r"C:\\Program Files\\GDAL\\gdal-data"

# Check if GDAL_DATA is already set and append the json directory to it
if 'GDAL_DATA' in os.environ:
    os.environ['GDAL_DATA'] += os.pathsep + json_dir
else:
    os.environ['GDAL_DATA'] = json_dir

os.environ['PROJ_LIB'] = os.path.join(r'C:\\Program Files\\GDAL\\projlib')

def Calc_Are_Per (capa, nomare, nomper):
    arcpy.AddField_management( capa, nomare, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management( capa, nomper, "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.CalculateField_management( capa, nomare, "!shape.area!", "PYTHON_9.3")
    arcpy.CalculateField_management( capa, nomper, "!shape.length!", "PYTHON_9.3")
    return

try:
    s1 = time.perf_counter()

    # Set path accordingly
    path_data = ".../Data_Codes/DATA/"
    print(path_data)

    date=2000

    # Read boundaries and copy shape to save results
    proj_utm = "E:\\Sapena_2020\\Data_Codes\\DATA\\UTM_Zones\\UTM_Zone_EPSG_3857.shp"
    fuas = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\Boundaries_SM_2000.shp"
    print(fuas)
    arcpy.CopyFeatures_management("E:\\Sapena_2020\\Data_Codes\\DATA\\Boundaries_OECD_EU\\Boundaries_3857.shp", fuas)
    
    # Set path accordingly
    # Data source GHSL: https://doi.org/10.2905/jrc-ghsl-10007.
    input_ghsl = "E:\\Sapena_2020\\Data_Codes\\DATA\\GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0\\V2-0\\GHS_BUILT_LDSMT_GLOBE_R2018A_3857_30_V2_0.vrt"
    
    # Create output folfers
    vec_3857 = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\Vec_3857\\"
    out_ras_all = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\Ras_3857\\"
    path_data_fua = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\FUAs\\"
    out_vec = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\Vec_00\\"
    out_ras = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\Ras_00\\"
    dirs = [os.path.join("E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\", f ) for f in os.listdir("E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\")]

    for i in [vec_3857, out_ras_all, path_data_fua, out_vec, out_ras]:
        if i[:-1] not in dirs:
            os.makedirs(i)
    path_temp = "E:\\Sapena_2020\\Data_Codes\\DATA\\Output_spatio_temporal_analysis\\"
    arcpy.Exists(fuas)

    arcpy.AddField_management(fuas, "AreaFUA", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    # metrics for the built-up area
    arcpy.AddField_management(fuas, "UA_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "C_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "DI_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "AWSD_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "DU_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    # metrics for the urban core
    arcpy.AddField_management(fuas, "L_UC_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "C_UC_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "SL_UC_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    arcpy.AddField_management(fuas, "ER_UC_T1", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")
    # Clouds
    arcpy.AddField_management(fuas, "Clouds", "FLOAT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

    # LOOP TO READ EACH FUA"
    #listaFua = [str(row[0]) for row in arcpy.da.SearchCursor(fuas, "fuacode_si")]
    listaFua = [str(row[0]) for row in arcpy.da.SearchCursor(fuas, "fuacode_si") if str(row[0]).startswith("USA")]

    # Print the list of FUAs
    #print("List of FUAs:", listaFua)

    for fua in listaFua:
        cloud = 0
        s2 = time.perf_counter()
        print("FUA: ", fua)
        print("")

        print("# 1 - CLIP GHSL LANDSAT 30M WITH THE AOI - FUAs")
        arcpy.FeatureClassToFeatureClass_conversion(fuas, path_data_fua, "FUA_%s.shp"%(fua), "fuacode_si = '%s'"%(fua))
        print("Paso 1: OK")
        print("")

        print("# 2- PROJECT THE BOUNDARY OF THE FUA TO UTM")
        fua_sel = path_data_fua + "FUA_%s.shp"%(fua)
        print("Fua_sel path: ", fua_sel)

        # look for the correct EPSG
        arcpy.FeatureToPoint_management(fua_sel, out_vec  + "pto.shp", "CENTROID")
        arcpy.MakeFeatureLayer_management(proj_utm, "proj_utm")
        arcpy.SelectLayerByLocation_management ("proj_utm", "intersect", out_vec  + "pto.shp")
        epsg = [int(code[0]) for code in arcpy.da.SearchCursor("proj_utm", "EPSG")][0]
        output = path_data_fua + "FUA_%s_%s.shp"%(fua,epsg)
        print("output EPSG path: ", output)

        # install gdal and change path accordingly
        subprocess.call('"C:\\Program Files\\GDAL\\ogr2ogr.exe" -f "ESRI Shapefile" -s_srs EPSG:3857 -t_srs EPSG:%s %s %s' %(epsg, output, fua_sel))
        # Verify the file was created
        if not os.path.exists(output):
                raise FileNotFoundError(f"The file {output} does not exist. Exiting script.")
        print("Projected selected FUA shapefile: OK")

        # Area of the FUA in UTM
        areaSO = np.sum(row[0] for row in arcpy.da.SearchCursor(output, "SHAPE@AREA"))/1000000 # Deprecated
        # areaSO = np.sum(np.fromiter(row[0] for row in arcpy.da.SearchCursor(output, "SHAPE@AREA")))/1000000
        sel_fua = output
        arcpy.Delete_management(out_vec  + "pto.shp")
        arcpy.Delete_management("proj_utm")

        output_all = out_ras_all + "BUILT_%s_3857.tif"%(fua)

        # Clip raster with the selected FUA boundary (projected in UTM)
        subprocess.call('"C:\\Program Files\\GDAL\\gdalwarp.exe" -dstnodata 7 -s_srs EPSG:3857 -t_srs EPSG:3857 -cutline %s -crop_to_cutline %s %s' %(fua_sel, input_ghsl, output_all))
        
        # Save in Ras_3857
        arcpy.BuildRasterAttributeTable_management(output_all, "Overwrite")
        print("Paso 2: OK")
        print("")

        n_null = [code[0] for code in arcpy.da.SearchCursor(output_all, "count", "value = 0")]
        if len(n_null) > 0:
            n_total = sum([code[0] for code in arcpy.da.SearchCursor(output_all, "count")])
            cloud = n_null[0] * 100 / n_total

        if cloud < 1:
            output = out_ras + "BUILT_%s_%s_3857.tif"%(fua,date)

            print("# 3 - RECLASSIFY TO GET A BUILT-UP MAP FOR THE YEAR 2000")
            arcpy.gp.Reclassify_sa(output_all, "Value", "0 NODATA;1 NODATA;2 NODATA;3 NODATA;4 1;5 1;6 1", output, "DATA")

            n_pixels = [code[0] for code in arcpy.da.SearchCursor(output, "count")][0]
            print("Paso 3: OK")
            print("")

            print("# 4 - CONVERT RASTER DATA TO VECTOR")
            # https://gis.stackexchange.com/questions/417383/how-to-apply-gdal-polygonize
            input_layer = output
            print("input raster layer: ", input_layer)
            # Opening the input layer
            dataset = gdal.Open(input_layer)
            if dataset is None:
                print("Failed to open", input_layer)
            else:
                # Checking if the dataset has at least one band
                if dataset.RasterCount > 0:
                    # Getting the first band
                    band = dataset.GetRasterBand(1)
                    dst_layername = "BUILT_%s_%s_3857"%(fua,date)
                    drv = ogr.GetDriverByName("ESRI Shapefile")
                    dst_ds = drv.CreateDataSource(vec_3857)
                                                  
                    sp_ref = osr.SpatialReference()
                    sp_ref.SetFromUserInput('EPSG:4326') 

                    dst_layer = dst_ds.CreateLayer(dst_layername, srs = sp_ref )
                
                    #fld = ogr.FieldDefn("HA", ogr.OFTInteger)
                    #dst_layer.CreateField(fld)
                    #dst_field = dst_layer.GetLayerDefn().GetFieldIndex("HA")

                    gdal.Polygonize( band, None, dst_layer, -1, [], callback=None )

                    #del src_ds
                    del dst_ds
                    print("Polygonization successful.")
                else:
                    print("Dataset has no bands.")

            output = vec_3857 + "BUILT_%s_%s_3857.shp"%(fua,date)
            
            # Before using the vectorized raster file in subsequent operations
            if not os.path.exists(output):
                raise FileNotFoundError(f"The file {output} does not exist. Exiting script.")
            
            if os.path.exists(output):
                print(f"Output: {output}.")
                print("Paso 4: OK")
                print("")
            

            print("# 5 - PROJECT TO UTM")
            input_layer = output
            output = out_vec + "BUILT_%s_%s_%s.shp"%(fua,date,epsg)
            print("output :", output)
            subprocess.call('"C:\\Program Files\\GDAL\\ogr2ogr.exe" -f "ESRI Shapefile" -s_srs EPSG:3857 -t_srs EPSG:%s %s %s' %(epsg, output, input_layer))
            print("Paso 5: OK")
            print("")

            print("# 6 - SPATIAL METRICS FROM INDIFRAG for the BUILT-UP AREA")
            arcpy.MakeFeatureLayer_management(fuas, "sel_fua", "fuacode_si = '%s'"%(fua))
            supobjetos = "sel_fua"
            objetos = output

            arcpy.CalculateField_management (supobjetos, "Clouds", cloud , "PYTHON")
            arcpy.CalculateField_management (supobjetos, "AreaFUA", areaSO , "PYTHON")

            Calc_Are_Per(objetos, "Area", "Perim")

            #areaU = np.sum(fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@AREA"))
            #perimU = np.sum(fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@LENGTH"))
            #cont1 =  int(str(arcpy.GetCount_management(objetos)))

            areaU = np.sum(np.fromiter((fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@AREA")), float))
            perimU = np.sum(np.fromiter((fila[0] for fila in arcpy.da.SearchCursor(objetos, "SHAPE@LENGTH")), float))
            cont1 = int(str(arcpy.GetCount_management(objetos)))
            
            print("Starting computation of urban metrics")
            # Urban area (UA)
            arcpy.CalculateField_management (supobjetos, "UA_T1", areaU/1000000 , "PYTHON")
            arcpy.CalculateField_management (supobjetos, "DU_T1", (areaU/1000000)/areaSO*100 , "PYTHON")

            print("# Normalized area-weighted standard distance (AWSD)")
            arcpy.StandardDistance_stats( objetos, out_vec  + "sdist.shp", "1_STANDARD_DEVIATION", "Area")
            distEstSO = [fila[0] for fila in arcpy.da.SearchCursor( out_vec  + "sdist.shp", "StdDist")][0]
            arcpy.Delete_management(out_vec  + "sdist.shp")
            # normalization with the `maximum distance'
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
            arcpy.CalculateField_management( supobjetos, "AWSD_T1", (distEstSO*100/DS_max), "PYTHON_9.3")

            print("# Urban compactness (CU)")
            compac = (2*math.sqrt(math.pi*areaU))/perimU
            arcpy.CalculateField_management (supobjetos, "C_T1", compac*100, "PYTHON")

            print("# Dispersion index (DI)")
            Amax = np.amax([(fila[0],fila[1]) for fila in arcpy.da.SearchCursor(objetos, ["SHAPE@AREA","SHAPE@LENGTH"])], axis=0)
            Lpi = Amax[0]/areaU*100
            form_DI = ((((cont1-1)/(n_pixels-1))*100) +(100-Lpi))/2
            arcpy.CalculateField_management (supobjetos, "DI_T1", form_DI , "PYTHON")
            print("")
            
            print("# 7 - SPATIAL METRICS FROM INDIFRAG for the URBAN CORE")
            if not arcpy.ListFields(objetos, "UMZ"):
                arcpy.AddField_management(objetos, "UMZ", "SHORT", None, None, None, None, "NULLABLE", "NON_REQUIRED")

            print("# seleccionar el Largest Patch")
            Amax = np.max([fila[0] for fila in arcpy.da.SearchCursor(objetos, "Area")])
            arcpy.MakeFeatureLayer_management(objetos, "lpi", "Area = %s"%(Amax))
            arcpy.CopyFeatures_management("lpi", path_temp+"umz.shp")

            # loop to select the patches in 200 meters from the LP. Urban Morphological Zone can be defined as “A set of urban areas laying less than 200m apart”
            arcpy.MakeFeatureLayer_management(objetos, "selec_umz")
            for i in range(0,3):
                arcpy.SelectLayerByLocation_management(in_layer="selec_umz", overlap_type="WITHIN_A_DISTANCE", select_features=path_temp+"umz.shp", search_distance="200 Meters", selection_type="ADD_TO_SELECTION", invert_spatial_relationship="NOT_INVERT")
                arcpy.CopyFeatures_management("selec_umz", path_temp+"umz.shp")

            arcpy.CalculateField_management ("selec_umz", "UMZ", 1 , "PYTHON")

            print("# Area of the urban core")
            A_UMZ = np.sum([fila[0] for fila in arcpy.da.SearchCursor("selec_umz", "Area")])

            print("# Elongation ratio (ER_UC) for the Largest urban core")
            arcpy.MinimumBoundingGeometry_management("selec_umz", path_temp+"lpi_MBG.shp", geometry_type="RECTANGLE_BY_WIDTH", group_option="ALL", group_field="", mbg_fields_option="MBG_FIELDS")
            lados = [(fila[0],fila[1]) for fila in arcpy.da.SearchCursor(path_temp+"lpi_MBG.shp", ["MBG_Width","MBG_Length"])][0]
            diamArea = 2*(math.sqrt(A_UMZ/math.pi))
            arcpy.CalculateField_management (supobjetos, "ER_UC_T1", diamArea/lados[1] , "PYTHON")

            print("# compactness (C_UC) for the Largest urban core")
            #PerUMZ = np.sum([fila[0] for fila in arcpy.da.SearchCursor("selec_umz", "Perim")])
            #c_UMZ = (2*math.sqrt(math.pi*A_UMZ))/PerUMZ
            #arcpy.CalculateField_management (supobjetos, "C_UC_T1", c_UMZ*100 , "PYTHON")

            # Check if the cursor returns any rows
            with arcpy.da.SearchCursor("selec_umz", "Perim") as cursor:
                rows = list(cursor)
                if len(rows) == 0:
                    print("No rows found in 'selec_umz'. Cannot calculate C_UC.")
                    continue

                # Calculate the sum of perimeters
                PerUMZ = np.sum([fila[0] for fila in rows])

                # Check if PerUMZ is zero
                if PerUMZ == 0:
                    print("'PerUMZ' is zero. Cannot proceed with calculation.")
                    continue

                c_UMZ = (2 * math.sqrt(math.pi * A_UMZ)) / PerUMZ
                arcpy.CalculateField_management(supobjetos, "C_UC_T1", c_UMZ * 100, "PYTHON")

            print("# Largest the urban core (L_UC)")
            LP_umz = A_UMZ/areaU*100
            arcpy.CalculateField_management (supobjetos, "L_UC_T1", LP_umz , "PYTHON")

            print("# Second largest urban core (SL_UC)")
            #Amax2nd = np.max([fila[0] for fila in arcpy.da.SearchCursor(objetos, "Area", "UMZ <> 1")])
            #arcpy.MakeFeatureLayer_management(objetos, "lpi2nd", "Area = %s"%(Amax2nd))
            #arcpy.CopyFeatures_management("lpi2nd", path_temp+"umz2.shp")

            # Attempt to find the second largest urban core
            areas = [fila[0] for fila in arcpy.da.SearchCursor(objetos, "Area", "UMZ <> 1")]
            if not areas:
                print("No second largest urban cores found based on criteria 'UMZ <> 1'. Cannot proceed.")
            else:
                Amax2nd = np.max(areas)
                arcpy.MakeFeatureLayer_management(objetos, "lpi2nd", f"Area = {Amax2nd}")
                arcpy.CopyFeatures_management("lpi2nd", path_temp + "umz2.shp")

                arcpy.MakeFeatureLayer_management(objetos, "selec_umz2")
                for i in range(0,3):
                    arcpy.SelectLayerByLocation_management(in_layer="selec_umz2", overlap_type="WITHIN_A_DISTANCE", select_features=path_temp+"umz2.shp", search_distance="200 Meters", selection_type="ADD_TO_SELECTION", invert_spatial_relationship="NOT_INVERT")
                    arcpy.CopyFeatures_management("selec_umz2", path_temp+"umz2.shp")
            
                arcpy.CalculateField_management ("selec_umz2", "UMZ", 2 , "PYTHON")

                A_UMZ2 = np.sum([fila[0] for fila in arcpy.da.SearchCursor("lpi2nd", "Area")])

                LP2_umz = A_UMZ2/areaU*100
                arcpy.CalculateField_management (supobjetos, "SL_UC_T1", LP2_umz , "PYTHON")

            # delete temporal datasets
            arcpy.Delete_management(supobjetos)
            arcpy.Delete_management("LUCob")

            arcpy.Delete_management(path_data_fua+ "FUA_%s.shp"%(fua))

            arcpy.Delete_management(path_temp+"lpi_MBG.shp")
            arcpy.Delete_management("lpi")
            arcpy.Delete_management("selec_umz")
            arcpy.Delete_management("selec_umz2")
            arcpy.Delete_management("lpi2nd")
            arcpy.Delete_management(path_temp+"umz.shp")
            arcpy.Delete_management(path_temp+"umz2.shp")
            arcpy.Delete_management(out_vec  + "pto.shp")
            print("Time {:.2f} min.".format(round((time.time() - s2) / 60, 2)))

        if cloud > 1:
            arcpy.MakeFeatureLayer_management(fuas, "sel_fua", "fuacode_si = '%s'"%(fua))
            supobjetos = "sel_fua"
            arcpy.CalculateField_management (supobjetos, "Clouds", cloud , "PYTHON")

except Exception as e:
    print(e)

finally:
    print("Total processing time {:.2f} min.".format(round((time.time() - s1) / 60, 2)))

