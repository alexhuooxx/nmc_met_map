import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math
import os
import xarray as xr
import matplotlib as mpl
import matplotlib.pyplot as plt
from nmc_met_publish_map.source.utility import add_logo_extra,add_public_title,add_logo_extra_in_axes,add_public_title_sta
import locale
import sys
import metpy.calc as mpcalc
from metpy.units import units
import astropy.units as unt
from nmc_met_io.retrieve_micaps_server import get_model_points,get_model_3D_grids,get_latest_initTime
import nmc_met_map.lib.utility as utl
from nmc_met_map.graphics import sta_graphics


def Station_Synthetical_Forecast_From_Cassandra(
        model='ECMWF',
        output_dir=None,
        output_head_name=None, # 'SEVP_NMC_RFFC_SCMOC_EME_ASH_LNO_P9_'
        output_tail_name=None, #07203  or 24003
        t_range=[1,29],
        t_gap=3,
        points={'lon':[116.3833], 'lat':[39.9]},
        initTime=None,
        draw_VIS=False,
        data_src='SC' # 'SC' or 'SM'
            ):

    #+get all the directories needed
    try:
        dir_rqd=[ 
                "ECMWF_HR/10_METRE_WIND_GUST_IN_THE_LAST_3_HOURS/",
                "ECMWF_HR/10_METRE_WIND_GUST_IN_THE_LAST_6_HOURS/",
                "ECMWF_HR/LCDC/",
                "ECMWF_HR/TCDC/",
                "ECMWF_HR/UGRD_100M/",
                "ECMWF_HR/VGRD_100M/",
                "NWFD_SCMOC/VIS_SURFACE/",

                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='RAIN03'),
                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='RAIN06'),
                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='T2m'),
                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='u10m'),
                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='v10m'),
                ]
    except KeyError:
        raise ValueError('Can not find all required directories needed')
    
    try:
        dir_opt=[ 
                utl.Cassandra_dir(
                    data_type='surface',data_source=model,var_name='Td2m')
                ]
    except:
        dir_opt=[
                utl.Cassandra_dir(data_type='surface',data_source=model,var_name='rh2m')
                ]
          
    #+get all the directories needed

    if(initTime == None):
        last_file={model:get_latest_initTime(dir_rqd[0]),
                    'SCMOC':get_latest_initTime(dir_rqd[6]),
                    }
    else:
        last_file={model:initTime[0],
                    'SCMOC':initTime[1],
                    }        

    y_s={model:int('20'+last_file[model][0:2]),
        'SCMOC':int('20'+last_file['SCMOC'][0:2])}
    m_s={model:int(last_file[model][2:4]),
        'SCMOC':int(last_file['SCMOC'][2:4])}
    d_s={model:int(last_file[model][4:6]),
        'SCMOC':int(last_file['SCMOC'][4:6])}
    h_s={model:int(last_file[model][6:8]),
        'SCMOC':int(last_file['SCMOC'][6:8])}

    fhours = np.arange(t_range[0]*t_gap, t_range[1]*t_gap, t_gap)
    for ifhour in fhours:
        if (ifhour == fhours[0] ):
            time_all=datetime(y_s[model],m_s[model],d_s[model],h_s[model])+timedelta(hours=int(ifhour))
        else:
            time_all=np.append(time_all,datetime(y_s[model],m_s[model],d_s[model],h_s[model])+timedelta(hours=int(ifhour)))            

    filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
    t2m=get_model_points(dir_rqd[9], filenames, points)
    
    Td2m=get_model_points(dir_opt[0], filenames, points)
    if(Td2m is None):
        rh2m=get_model_points(dir_opt[0], filenames, points)
        Td2m=mpcalc.dewpoint_rh(t2m['data'].values*units('degC'),rh2m['data'].values/100.)
        p_vapor=(rh2m['data'].values/100.)*6.105*(math.e**((17.27*t2m['data'].values/(237.7+t2m['data'].values))))

    if(Td2m is not None):
        rh2m=mpcalc.relative_humidity_from_dewpoint(t2m['data'].values* units('degC'),
                Td2m['data'].values* units('degC'))
        p_vapor=(np.array(rh2m))*6.105*(math.e**((17.27*t2m['data'].values/(237.7+t2m['data'].values))))
        Td2m=np.array(Td2m['data'].values)* units('degC')

    u10m=get_model_points(dir_rqd[10], filenames, points)
    v10m=get_model_points(dir_rqd[11], filenames, points)
    wsp10m=(u10m['data']**2+v10m['data']**2)**0.5
    AT=1.07*t2m['data'].values+0.2*p_vapor-0.65*wsp10m-2.7      
    if((t_range[1]-1)*t_gap > 84):
        fhours = np.arange(6, t_range[1]*t_gap, 6)
        filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
        r03=get_model_points(dir_rqd[8], filenames, points)
    else:
        r03=get_model_points(dir_rqd[7], filenames, points)

    fhours = np.arange(t_range[0]*t_gap, 75, t_gap)
    filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
    VIS=get_model_points(dir_rqd[6], filenames, points)     

    if(last_file['SCMOC'] == last_file[model] and t_range[1]*t_gap > 72):
        fhours = np.append(np.arange(3,72,3),np.arange(72, (t_range[1])*t_gap, 6))
        filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
        filenames2 = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]            

    if(last_file['SCMOC'] != last_file[model] and t_range[1]*t_gap > 60):
        fhours = np.append(np.arange(3,60,3),np.arange(60, (t_range[1])*t_gap, 6))
        filenames = [last_file[model]+'.'+str(fhour+12).zfill(3) for fhour in fhours]
        filenames2 = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]

    if(last_file['SCMOC'] != last_file[model] and t_range[1]*t_gap <= 60):
        fhours = np.arange(t_range[0]*t_gap, t_range[1]*t_gap, t_gap)
        filenames = [last_file[model]+'.'+str(fhour+12).zfill(3) for fhour in fhours]
        filenames2 = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]

    if(last_file['SCMOC'] == last_file[model] and t_range[1]*t_gap <= 72):
        fhours = np.arange(t_range[0]*t_gap, t_range[1]*t_gap, t_gap)
        filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
        filenames2 = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]

    TCDC=get_model_points(dir_rqd[2], filenames2, points)
    LCDC=get_model_points(dir_rqd[3], filenames2, points)
    u100m=get_model_points(dir_rqd[4], filenames2, points)
    v100m=get_model_points(dir_rqd[5], filenames2, points)
    wsp100m=(u100m['data']**2+v100m['data']**2)**0.5

    if(fhours[-1] < 120):
        gust10m=get_model_points(dir_rqd[0], filenames, points)
    if(fhours[-1] > 120):
        if(last_file['SCMOC'] == last_file[model]):
            fhours = np.arange(0, t_range[1]*t_gap, 6)
            filenames = [last_file[model]+'.'+str(fhour).zfill(3) for fhour in fhours]
        if(last_file['SCMOC'] != last_file[model]):
            fhours = np.arange(0, t_range[1]*t_gap, 6)
            filenames = [last_file[model]+'.'+str(fhour+12).zfill(3) for fhour in fhours]
        gust10m=get_model_points(dir_rqd[1], filenames, points)        
        
    sta_graphics.draw_Station_Synthetical_Forecast_From_Cassandra(
            t2m=t2m,Td2m=Td2m,AT=AT,u10m=u10m,v10m=v10m,u100m=u100m,v100m=v100m,
            gust10m=gust10m,wsp10m=wsp10m,wsp100m=wsp100m,r03=r03,TCDC=TCDC,LCDC=LCDC,
            draw_VIS=True,VIS=VIS,
            time_all=time_all,
            model=model,points=points,
            y_s=y_s,m_s=m_s,d_s=d_s,h_s=h_s,
            output_dir=None)        