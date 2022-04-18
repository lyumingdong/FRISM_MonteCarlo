
# %%
from matplotlib.image import AxesImage
import pandas as pd
import numpy as np
#import geopandas as gpd
#import networkx as nx
import matplotlib.pyplot as plt
from argparse import ArgumentParser
import seaborn as sns
import geopandas as gpd
#import osmnx as ox
#import plotly.graph_objects as go

# %%
parser = ArgumentParser()
parser.add_argument("-st", "--shipment type", dest="ship_type",
                    help="B2B or B2C", required=True, type=str)
args = parser.parse_args()

# %%
county_list=[1, 13, 41, 55, 75, 81, 85, 95, 97]
sf_map = plt.imread('../../../FRISM_input_output_SF/Sim_inputs/Geo_data/SF_map.png')
BBox= (-123.655,-121.524,36.869,38.852)

# %%
#
# ship_type=args.ship_type
ship_type="B2B"
#ship_type="B2B"
for count_num in county_list:

    payload_df=pd.read_csv("../../../FRISM_input_output/Sim_outputs/Tour_plan/{0}_county{1}_payload_xy.csv" .format(ship_type, count_num))
    #'locationZone_x':long, 'locationZone_y':lat
    fig, ax = plt.subplots(figsize = (9.68,11.45))
    ax.scatter(payload_df.locationZone_x, payload_df.locationZone_y, zorder=1, alpha= 0.2, c='b', s=10)
    ax.set_title('Plotting payload points for county{0}'.format(count_num))
    ax.set_xlim(BBox[0],BBox[1])
    ax.set_ylim(BBox[2],BBox[3])
    ax.imshow(sf_map, zorder=0, extent = BBox, aspect= 'equal')
    fig.savefig('../../../FRISM_input_output/Sim_outputs/{0}payload_plot_county{1}.png'.format(ship_type, count_num))

# %%
fdir_in_out= "../../../FRISM_input_output_SF"
fdir_geo= fdir_in_out+'/Sim_inputs/Geo_data/'
CBG_file= 'sfbay_freight.geojson'

CBGzone_df = gpd.read_file(fdir_geo+CBG_file)
CBGzone_df["GEOID"]=CBGzone_df["GEOID"].astype(str)
## Add county id from GEOID
CBGzone_df["County"]=CBGzone_df["GEOID"].apply(lambda x: x[2:5] if len(x)>=12 else 0)
CBGzone_df["County"]=CBGzone_df["County"].astype(str).astype(int)
CBGzone_df["GEOID"]=CBGzone_df["GEOID"].astype(str).astype(int)
sf_shape_file=CBGzone_df[CBGzone_df["County"].isin(county_list)]

# %%

ship_type="B2B"
#ship_type="B2B"
payload_df=pd.DataFrame()
for count_num in county_list:
    temp=pd.read_csv("../../../Results_from_HPC_v2/Shipment2Fleet/{0}_payload_county{1}_shipall.csv" .format(ship_type, count_num))
    payload_df=pd.concat([payload_df,temp],ignore_index=True)

payload_by_meso=payload_df.groupby(['del_zone'])['del_zone'].agg(agg_ship="count").reset_index()
payload_by_meso['agg_ship']=payload_by_meso['agg_ship']*10
sf_shape_file=sf_shape_file.merge(payload_by_meso,  left_on="MESOZONE",  right_on="del_zone", how="left" )
sf_shape_file.to_file(fdir_geo+"{}_aggregated_demand.geojson".format(ship_type), driver='GeoJSON')

'''
https://api.mapbox.com/styles/v1/ksjeong/cl1y7ojor001314o5mg62wtd7/wmts?access_token=pk.eyJ1Ijoia3NqZW9uZyIsImEiOiJjbDF5N3p4amcwN2ltM2ptZjl2cnQ5YW42In0.hj4c3SVS9YLVe5YTiDdJDw
'''
################################################################################################################

# %%

study_region= "SF" #"AT" 
web_obs=pd.read_csv('../../../FRISM_input_output_{}/Sim_outputs/Generation/{}_webuse_by_income_observed.csv'.format(study_region,study_region))
online_bi_obs=pd.read_csv('../../../FRISM_input_output_{}/Sim_outputs/Generation/{}_online_by_income_observed.csv'.format(study_region,study_region))

df_hh_obs=pd.read_csv('../../../FRISM_input_output_{}/Model_inputs/NHTS/{}_hh.csv'.format(study_region,study_region))
df_per_obs=pd.read_csv('../../../FRISM_input_output_{}/Model_inputs/NHTS/{}_per.csv'.format(study_region,study_region))
df_per_obs_hh=df_per_obs.groupby(['HOUSEID'])['DELIVER'].agg(delivery_f='sum').reset_index()
df_hh_obs=df_hh_obs.merge(df_per_obs_hh, on='HOUSEID', how='left')

df_hh_model=pd.read_csv('../../../FRISM_input_output_{}/Sim_outputs/Generation/households_del.csv'.format(study_region))


df_hh_obs['delivery_f'] =df_hh_obs['delivery_f'].apply(lambda x: 0 if np.isnan(x) else int(x))
df_hh_model['delivery_f'] =df_hh_model['delivery_f'].apply(lambda x: 0 if np.isnan(x) else int(x))


list_income=["income_cls_0","income_cls_1","income_cls_2","income_cls_3"]
dic_income={"income_cls_0": "income <$35k",
            "income_cls_1": "income $35k-$75k",
            "income_cls_2": "income $75k-125k",
            "income_cls_3": "income >$125k"}
     
for ic_nm in list_income:
    plt.figure(figsize = (8,6))
    #plt.hist(df_hh_obs[df_hh_obs[ic_nm]==1]['delivery_f'], color ="blue", density=True, bins=df_hh_obs[df_hh_obs[ic_nm]==1]['delivery_f'].max(), alpha = 0.3, label="observed")
    #plt.hist(df_hh_model[(df_hh_model[ic_nm]==1) & (df_hh_model['delivery_f']<=30)]['delivery_f'], color ="red", density=True, bins=80, alpha = 0.3, label="modeled")
    #plt.hist(df_hh_model[(df_hh_model[ic_nm]==1)]['delivery_f'], color ="red", density=True, bins=df_hh_model[(df_hh_model[ic_nm]==1)]['delivery_f'].max(), alpha = 0.3, label="modeled")
    plt.hist(df_hh_obs[(df_hh_obs[ic_nm]==1) & (df_hh_obs['delivery_f']<=60)]['delivery_f'], color ="blue", density=True, bins=df_hh_obs[(df_hh_obs[ic_nm]==1) & (df_hh_obs['delivery_f']<=60)]['delivery_f'].max(), alpha = 0.3, label="observed")
    plt.hist(df_hh_model[(df_hh_model[ic_nm]==1)& (df_hh_model['delivery_f']<=60)]['delivery_f'], color ="red", density=True, bins=df_hh_model[(df_hh_model[ic_nm]==1)& (df_hh_model['delivery_f']<=60)]['delivery_f'].max(), alpha = 0.3, label="modeled")
    plt.title("Density of Delivery Frequency in {0}, {1}".format(dic_income[ic_nm], study_region))
    plt.legend(loc="upper right")
    plt.savefig('../../../FRISM_input_output_{0}/Sim_outputs/Generation/B2C_delivery_val_{1}.png'.format(study_region, ic_nm))


################################################################################################################    
# %%

fdir_truck='../../../FRISM_input_output/Model_carrier_op/INRIX_processing/'
df_dpt_dist_MD=pd.read_csv(fdir_truck+'depature_dist_by_cbg_MD.csv', header=0, sep=',')
df_dpt_dist_HD=pd.read_csv(fdir_truck+'depature_dist_by_cbg_HD.csv', header=0, sep=',')

fdir_geo='../../../FRISM_input_output/Sim_inputs/Geo_data/'
CBGzone_df = gpd.read_file(fdir_geo+'freight_centroids.geojson')
CBGzone_df.GEOID=CBGzone_df.GEOID.astype(str).astype(int)
df_dpt_dist_MD=df_dpt_dist_MD.merge(CBGzone_df[["GEOID",'MESOZONE']], left_on="cbg_id", right_on="GEOID", how='left')
df_dpt_dist_HD=df_dpt_dist_HD.merge(CBGzone_df[["GEOID",'MESOZONE']], left_on="cbg_id", right_on="GEOID", how='left')
sel_zone= pd.read_csv(fdir_geo+'selected zone.csv')
sel_zone=sel_zone.rename({'blkgrpid':'GEOID'}, axis=1)
sel_zone = sel_zone.merge(CBGzone_df[['GEOID','MESOZONE']], on='GEOID', how='left')

df_dpt_dist_MD=df_dpt_dist_MD[df_dpt_dist_MD['MESOZONE'].isin(sel_zone['MESOZONE'])].reset_index()
df_dpt_dist_HD=df_dpt_dist_HD[df_dpt_dist_HD['MESOZONE'].isin(sel_zone['MESOZONE'])].reset_index()

MD_dpt= df_dpt_dist_MD.groupby(['start_hour'])['Trip'].sum()
MD_dpt=MD_dpt.to_frame()
MD_dpt.reset_index(level=(0), inplace=True)
MD_dpt['Trip_rate']=MD_dpt['Trip']/MD_dpt['Trip'].sum()

HD_dpt= df_dpt_dist_HD.groupby(['start_hour'])['Trip'].sum()
HD_dpt=HD_dpt.to_frame()
HD_dpt.reset_index(level=(0), inplace=True)
HD_dpt['Trip_rate']=HD_dpt['Trip']/HD_dpt['Trip'].sum()

plt.figure(figsize = (8,6))
plt.plot("start_hour", "Trip", data=MD_dpt,color ="blue", label="MD")
plt.plot("start_hour", "Trip", data=HD_dpt, color ="red", label="HD")
plt.title("Distrubtion of stop activities  by time of day (INRIX)")
plt.legend(loc="upper right")
plt.savefig('../../../FRISM_input_output/Sim_outputs/INRIX_truck_dist.png')
# %%
f_dir="/Users/kjeong/NREL/1_Work/1_2_SMART_2_0/Model_development/Results_from_HPC/Tour_plan/"

county_list=[1, 13, 41, 55, 75, 81, 85, 95, 97]
b2b_carrier=0
b2b_veh =0

b2c_carrier=0
b2c_veh =0

for county in county_list:
    df = pd.read_csv(f_dir+"B2B_county{}_carrier_xy.csv".format(county))
    b2b_carrier += df['carrierId'].nunique()
    b2b_veh +=df['tourId'].nunique()

for county in county_list:
    df = pd.read_csv(f_dir+"B2C_county{}_carrier_xy.csv".format(county))
    b2c_carrier += df['carrierId'].nunique()
    b2c_veh +=df['tourId'].nunique()

print ("num_carrier sum: {0}, b2b: {1}, b2c: {2}".format(b2b_carrier+b2c_carrier,b2b_carrier,b2c_carrier))
print ("num_veh sum: {0}, b2b: {1}, b2c: {2}".format(b2b_veh+b2c_veh,b2b_veh,b2c_veh))
# %%
f_dir="/Users/kjeong/NREL/1_Work/1_2_SMART_2_0/Model_development/"

county_list=[1, 13, 41, 55, 75, 81, 85, 95, 97]

df_for_qc=pd.DataFrame(county_list, columns =["county"])
# df_for_qc["B2B_ship_v1"]=0
# df_for_qc["B2B_carr_v1"]=0
# df_for_qc["B2B_veh_v1"]=0
# df_for_qc["B2C_ship_v1"]=0
# df_for_qc["B2C_carr_v1"]=0
# df_for_qc["B2C_veh_v1"]=0

# df_for_qc["B2B_ship_v2"]=0
# df_for_qc["B2B_carr_v2"]=0
# df_for_qc["B2B_veh_v2"]=0
# df_for_qc["B2C_ship_v2"]=0
# df_for_qc["B2C_carr_v2"]=0
# df_for_qc["B2C_veh_v2"]=0

df_for_qc["B2B_ship_v1"]=0
df_for_qc["B2B_ship_v2"]=0
df_for_qc["B2B_carr_v1"]=0
df_for_qc["B2B_carr_v2"]=0
df_for_qc["B2B_veh_v1"]=0
df_for_qc["B2B_veh_v2"]=0
df_for_qc["B2C_ship_v1"]=0
df_for_qc["B2C_ship_v2"]=0
df_for_qc["B2C_carr_v1"]=0
df_for_qc["B2C_carr_v2"]=0
df_for_qc["B2C_veh_v1"]=0
df_for_qc["B2C_veh_v2"]=0

for i in range (0, df_for_qc.shape[0]):
    county=df_for_qc.loc[i,"county"]
    for s_type in ["B2B", "B2C"]:
        try:
            df_ship_v1= pd.read_csv(f_dir+"Results_from_HPC_v1/Shipment2Fleet/"+"{}_payload_county{}_shipall.csv".format(s_type,county))
            df_for_qc.loc[i,s_type+"_ship_v1"]=df_ship_v1.shape[0]
            df_car_v1= pd.read_csv(f_dir+"Results_from_HPC_v1/Tour_plan/"+"{}_county{}_carrier_xy.csv".format(s_type,county))
            df_for_qc.loc[i,s_type+"_carr_v1"]= df_car_v1['carrierId'].nunique()
            df_for_qc.loc[i,s_type+"_veh_v1"]=df_car_v1['tourId'].nunique()
        except:
            print ("no file v1 for {}_county {}".format(s_type,county))
        try: 
            df_ship_v2= pd.read_csv(f_dir+"Results_from_HPC_v3/Shipment2Fleet/"+"{}_payload_county{}_shipall.csv".format(s_type,county))
            df_for_qc.loc[i,s_type+"_ship_v2"]=df_ship_v2.shape[0]
            df_car_v2= pd.read_csv(f_dir+"Results_from_HPC_v3/Tour_plan/"+"{}_county{}_carrier_xy.csv".format(s_type,county))
            df_for_qc.loc[i,s_type+"_carr_v2"]= df_car_v2['carrierId'].nunique()
            df_for_qc.loc[i,s_type+"_veh_v2"]=df_car_v2['tourId'].nunique()
        except:
            print ("no file v2 for {}_county {}".format(s_type,county))    

df_for_qc.to_csv("/Users/kjeong/NREL/1_Work/1_2_SMART_2_0/Model_development/FRISM_input_output_SF/Validation/Sim_result_QC_0416.csv")
# %%
#[1, 13, 41, 55, 75, 81, 85, 95, 97]
f_dir="/Users/kjeong/NREL/1_Work/1_2_SMART_2_0/Model_development/Results_from_HPC_v3/Shipment2Fleet/"
county=85
df_carr=pd.read_csv(f_dir+"B2B_carrier_county{}_shipall.csv".format(county))
df_pay=pd.read_csv(f_dir+"B2B_payload_county{}_shipall.csv".format(county))

carr_id_from_car_f=df_carr["carrier_id"].unique()

test= df_pay[~df_pay["carrier_id"].isin(carr_id_from_car_f)]
test.shape[0]
# %%
f_dir="../../../FRISM_input_output_SF/Sim_outputs/Shipment2Fleet/"
f_dir="../../../Results_from_HPC_v3/Shipment2Fleet/"
county =85
df_carr=pd.read_csv(f_dir+"B2B_carrier_county{}_shipall.csv".format(county))
df_pay=pd.read_csv(f_dir+"B2B_payload_county{}_shipall.csv".format(county))
print (df_pay.shape[0])

# %%
new_df_pay=pd.DataFrame()
new_df_carr=pd.DataFrame()
#for c_id in df_carr["carrier_id"].unique():
for c_id in ["B2B_1006810_4976","B2B_1006812_4977"]:    
    temp_pay_md= df_pay[(df_pay["carrier_id"]==c_id) & (df_pay["veh_type"]=="md")].reset_index(drop=True)
    temp_pay_hd= df_pay[(df_pay["carrier_id"]==c_id) & (df_pay["veh_type"]=="hd")].reset_index(drop=True)
    temp_carr_md = df_carr[df_carr["carrier_id"]==c_id].reset_index(drop=True)
    temp_carr_hd = df_carr[df_carr["carrier_id"]==c_id].reset_index(drop=True)
    num_md = temp_pay_md.shape[0]
    num_hd = temp_pay_hd.shape[0]

    if num_md ==0:
        temp_carr_md = pd.DataFrame()
    elif num_md <= 30 and num_md >0:
        new_c_id=c_id+"m"
        temp_pay_md["carrier_id"] = new_c_id
        temp_carr_md["carrier_id"] = new_c_id
        temp_carr_md["num_veh_type_1"] =num_md
        temp_carr_md["num_veh_type_2"] =0
    else: 
        for i in range(0,temp_pay_md.shape[0]):
            new_c_id=c_id+"m{}".format(str(int(i/30)))
            temp_pay_md.loc[i,"carrier_id"] = new_c_id
        break_num=int(num_md/30)+1
        temp_carr_md=pd.concat([temp_carr_md]*break_num, ignore_index=True).reset_index(drop=True)
        for i in range(0,temp_carr_md.shape[0]):
            new_c_id=c_id+"m{}".format(str(i))
            temp_carr_md.loc[i,"carrier_id"] = new_c_id
            temp_carr_md["num_veh_type_1"] =30
            temp_carr_md["num_veh_type_2"] =0                    
    if num_hd ==0:
        temp_carr_hd = pd.DataFrame()
    elif num_hd <= 30 and num_hd >0:
        new_c_id=c_id+"h"
        temp_pay_hd["carrier_id"] = new_c_id
        temp_carr_hd["carrier_id"] = new_c_id
        temp_carr_hd["num_veh_type_1"] =0
        temp_carr_hd["num_veh_type_2"] =num_hd
    else: 
        for i in range(0,temp_pay_hd.shape[0]):
            new_c_id=c_id+"h{}".format(str(int(i/30)))
            temp_pay_hd.loc[i,"carrier_id"] = new_c_id
        break_num=int(num_hd/30)+1
        temp_carr_hd=pd.concat([temp_carr_hd]*break_num, ignore_index=True).reset_index(drop=True)
        for i in range(0,temp_carr_hd.shape[0]):
            new_c_id=c_id+"h{}".format(str(i))
            temp_carr_hd.loc[i,"carrier_id"] = new_c_id
            temp_carr_hd["num_veh_type_1"] =0
            temp_carr_hd["num_veh_type_2"] =30
    new_df_pay=pd.concat([new_df_pay,temp_pay_md, temp_pay_hd], ignore_index=True).reset_index(drop=True)
    new_df_carr=pd.concat([new_df_carr,temp_carr_md, temp_carr_hd ], ignore_index=True).reset_index(drop=True) 

# %%
