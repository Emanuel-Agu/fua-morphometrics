#-------------------------------------------------------------------------------
# Name:         2.4. Regression models and identifying spatio-temporal metrics relevance
#
# Purpose:      Random forest regression models of the socio-economic variables (OECD)
#                 and spatio-temporal metrics "Output_spatio_temporal_analysis"
#
#               This code belongs to the publication doi: https://doi.org/10.3390/ijgi9070436
#
# Required libraries:   dplyr, ggplot2, randomForest,rfPermute,ggrepel
#
# Author:       Marta Sapena (https://orcid.org/0000-0003-3283-319X)
#
# Created:     08/03/2018
# Copyright:   (c)
# Licence:     In all distribution of or public communications made concerning the code,
#              the authors shall always be cited. In any case of publishing results,
#              the only strict obligation is to acknowledge the origin and ownership
#-------------------------------------------------------------------------------

library(dplyr)
library(ggplot2)
library(randomForest)
library(rfPermute)
library(ggrepel)


## FUNCTIONS

# optimize selection of mtry and node size
# based on: https://rpubs.com/Joaquin_AR/255596 
tuning_rf <- function(df, y, size = NULL, ntree = 500){
  require(dplyr)
  if (is.null(size)){
    size <- seq(from = 1, to = nrow(df), by = 5)
  }
  max_predictors <- ncol(df) - 1
  n_predictors <- rep(NA, length(size) * max_predictors)
  n_node <- rep(NA, length(size) * max_predictors)
  oob_mse <- rep(NA, length(size) * max_predictors)
  rsqr_l <- rep(NA, length(size) * max_predictors)
  c = 0
  for (i in 1:max_predictors) {
    for (j in seq_along(size)) {
      c = c + 1
      set.seed(123)
      f <- formula(paste(y,"~ ."))
      model_rf <- randomForest(formula = f, data = df, mtry = i, nodesize = j, ntree = ntree, proximity=T)
      rsqr <- round((1 - sum((model_rf$y-model_rf$predicted)^2)/sum((model_rf$y-mean(model_rf$y))^2))*100,4)
      rsqr_l[c] <- tail(rsqr, n = 1)
      n_predictors[c] <- i
      n_node[c] <- j
      oob_mse[c] <- tail(model_rf$mse, n = 1)
    }
  }
  results <- data_frame(n_predictors, n_node, oob_mse,rsqr_l)
  return(results)
}

# methods to normalize the RMSE
# from: https://www.marinedatascience.co/blog/2019/01/07/normalizing-the-rmse/
nrmse_func <-  function(obs, pred, type = "sd") {
  squared_sums <- sum((obs - pred)^2)
  mse <- squared_sums/length(obs)
  rmse <- sqrt(mse)
  if (type == "sd") nrmse <- rmse/sd(obs)
  if (type == "maxmin") nrmse <- rmse/ (max(obs) - min(obs))
  if (!type %in% c("sd", "maxmin")) message("Wrong type!")
  nrmse <- nrmse
  return(nrmse)
}


my_colors = c("#a060ff","#4e63b2","#eaef22","#75d94c","#50b570","#006800","#fcbecf",
              "#8c0047","#f78600","#c0b53d","#4f6851","#8C3C3C","#9de0e1","#a7a1d3","#c80000",
              "#B57E38","#36FF00","#a1a0a1","#fc5d98","#0074d8","#ff8042","#cd9283","#4f98bd",
              "#a0b838","#050005","#75130f","#e5008b","#FFF500","#FF0000","#824119",
              "#00e6ff","#00007f")

# input path
rutaE = "...\\Data_Codes\\DATA\\OECD_02_2020\\Preprocessed\\"

# output path
rutaS = "...\\Data_Codes\\DATA\\Output_statistical_analysis\\"

if (file.exists(rutaS)== FALSE){
  dir.create(file.path(rutaS))
}

paises <-
  read.csv(
    paste(rutaE, "names_FUAs.csv", sep = ""),
    header = T,
    encoding = "UTF-8",
    sep = ","
  )

# load socio-economic data
load(paste(rutaE, "Datos_OECD_CH.Rda", sep=""))
load(paste(rutaE, "Datos_OECD_T2.Rda", sep=""))

datosSE_t2 <- merge(datosSE_t2, paises[,c("fuacode_si","fuaname_en")], by = "fuacode_si")
datosSE_ch <- merge(datosSE_ch, paises[,c("fuacode_si","fuaname_en")], by = "fuacode_si")

# load spatio-temporal data
load(paste(rutaE, "Spatiotemp_metrics.Rda", sep=""))
load(paste(rutaE, "spatial_metrics.Rda", sep=""))
load(paste(rutaE, "Pugi.Rda", sep=""))
load(paste(rutaE, "Roads.Rda", sep=""))
load(paste(rutaE, "LandCover_CH.Rda", sep=""))
load(paste(rutaE, "LC_dens.Rda", sep=""))

# Create the different combination subsets of spatial and multi-temporal metrics
datos_comb_mt <- merge(datos_CH, datos_LCC, by = "fuacode_si")
datos_comb_mt <- merge(datos_comb_mt, datos_pugi, by = "fuacode_si")

datos_comb <- merge(datos_FM14, datos_road, by = "fuacode_si")
datos_comb_t2 <- merge(datos_comb, lc_den, by = "fuacode_si")

datos_comb <- merge(datos_comb, datos_LCC, by = "fuacode_si")
datos_comb <- merge(datos_comb, datos_pugi, by = "fuacode_si")

datos_t2_p_lc <- merge(datos_comb_t2, datos_LCC, by = "fuacode_si")
datos_t2_p_lc <- merge(datos_t2_p_lc, datos_pugi, by = "fuacode_si")

datos_comb_all2 <- merge(datos_comb_t2, datos_LCC, by = "fuacode_si")
datos_comb_all2 <- merge(datos_comb_all2, datos_pugi, by = "fuacode_si")

datos_comb_all <- merge(datos_comb_mt, datos_comb_t2[,-(2:2)], by = "fuacode_si")

# Declare all the data for looping the models

names <- list("GDP","Gini",
              "Income","Air_quality",
              "Air_quality_change", "Employment_change")

socioec <- list(datosSE_t2[,c(1,4,6)],datosSE_t2[,c(1,2,6)],
                datosSE_t2[,c(1,5,6)],datosSE_t2[,c(1,3,6)],
                datosSE_ch[,c(1,2,4)],datosSE_ch[,c(1,3,4)])

metricas_all <- list(datos_comb_all[,c(1:7,9:22,24:31)],datos_comb_all[,c(1:4,7,9:22,24:31)],
                     datos_comb[,c(1:8,10:15)],datos_comb_all2,
                     datos_comb_all,datos_comb_all[,c(1:4,6:21,23:30)])

metricas_num <- list(datos_comb_all[,c(3:7,9:22,24:31)],datos_comb_all[,c(3,4,7,9:22,24:31)],
                     datos_comb[,c(3:8,10:15)],datos_comb_all2[,c(3:length(datos_t2_p_lc))],
                     datos_comb_all[,c(3:length(datos_comb_all))],datos_comb_all[,c(3,4,6:21,23:30)])

# to get these numbers for the first time use the comented funcion below "tuning_rf"
best_n <- list(3,2,7,4,1,4)
best_m <- list(9,6,6,9,12,8)


sink(paste(rutaS,"Random_Forest_models.txt",sep=""), append=FALSE, split=FALSE)

for (m in c(1:length(names))){
  # read socioeconomic data
  OECD<-socioec[[m]]
  OECDvar <- colnames(OECD)[2]
  
  col_met <-colnames(metricas_num[[m]])

  datos_met <-metricas_all[[m]]
  
  for(SE in OECDvar) {
    STSE <- datos_met %>% left_join(OECD, by = "fuacode_si")
    STSE <- STSE[order(STSE$country),]
    STSE$color <- my_colors[STSE$country]
    
    STSE_comp <- STSE[,append(append(append(append(SE, col_met), "country"),"color"),"fuaname_en")]
    STSE_comp <- na.omit(STSE_comp)
    STSE_comp <- droplevels(STSE_comp)
    
    cat('\n*** Model for', SE, '***\n\n')
    n <- sum(complete.cases(STSE_comp[,SE]))
    cat('Valid Observations', n, '\n')
    
    # hiperparametro_mtry_node <-  tuning_rf(df = STSE_comp[1:(length(STSE_comp)-3)], y = SE, size = c(1:30))
    # selec <- hiperparametro_mtry_node %>% arrange(oob_mse)
    # best_mtry <- selec[[1,1]]
    # best_nodesize <- selec[[1,2]]
    
    # if we already know the mtry and nodesize, if not run the function above and comment these lines
    best_mtry <- best_m[[m]]
    best_nodesize <- best_n[[m]]
    
    # for reproduciblity set a seed
    set.seed(123)
    formul <- as.formula(paste(SE, " ~ ."))
    random2 <- randomForest(formul, data = STSE_comp[1:(length(STSE_comp)-3)], mtry = best_mtry,
                            ntree = 500, nodesize = best_nodesize, importance = TRUE, proximity=TRUE)
    
    print(random2)
    
    # estimate p-values
    set.seed(123)
    permu <- rfPermute(formul, data = STSE_comp[1:(length(STSE_comp)-3)], mtry = best_mtry,
                       ntree = 500, nodesize = best_nodesize, importance = TRUE, proximity=T, nrep = 100)
    
    # change name of variables fro the plots
    variab <- c("C_T2","C_UC_T2","DI_T2","AWSD_T2","DU_T2","SL_UC_T2","ER_UC_T2","LC1_T2_R","LC2_T2_R","LC3_T2_R","LC5_T2_R","LC6_T2_R","RD_DEN","C_CH","C_UC_CH","DI_CH","AWSD_CH","DU_CH","L_UC_CH","SL_UC_CH","ER_UC_CH","UCR","AWMEI","AWMAI","PUGI","CP_LC1","CP_LC2","CP_LC3","CP_LC4")
    a<- as.data.frame(variab,stringsAsFactors = FALSE)
    listado<- c("C (T2)","C uc (T2)","DI (T2)","AWSD (T2)","D (T2)","Sl uc (T2)","Er uc (T2)","D agric.(T2)","D high veg.(T2)","D low veg.(T2)","D bare (T2)","D water (T2)","D road","C (CH)","C uc (CH)","DI (CH)","AWSD (CH)","D (CH)","Luc (CH)","Sluc (CH)","ER uc (CH)","UCR","AWMEI","AWMAI","PUGI","CP agric.","CP high veg.","CP low veg.","CP urban")
    a$var2 <- listado

    importancia_pred <- as.data.frame(rp.importance(permu, scale = FALSE))
    importancia_pred <- tibble::rownames_to_column(importancia_pred, var = "variable")
    importancia_pred$sd_imp <- permu$importanceSD

    importancia_pred$p_value <- cut(importancia_pred$`%IncMSE.pval`,
                            breaks = c(-Inf, 0.05, Inf),
                            labels = c("<=0.05", ">0.05"))

    importancia_exp <- merge(importancia_pred,a, by.x = "variable", by.y = "variab", all=TRUE, sort = FALSE)
    importancia_exp$variable <- factor(importancia_exp$var2, levels = listado)

    # PLOTTING THE IMPORTANCE
    p <- ggplot(data = importancia_exp, aes(x = reorder(variable, desc(variable)),
                                             y = `%IncMSE`, fill = p_value)) +
      labs(x = "",y = "Increase MSE", title = names[[m]]) +
      geom_col() +
      geom_hline(yintercept = 0, color = "grey80", size=0.5)+
      scale_fill_manual(values = c("steelblue4", "darkgrey"))+
      coord_flip() +
      geom_errorbar(aes(ymin = `%IncMSE` - sd_imp, ymax = `%IncMSE` + sd_imp), width = 0.2)+
      theme_bw() +
      theme(legend.position = "bottom",panel.grid.minor.y=element_blank(),
            panel.grid.major.y=element_blank(),
            panel.grid.major.x =element_line(linetype = "dashed",colour = "grey80"),
            panel.grid.minor.x =element_blank(),
            panel.border = element_blank(),
            axis.line.y.left  = element_line(colour = "black"))

    ggsave(filename=paste(rutaS, names[[m]], "_Importance.png", sep = ""), plot=p, dpi = 200, width = 4, height = 5)
    
    # RMSE is measured in the same units as our outcome; one sensible approach
    # to interpret the RMSE is then to divide it by the mean of our outcome
    # variable so we can interpret in terms of percentage of the mean

    # coef. determination
    rsqr<- round((1 - sum((random2$y-random2$predicted)^2)/sum((random2$y-mean(random2$y))^2))*100,2)
    # errors
    MSE <- mean((random2$predicted - random2$y)^2)
    RMSE <- sqrt(MSE)

    # normalize errors
    NRMSE_sd <- nrmse_func(obs=random2$y,pred=random2$predicted, type ="sd")
    NRMSE_maxmin <- nrmse_func(obs=random2$y,pred=random2$predicted, type ="maxmin")

    cat('\nnode size: ',best_nodesize)
    cat('\nmtry: ',best_mtry)
    cat('\nR-square: ',rsqr,'%')
    cat('\nMSEe: ',MSE)
    cat('\nRMSE: ',RMSE)
    cat('\nNRMSE_sd: ',NRMSE_sd*100,'%')
    cat('\nNRMSE_maxmin: ',NRMSE_maxmin*100,'%\n\n')

    #Variable importance
    cat('Variable importance\n')
    print(round(importance(random2, type=1, scale=FALSE), 8))

    # select the 10 FUAs with highest errors
    rf<-as.data.frame(random2$y)
    rf$predicted <- random2$predicted
    rf$error <- rf$predicted - rf$`random2$y`
    rf$name <- STSE_comp$fuaname_en
    rf$color <- STSE_comp$color
    rf$country <- STSE_comp$country
    sel <- arrange(rf, desc(abs(error)))
    lista <- as.vector(sel$name)
    all = c(random2$predicted,random2$y)
    range = c(min(all), max(all))
    
    rf <- rf[nrow(rf):1,]

    ggplot(rf, aes(x=predicted, y=`random2$y`,label=name, color=country))+
      geom_point(color=rf$color, alpha=0.7,size = 4) +
      geom_abline(intercept = 0, slope = 1, color="black", linetype="dashed", size=0.6)+
      geom_abline(intercept = -RMSE, slope = 1, color="blue",linetype="dashed", size=0.4)+
      geom_abline(intercept = RMSE, slope = 1, color="blue",linetype="dashed", size=0.4)+
      geom_text_repel(aes(label = name), size =4.5,color = "gray20",data = filter(rf, name %in% lista[1:10]), force = 10)+
      labs(x="Predicted", y=paste("Observed (",names[[m]],")")) +
      theme_classic()+
      theme(title = element_text(size = 14), axis.title = element_text(size = 15),
            axis.text= element_text(size = 15), axis.text.y = element_text(angle = 90,vjust=0.5, hjust=0.5),
            panel.border = element_rect(colour = "black", fill=NA))+
      coord_fixed(ratio = 1, xlim =range, ylim =range )

    ggsave(paste(rutaS, names[[m]],"_pred_vs_obs.png", sep = ""), width = 6, height = 6, dpi=150)

    STSE_comp[,SE]<-NULL
    
  }
}
cat("\n")
sink()
