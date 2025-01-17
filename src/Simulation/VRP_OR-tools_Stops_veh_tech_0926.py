# Authors: Juliette Ugirumurera and Kyungsoo Jeong

"""Run to generate vehicles' tour plans considering timing and load constraints.

"""

import pandas as pd
import geopandas as gp
import csv
import numpy as np
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from copy import copy
import os
import inspect
from xml.dom import minidom
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from time import time
import numpy as np
from argparse import ArgumentParser
from shapely.geometry import Point
import random
import config
import pickle


# Global Variables
tour_id = 0
payload_i = 0
depot_i = 0
job_id = 0


def tt_cal(org_meso, dest_meso, org_geoID, dest_geoID, sel_tt, sel_dist):
    """Retreives the travel time between an origin and destination.

    Retrieves travel time between origin and destination geo ids (geo ids are census block group ids); 
    if we can't get travel time with geo ids, the travel time is calculated from
    the distance between the origin and destination mesozones (mesozones are assigned by synthfirm module).

    Args:
        org_meso: origin mesozone id
        dest_meso: destination mesozone id
        org_geoID: origin geo id
        dest_geoId: dest geo id
        sel_tt: subset of origin-destination travel time dataframe containing data for org_geoID and dest_geoID
        sei_dist: subset of origin-destination distance dataframe contaning data org_meso and dest_meso

    Returns:
        travel_time: travel time between the origin and destination
    """
    travel_time = -1
    try:
        # print('org_geo: ', org_geoID, ' dest geo: ', dest_geoID)
        travel_time = sel_tt['TIME_minutes'].to_numpy()[(sel_tt['origin'].to_numpy() == org_geoID)
                                              &(sel_tt['destination'].to_numpy() == dest_geoID)].item()
    except:
        try:
            dist = sel_dist['dist'].to_numpy()[(sel_dist['Origin'].to_numpy() == org_meso)
                                              &(sel_dist['Destination'].to_numpy() == dest_meso)].item()
            travel_time= dist/40*60
        except:
            travel_time = 60*3
    return travel_time

def ec_cal(org_meso, dest_meso, org_geoID, dest_geoID, sel_ec, sel_dist, ec_vehicletype_df, veh_type):
    """
    Args:
        org_meso: origin mesozone id
        dest_meso: destination mesozone id
        org_geoID: origin geo id
        dest_geoId: dest geo id
        sel_ec: subset of origin-destination energy cost dataframe containing data for org_geoID and dest_geoID
        sei_dist: subset of origin-destination distance dataframe contaning data org_meso and dest_meso

    Returns:
        energy cost: energy cost between the origin and destination
    """
    energy_cost = -1
    try:
        # print('org_geo: ', org_geoID, ' dest geo: ', dest_geoID)
        energy_cost = (sel_ec['energy'].to_numpy()[(sel_ec['origTaz'].to_numpy() == org_geoID)
                                              &(sel_ec['destTaz'].to_numpy() == dest_geoID)
                                              &(sel_ec['vehicleType'] == veh_type)].item())/1.3E8

    except:
        try:
            dist = sel_dist['dist'].to_numpy()[(sel_dist['Origin'].to_numpy() == org_meso)
                                              &(sel_dist['Destination'].to_numpy() == dest_meso)].item()
            primary_fuel_rate = ec_vehicletype_df['primary-fuel-rate'][ec_vehicletype_df['veh-type-id'] == veh_type].values
            energy_cost= dist * primary_fuel_rate # include different vechile type(a look-up table)
        except:
            energy_cost = np.mean(sel_ec.energy)/1.3E8
    return energy_cost

def get_geoId(zone, CBGzone_df):
    """Retreives the geo ID of a given mesozone.

    Give mesozone id, retreives the corresponding geo id from dataframe that
     maps mesozone to geo ids to mesozone ids.

    Args:
        zone: mesozone id
        CBGzone_df: dataframe that maps mesozones to geo ids

    Returns:
        org_geoID: returns the corresponding geo id. If mesozone was not found, org_geoID is 
        set to -1.
    """
    try:
        org_geoID= int(CBGzone_df[CBGzone_df['MESOZONE']==zone].GEOID.values[0])
    except:
        org_geoID = -1
    return int(org_geoID)


def create_data_model(df_prob, depot_loc, prob_type, v_df, f_prob, c_prob, carrier_id,
                     CBGzone_df, tt_df, ec_df, ec_vehicletype_df, dist_df, veh, commodity, ship_index, path_stops):
    """Create the data model for the vehicle routing problem.

    Args:
        df_prob: payload information for the vehicle routing problem
        depot_loc: mesozone id of depot location for the problem
        prob_type: problem type(Pickup, Delivery, or Pickup and Delivery)
        v_df: dataframe with vehicle types infomation (vehicle capacity, vehicle technology: diezel or gasoline,..)
        f_prob: dataframe with individual vehicle information (vehicle id, vehicle capacity, ...)
        c_prob: carrier information dataframe
        carrier_id: carrier id
        CBGzone_df: dataframe that maps geo ids to mesozones
        tt_df: orgin-destination travel time dataframe
        dist_df: origin-destination distance dataframe
        veh: vehicle type
        commodity: commodity id of shipment to be carried
        ship_index: integer that indicates if the shipments inside the region or has a 
                    destination external to the region

    Returns:
        data: returns a dictionary with with all data necessary to formulate and solve a vehile routing
        problem using ortools library.
    """

    # random.seed(10) # seeding the random generator to ensre consistent results for testing purposes

    try:
        data = {}
        data['time_matrix'] = []

        data['energy_matrix'] = []
        
        data['loc_zones'] = []    # zones corresponding to locations
        data['payload_ids'] = []
        data['stop_durations'] = []

        if prob_type == 'pickup_delivery':
            data['pickups_deliveries']=[]

        time_l = []
        # Adding time 0 for the depot and location for depot
        time_l.append(0)
        data['loc_zones'].append(depot_loc)
        depot_service_time = float(c_prob.loc[c_prob['carrier_id'] == carrier_id]['depot_time_before'].values[0])
        data['stop_durations'].append(depot_service_time)

        data['time_windows'] = []
        # Add time window for depot
        data['time_windows'].append((int(c_prob.loc[c_prob['carrier_id'] == carrier_id]['depot_lower'].values[0]),
                                    int(c_prob.loc[c_prob['carrier_id'] == carrier_id]['depot_upper'].values[0])))
        data['demands'] = []
        if commodity != 2 and ship_index =='internal':
            data['stops'] = []  # parameter to keep track of number of stops per node
            data['stops'].append(0.0) # No stop counted for depot

            data['vehicle_max_stops'] = []
            data['vehicle_slack_stops'] = []

        # if problem is delivery, we start with full laod at depot
        # if problem is pickup, we start with empty load
        data['demands'].append(0.0) # Adding demand for depot

        data['geo_ids'] = []
        data['geo_ids'].append(get_geoId(depot_loc, CBGzone_df))
        
        index = 1
        for i in df_prob['payload_id'].unique():
            if prob_type == 'delivery':
                temp_zone = (int(df_prob.loc[df_prob['payload_id'] == i]['del_zone'].values[0])) # find zone
                data['loc_zones'].append(copy(temp_zone))     # saving zone
                data['geo_ids'].append(get_geoId(temp_zone, CBGzone_df))

                # Adding time window
                data['time_windows'].append((int(df_prob.loc[df_prob['payload_id'] == i]['del_tw_lower'].values[0]),
                                    int(df_prob.loc[df_prob['payload_id'] == i]['del_tw_upper'].values[0])))

                data['payload_ids'].append(copy(i))

                demand = math.ceil(df_prob.loc[df_prob['payload_id'] == i]['weight'].values[0])
                data['demands'].append(copy(demand))
                if commodity != 2 and ship_index =='internal': data['stops'].append(1)  # stop for this demand location

                service_time = float(df_prob.loc[df_prob['payload_id'] == i]['del_stop_duration'].values[0])
                data['stop_durations'].append(copy(service_time))


            elif prob_type =='pickup':
                temp_zone = int(df_prob.loc[df_prob['payload_id'] == i]['pu_zone'].values[0]) # find zone
                data['loc_zones'].append(copy(temp_zone))   # saving zone
                data['geo_ids'].append(get_geoId(temp_zone, CBGzone_df))

                # Adding time window
                data['time_windows'].append((int(df_prob.loc[df_prob['payload_id'] == i]['pu_tw_lower'].values[0]),
                                    int(df_prob.loc[df_prob['payload_id'] == i]['pu_tw_upper'].values[0])))

                data['payload_ids'].append(copy(i))

                demand = math.ceil(df_prob.loc[df_prob['payload_id'] == i]['weight'].values[0])
                data['demands'].append(copy(demand))
                if commodity != 2 and ship_index =='internal': data['stops'].append(1) 

                service_time = float(df_prob.loc[df_prob['payload_id'] == i]['pu_stop_duration'].values[0])
                data['stop_durations'].append(copy(service_time))

            elif prob_type == 'pickup_delivery':
                temp_zone_d = int(df_prob.loc[df_prob['payload_id'] == i]['del_zone'].values[0]) # find delivery zone
                temp_zone_p = int(df_prob.loc[df_prob['payload_id'] == i]['pu_zone'].values[0]) # find pickup zone
                # Adding pickup and delivery zone to data frame
                data['loc_zones'].append(copy(temp_zone_p))
                data['loc_zones'].append(copy(temp_zone_d))
                data['geo_ids'].append(get_geoId(temp_zone_p, CBGzone_df))
                data['geo_ids'].append(get_geoId(temp_zone_d, CBGzone_df))

                # Adding time pickup and delivery windows
                data['time_windows'].append((int(df_prob.loc[df_prob['payload_id'] == i]['pu_tw_lower'].values[0]),
                                    int(df_prob.loc[df_prob['payload_id'] == i]['pu_tw_upper'].values[0])))
                data['time_windows'].append((int(df_prob.loc[df_prob['payload_id'] == i]['del_tw_lower'].values[0]),
                                    int(df_prob.loc[df_prob['payload_id'] == i]['del_tw_upper'].values[0])))


                data['payload_ids'].append(copy(i))
                data['payload_ids'].append(copy(i))

                demand = math.ceil(df_prob.loc[df_prob['payload_id'] == i]['weight'].values[0])
                data['demands'].append(copy(demand))
                data['demands'].append(copy(-1 * demand))
                if commodity != 2 and ship_index =='internal':
                    data['stops'].append(1)  # Add stop for pickup
                    data['stops'].append(1)  # Add stop for delivery

                # Add pickup service time and delivery service time
                service_time = float(df_prob.loc[df_prob['payload_id'] == i]['pu_stop_duration'].values[0])
                data['stop_durations'].append(copy(service_time))
                service_time = float(df_prob.loc[df_prob['payload_id'] == i]['del_stop_duration'].values[0])
                data['stop_durations'].append(copy(service_time))

                # Assuming that if a carrier has pickup_delivery jobs it only has that
                data['pickups_deliveries'].append([index, index+1])
                index += 2

        # After gathering demand by location, change demand of depot to full load at the depot
        #TODO: this need to be double checked for a problem where one vehile is not enough to deliver everything
        # Below did not work if more than 1 vehicle is needed to handle depot demand

        b_timing = time()
        sel_tt= tt_df[(tt_df['origin'].isin(data['geo_ids'])) &
                        (tt_df['destination'].isin(data['geo_ids']))]

        sel_ec= ec_df[(ec_df['origin'].isin(data['geo_ids'])) &
                        (ec_df['destination'].isin(data['geo_ids']))]
        
        sel_dist = dist_df[(dist_df['Origin'].isin(data['loc_zones'])) &
                        (dist_df['Destination'].isin(data['loc_zones']))]
        # print('len of tt ', len(sel_tt), ' len of dist ', len(sel_dist))

        ## Saving travel time and distance dataframes for testing
        # sel_tt.to_csv('Carrier_Tour_Plan/test_data/sel_tt_pickup_delivery.csv', index=False)
        # sel_dist.to_csv('Carrier_Tour_Plan/test_data/sel_dist_pickup_delivery.csv', index=False)

        max_tt = 0
        mac_ec = 0
        for i in range(len(data['loc_zones'])):
            time_l = []
            energy_l = []
            travel_time = 0
            energy_cost = 0

            for j in range(len(data['loc_zones'])):
                if i == j or data['loc_zones'][i] == data['loc_zones'][j]:
                    time_l.append(0)
                    energy_l.append(0)
                else:
                    travel_time = tt_cal(data['loc_zones'][i], data['loc_zones'][j],
                                        data['geo_ids'][i], data['geo_ids'][j], sel_tt, sel_dist)
                    energy_cost = ec_cal(data['loc_zones'][i], data['loc_zones'][j],
                                        data['geo_ids'][i], data['geo_ids'][j], sel_ec, sel_dist, ec_vehicletype_df, veh)
                    time_l.append(int(travel_time))
                    energy_l.append(int(energy_cost))
                    if travel_time > max_tt: max_tt = copy(travel_time)
                    if energy_cost > mac_ec: mac_ec = copy(energy_cost)

            data['time_matrix'].append(copy(time_l))
            data['energy_matrix'].append(copy(energy_l))

        # print("calculating matrix time, ", time()-b_timing)
        # print('max travel time seen: ', max_tt)

        # We assume first value in graph is medium duty and second is duty
        # Adding vehicle capacities
        data['vehicle_capacities'] = []
        data['vehicle_ids'] = []
        data['vehicle_types'] = []
        
        # TODO: this will need to change is we have stop durations for commodity type 2
        if commodity != 2 and ship_index =='internal':
            prefix = ''
            if commodity == 1: prefix = 'bulk'
            elif commodity == 3: prefix= 'interm_food'
            elif commodity == 4: prefix= 'mfr_goods'
            elif commodity == 5: prefix = 'other'

            # stop_df = pd.read_csv('../../../FRISM_input_output_AT/Survey_Data/' + prefix + '_stops_distribution.csv')
            stop_df = pd.read_csv(path_stops + prefix + '_stops_distribution.csv')

        #################### KJ added for veh_tech
        veh_index= veh.split("_")[0]+"_"+veh.split("_")[1]
        veh_id= int(f_prob[veh_index+"_start_id"].values[0])
        veh_capacity =int(v_df[v_df['veh_type_id'] == veh]['payload_capacity_weight'].values[0])
        for i in range(0, int(f_prob[veh_index].values[0])):
            data['vehicle_capacities'].append(int(veh_capacity))
            data['vehicle_ids'].append(veh_id)
            data['vehicle_types'].append(veh) 
            veh_id += 1

            if commodity != 2 and ship_index =='internal':
                    prob = random.uniform(0, 1)
                    temp = stop_df[stop_df.Cum_Prob >= prob].reset_index()
                    max_stops = temp.loc[0,'Num_Trips_per_Tour']
                    slack_stops = temp.loc[len(temp)-1, 'Num_Trips_per_Tour']
                    data['vehicle_max_stops'].append(int(max_stops))
                    data['vehicle_slack_stops'].append(int(slack_stops))

        data['num_vehicles'] = int(f_prob[veh_index].values[0])

        # print("veh_capacity: ", veh_capacity, " num_veh: ", data['num_vehicles'])
        data['depot'] = 0

        # print(data)
        # Saving dictionary for testing purposes
        # with open('test_data/b2b_pickup_delivery_internal.pickle', 'wb') as handle:
        #     pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    except Exception as e:
        print('Could not build data dictionary for: ', carrier_id, 'and vehicle ', veh , ' : ', e)
        return {}

    return data




def input_files_processing(travel_file, energy_file, energy_vehicle_file, dist_file, CBGzone_file, carrier_file, payload_file, vehicleType_file):
    """Processes input files.

    Reads in input files and processes them to generate dataframe with necessary to generate tours for
    vehicles.

    Args:
        travel_file: file with origin-destination travel time information.
        energy_file: file with origin-destination energy cost information.
        energy_vehicle_file: file with average energy cost by vehicle type.
        dist_file: file with origin-destination distance information.
        CBGzone_file: file that maps mesozones ids to geo ids.
        carrier_file: file with carrier information.
        payload_file: file with payload information.
        vehicleType_file: file with vehicle type information

    Returns:
        tt_df: origin-destination travel time dataframe.
        dist_df: origin-destination distance dataframe.
        CBGzone_df: dataframe that maps mesozones to geo ids.
        c_df: carrier information dataframe.
        p_df: paylaod information dataframe.
        v_df: dataframe with vehicle type information (capacity, weight, diezel or electric, ...)
        vc_df: dataframe with individual vehicle information (id, capacity, ...)
    """
    try:
        # KJ: read travel time, distance, zonal file as inputs  # Slow step
        tt_df = pd.read_csv(travel_file, compression='gzip', header=0, sep=',', quotechar='"', on_bad_lines='skip')
        # ec_df = pd.read_csv(energy_file, compression='gzip', header=0, sep=',', quotechar='"', on_bad_lines='skip')
        
        
        ec_df = pd.read_csv(energy_file)
        ec_vehicletype_df = pd.read_csv(energy_vehicle_file)
        
        dist_df = pd.read_csv(dist_file)  # Slow step
        CBGzone_df = gp.read_file(CBGzone_file)

        # We need to know the depot using the carrier file
        c_df = pd.read_csv(carrier_file)
        c_df = c_df.dropna(axis=1, how='all')   # Removing all nan
        #c_df = c_df[c_df["num_veh_type_1"]>0]  # Removing carriers don't have vehicles (Temporary solution)- need to check Shipment code

        # reading payload definition
        p_df = pd.read_csv(payload_file)
        p_df = p_df.dropna(axis=1, how='all')   # Removing all nan

        # Removing nans
        c_df = c_df.fillna(0); # Fill all nan with zeros


        # Removing nans
        p_df['carrier_id'] = p_df['carrier_id'].astype(str)
        p_df['sequence_id'] = np.nan
        p_df['tour_id'] = np.nan
        p_df['pu_arrival_time'] = np.nan
        p_df['del_arrival_time'] = np.nan
        p_df = p_df.fillna(int(0))

        # Adding in additional colums for vehicle tours
        # Changing tour id and sequence id into ints
        p_df['tour_id'] = p_df['tour_id'].astype(int)
        p_df['sequence_id'] = p_df['sequence_id'].astype(int)

        # Reading in vehicle information
        v_df = pd.read_csv(vehicleType_file)
        v_df = v_df.dropna(axis=1, how='all')   # Removing all nan
        ################ KJ added for veh_tech
        veh_list=p_df["veh_type"].unique()
        veh_list = [ x.split("_")[0]+"_"+x.split("_")[1] for x in veh_list]
        veh_list = list(dict.fromkeys(veh_list))
        # Create vehicle sequence vehicle ID
        vc_df = pd.DataFrame()
        vc_df['carrier_id']=c_df['carrier_id']
        for key in veh_list:
            vc_df[key]=c_df[key]
            vc_df[key+'_start_id']=np.nan
        vc_df = vc_df.fillna(int(0))
        vc_df = vc_df.reset_index()
        n=0
        for i in range (0, vc_df.shape[0]):
            for j in range(0,len(veh_list)):
                if j==0:
                    veh_type_id=veh_list[j]
                    vc_df.loc[i,veh_type_id+"_start_id"]=n
                else:
                    veh_type_id=veh_list[j]
                    n=n+ vc_df.loc[i,veh_list[j-1]]
                    vc_df.loc[i,veh_type_id+"_start_id"]=n 
                if j== len(veh_list)-1:
                    n=  n + vc_df.loc[i,veh_type_id] 
        return tt_df, ec_df, dist_df, CBGzone_df, c_df, p_df, v_df, vc_df, ec_vehicletype_df
    except Exception as e:
        prefix = ''
        if 'gzipped' in str(e): prefix = 'Travel time file'
        print('Could not parse input files: exception: ', prefix, e)
        return None




def form_solve(data, tour_df, carr_id, carrier_df, payload_df, prob_type, count_num, ship_type, c_prob, 
                df_prob, max_time, index, comm, error_list, results_df, w1, w2):
    # w1, w2 are the weight related to the time and energy cost respectively
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                        data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a time transit callback.
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['time_matrix'][from_node][to_node] + data['stop_durations'][from_node]
    
    # Create and register a energy transit callback.
    def energy_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['energy_matrix'][from_node][to_node]
    
    def create_combined_cost_callback(manager, data):
        """Creates a combined time and energy cost callback."""
        def combined_cost_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            time_cost = data['time_matrix'][from_node][to_node] + data['stop_durations'][from_node]
            energy_cost = data['energy_matrix'][from_node][to_node]
            combined_cost = w1 * time_cost + w2 * energy_cost
            return combined_cost
        return combined_cost_callback
    
    # Add Capacity constraint.
    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]
    
    combined_cost_callback = create_combined_cost_callback(manager, data)
    transit_callback_index = routing.RegisterTransitCallback(combined_cost_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Time Windows constraint.
    # time_dim = 'Time'
    # routing.AddDimension(
    #     transit_callback_index,
    #     30,  # allow waiting time
    #     86400,  # maximum time per vehicle, JU: set to minutes in a day assuming no trip goes beyod a day
    #     False,  # Don't force start cumul to zero.
    #     time_dim)
    # time_dimension = routing.GetDimensionOrDie(time_dim)

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    time_dim = 'Time'
    routing.AddDimension(
        time_callback_index,
        30,  # Allow waiting time
        86400,  # Maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time_dim)

    time_dimension = routing.GetDimensionOrDie(time_dim)


    if index == 'internal' and comm != 2:
                # Add Capacity constraint.
        def stops_callback(from_index):
            """Returns the stops of the node."""
            # Convert from routing variable Index to demands NodeIndex.
            from_node = manager.IndexToNode(from_index)
            return data['stops'][from_node]

        stops_callback_index = routing.RegisterUnaryTransitCallback(
            stops_callback)
        routing.AddDimensionWithVehicleCapacity(
            stops_callback_index,
            0,  # null capacity slack
            data['vehicle_slack_stops'],  # vehicle maximum capacities
            True,  # start cumul to zero
            'Stops')
        
        stop_dimension = routing.GetDimensionOrDie('Stops')
        
        penalty_stop = 100000
        for v in range(data['num_vehicles']):
            stop_dimension.SetCumulVarSoftUpperBound(routing.End(v), data['vehicle_max_stops'][v], penalty_stop)
    #     # Allow to go over number of stops
        penalty_drop = 100000
        for node in range(1, len(data['time_matrix'])):
            routing.AddDisjunction([manager.NodeToIndex(node)], penalty_drop)

    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == data['depot']:
            continue
        index = manager.NodeToIndex(location_idx)

        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Add time window constraints for each vehicle start node.
    depot_idx = data['depot']
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            data['time_windows'][depot_idx][0],
            data['time_windows'][depot_idx][1])

    if prob_type == 'pickup_delivery':
        # Define Transportation Requests.
        for request in data['pickups_deliveries']:
            pickup_index = manager.NodeToIndex(request[0])
            delivery_index = manager.NodeToIndex(request[1])
            routing.AddPickupAndDelivery(pickup_index, delivery_index)
            routing.solver().Add(
                routing.VehicleVar(pickup_index) == routing.VehicleVar(
                    delivery_index))
            routing.solver().Add(
                time_dimension.CumulVar(pickup_index) <=
                time_dimension.CumulVar(delivery_index))

    demand_callback_index = routing.RegisterUnaryTransitCallback(
            demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Instantiate route start and end times to produce feasible times.
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i)))

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.time_limit.seconds = max_time   #set a time limit of 900 seconds for a search

    s_time = time()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    #print('before solving the problem')
    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    solve_time = time() - s_time
    # print('\nTime to solve is: ', solve_time)
    #print('after solving the problem')
    # Print solution on console.
    if solution:
        try:
            used_veh = print_solution(data, manager, routing, solution, tour_df, carr_id, carrier_df,
                                  payload_df, prob_type, count_num, ship_type, c_prob, df_prob, results_df)
            # print('\n')
            return used_veh
        except Exception as e:
            veh = data['vehicle_types'][0]
            print('Could not write out solution for : ', carr_id, ' : ', e)
            error_list.append([carr_id, veh, comm, index, e])

    else:
        st = routing.status()
        message = ''
        if st == 0:
            message = 'PROBLEM NOT YET SOLVED'
        elif st == 2:
            message = 'NO SOLUTION FOUND FOR PROBLEM'
        elif st == 3:
            message = 'TIME LIMIT REACHED BEFORE FINDING A SOLUTION'
        elif st ==4:
            message = 'MODEL, PARAMETERS, OR FLAGS ARE INVALID'

        veh = data['vehicle_types'][0]
        print('Could not find a solution for carrier: ', carr_id, ' with prob type', prob_type, ' and veh type ', veh,
        ' comm ', comm, ' index ', index, ': ', message)
        error_list.append([carr_id, veh, comm, index, message])
        # print('\n')
        return []


def print_solution(data, manager, routing, solution, tour_df, carr_id, carrier_df, payload_df, prob_type,
                   count_num, ship_type, c_prob, df_prob, results_df):

    global tour_id
    global payload_i
    global depot_i
    global job_id
    global sim_seq
    used_veh = []

    # print(f'Objective: {solution.ObjectiveValue()}')
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    for vehicle_id in range(data['num_vehicles']):
        route_load = 0
        index = routing.Start(vehicle_id)
        start_loc = manager.IndexToNode(index)
        next_loc = manager.IndexToNode(solution.Value(routing.NextVar(index)))

        # Print out solution from vehicles that left the dept
        if start_loc != next_loc:
            used_veh.append(vehicle_id)
            start_time = solution.Min(time_dimension.CumulVar(index))

            # Adding tour, carrier info to csv
            # Format for tour csv: ['tour_id', 'departureTimeInSec', 'departureLocation_zone', 'maxTourDurationInSec']
            # Fomat for carrier csv: ['carrierId','tourId', 'vehicleId', 'vehicleTypeId','depot_zone']
            depot_x = c_prob['c_x'].values[0]
            depot_y = c_prob['c_y'].values[0]

            tour_df.loc[tour_id] = [tour_id, start_time*60, data['loc_zones'][manager.IndexToNode(index)], 3600,
                                    depot_x, depot_y]
            carrier_df.loc[tour_id] = [carr_id, tour_id, data['vehicle_ids'][vehicle_id],
                                       data['vehicle_types'][vehicle_id], data['loc_zones'][manager.IndexToNode(index)],
                                       depot_x,depot_y]

            plan_output = 'Route for vehicle {0} with id {1}:\n'.format(vehicle_id, data['vehicle_ids'][vehicle_id])
            plan_output_l = 'Load for vehicle {}:\n'.format(vehicle_id)
            seqId = 0

            if prob_type == 'delivery':
                beg_index = payload_i   # to be used to adjust load info for delivery problems
                node_list = []

            node_ls = []
            load_ls = []
            while not routing.IsEnd(index):

                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)
                plan_output += '{0} Time({1},{2}) -> '.format(
                    manager.IndexToNode(index), solution.Min(time_var),
                    solution.Max(time_var))

                # Load info
                route_load += data['demands'][node_index]
                load_ls.append(route_load)
                # Add processing for depot
                
                if node_index == 0:
                    payload_df.loc[payload_i] = [str(count_num) + '_d' + ship_type + str(depot_i), int(seqId), int(tour_id),
                                                 int(1),
                                                 int(data['demands'][node_index]), int(route_load), 1,
                                                 int(data['loc_zones'][node_index]),
                                                 int(solution.Min(time_var) * 60),
                                                 int(0 * 60),
                                                 int(0 * 60),
                                                 int(0 * 60), depot_x, depot_y]
                    # divided by 60 for integrity
                    depart_time = int(solution.Min(time_var))

                elif(node_index != 0):
                    id_payload = str(data['payload_ids'][node_index-1])
                    loc_x = 0
                    loc_y = 0
                    if prob_type == 'pickup':
                        loc_x = df_prob[df_prob['payload_id'] == id_payload]['pu_x'].values[0]
                        loc_y = df_prob[df_prob['payload_id'] == id_payload]['pu_y'].values[0]

                    elif prob_type == 'delivery':
                        loc_x = df_prob[df_prob['payload_id'] == id_payload]['del_x'].values[0]
                        loc_y = df_prob[df_prob['payload_id'] == id_payload]['del_y'].values[0]

                    elif prob_type == 'pickup_delivery':
                        if data['demands'][node_index] > 0:
                            loc_x = df_prob[df_prob['payload_id'] == id_payload]['pu_x'].values[0]
                            loc_y = df_prob[df_prob['payload_id'] == id_payload]['pu_y'].values[0]
                        elif data['demands'][node_index] < 0:
                            loc_x = df_prob[df_prob['payload_id'] == id_payload]['del_x'].values[0]
                            loc_y = df_prob[df_prob['payload_id'] == id_payload]['del_y'].values[0]

                    payload_df.loc[payload_i] = [str(data['payload_ids'][node_index-1]), int(seqId), int(tour_id), int(1),
                                                 int(data['demands'][node_index]), int(route_load), 1, int(data['loc_zones'][node_index]),
                                                int(solution.Min(time_var)*60),
                                                 int(data['time_windows'][node_index][0]*60),
                                                int(data['time_windows'][node_index][1]*60),
                                                 int(data['stop_durations'][node_index]*60),
                                                 loc_x, loc_y]
                payload_i += 1
                seqId += 1


                if prob_type == 'delivery': node_list.append(copy(node_index))
                else:
                    plan_output_l += ' {0} Load({1}) -> '.format(node_index, route_load)

                pre_node_index = node_index
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                current_node_index = manager.IndexToNode(index)
                node_ls.append([pre_node_index, current_node_index])

            
            # Node of depot
            node_index = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)

            row = {
            "MonteCarlo Iteration": sim_seq,
            "job_id": job_id,
            "tour_id": tour_id,
            "Vehicle ID": vehicle_id,
            "Route": str(node_ls),  # Convert list to string for storage
            "Time": solution.Min(time_var),
            "Load": str(load_ls),  # Convert list to string for storage
            "Stop_duration_time": str(data['stop_durations']),
            "Current Distance Matrix": str(data['time_matrix']),  # Convert matrix to string
            "time_windows": str(data['time_windows']),
            "Departure_time": depart_time
            }
            results_df.loc[len(results_df)] = row  # Using loc to append avoids the AttributeError

            ['payloadId','sequenceRank','tourId','payloadType','weightInlb','cummulativeWeightInlb',
                                         'requestType','locationZone','estimatedTimeOfArrivalInSec','arrivalTimeWindowInSec_lower',
                                         'arrivalTimeWindowInSec_upper','operationDurationInSec', 'locationZone_x', 'locationZone_y']
            payload_df.loc[payload_i] = [str(count_num) + '_d' + ship_type + str(depot_i) + '_', int(seqId), int(tour_id),
                                         int(1),
                                         int(data['demands'][node_index]), int(route_load), 1,
                                         int(data['loc_zones'][node_index]),
                                         int(solution.Min(time_var) * 60),
                                         int(0 * 60),
                                         int(0 * 60),
                                         int(0 * 60),
                                         depot_x, depot_y]


            if prob_type == 'delivery':
                tot_load = route_load
                end_index = payload_i   # to be used to adjust load info for delivery problems
                # payload_df.loc[beg_index]['cummulativeWeightInlb'] = tot_load

                l = 0
                for k in range(beg_index, end_index):
                    temp_load = tot_load - payload_df.loc[k]['weightInlb']
                    payload_df.loc[k,('cummulativeWeightInlb')] = temp_load
                    if k == beg_index: payload_df.loc[k,('weightInlb')] = temp_load
                    else:
                        payload_df.loc[k,('weightInlb')] = -1 * payload_df.loc[k]['weightInlb']

                    plan_output_l += ' {0} Load({1}) -> '.format(node_list[l], temp_load)
                    tot_load = copy(temp_load)
                    l += 1

                # When the vehicle goes back to the depot, it's load is zero
                payload_df.loc[end_index,'cummulativeWeightInlb'] = 0
                route_load = temp_load

                #Increment the load index
            payload_i +=1

            plan_output += '{0} Time({1},{2})'.format(manager.IndexToNode(index),
                                                        solution.Min(time_var),
                                                        solution.Max(time_var))
            plan_output_l += ' {0} Load({1})\n'.format(manager.IndexToNode(index),
                                                 route_load)
            if prob_type != 'delivery': plan_output += 'Time of the route: {}min'.format(
                solution.Min(time_var) - start_time)

            # print(plan_output)
            # print(plan_output_l)
            total_time += solution.Min(time_var)- start_time
            tour_id += 1 # Incrementing for the tour id
            depot_i +=1
    
    # print('Used Vehicles: ', used_veh)
    # print('Total time of all routes: {}min'.format(total_time))

    return used_veh

def vehicle_routing_result_summary(dir_out, ship_type, count_num, file_index, target_year, scenario, num_montecarlo):



    df_resultssim = pd.read_csv(dir_out+"{0}_county{1}_resultsim{2}_s{3}_y{4}.csv".format(ship_type, count_num, str(file_index), scenario, target_year))

    def calculate_route_distance(route, distance_matrix, stop_duration_matrix):
        """
        Calculate the total distance of a route using the given distance matrix.

        Parameters:
        - route: A list of lists, where each sublist represents a movement from one node to another.
        - distance_matrix: A 2D list representing the distance between nodes.

        Returns:
        - Total distance of the route.
        """
        total_distance = 0
        for movement in route:
            start_node, end_node = movement
            total_distance += distance_matrix[start_node][end_node] + stop_duration_matrix[start_node]
        return total_distance


    def time_window_check(route, distance_matrix, stop_duration_matrix, time_window_matrices, departure_time):
        current_time = departure_time
        for movement in route:
            start_node, end_node = movement
            if start_node == 0:
                current_time = time_window_matrices[end_node][0] - distance_matrix[start_node][end_node] - stop_duration_matrix[start_node]
            current_time += distance_matrix[start_node][end_node] + stop_duration_matrix[start_node]
            if end_node != 0: 
                if (current_time <  time_window_matrices[end_node][0]) or (current_time > time_window_matrices[end_node][1]):
                    print(start_node, end_node)
                    return False
        return True

    final_results = pd.DataFrame()

    for job_id_num in df_resultssim.job_id.unique():
        full_data = df_resultssim[df_resultssim['job_id'] == job_id_num]
        routes = {}
        distance_matrices = {}
        stop_duration_matrices = {}
        time_window_matrices = {}
        departure_time_matrices = {}

        for index, row in full_data.iterrows():
            iteration = row['MonteCarlo Iteration']

            # Parsing the 'Route' and 'Current Distance Matrix' from string to actual Python lists
            # Assuming the structure is consistent and can be safely evaluated
            route = eval(row['Route'])
            distance_matrix = eval(row['Current Distance Matrix'])
            stop_duration_matrix = eval(row['Stop_duration_time'])
            time_windows_matirx = eval(row['time_windows'])
            departure_time = row['Departure_time']

            # Storing routes and distance matrices
            if iteration not in routes:
                routes[iteration] = []
            routes[iteration].append(route)

            # Assuming each iteration has the same distance matrix, so only store it once
            if iteration not in distance_matrices:
                distance_matrices[iteration] = distance_matrix

            if iteration not in stop_duration_matrices:
                stop_duration_matrices[iteration] = stop_duration_matrix

            if iteration not in time_window_matrices:
                time_window_matrices[iteration] = time_windows_matirx

            if iteration not in departure_time_matrices:
                departure_time_matrices[iteration] = departure_time

        # Calculate the total distance for each route in each iteration's distance matrix
        distance_results = []
        # Iterating over each combination of route iteration and distance matrix iteration
        for route_iter, routes_list in routes.items():
            for dist_matrix_iter, dist_matrix in distance_matrices.items():
                for route_index, route in enumerate(routes_list):
                    stop_duration_matrix = stop_duration_matrices[dist_matrix_iter]
                    time_window_matrix = time_window_matrices[dist_matrix_iter]
                    stop_departure_time = departure_time_matrices[dist_matrix_iter]
                    total_distance = calculate_route_distance(route, dist_matrix, stop_duration_matrix)

                    timewindow_check = time_window_check(route, dist_matrix, stop_duration_matrix, time_window_matrix, stop_departure_time)
                    distance_results.append({
                        "Route Iteration": route_iter,
                        "Route Index": route_index,
                        "Distance Matrix Iteration": dist_matrix_iter,
                        "Total Distance": total_distance,
                        "time_window_check": timewindow_check
                    })

        # Convert the results into a DataFrame for better visualization
        df_results = pd.DataFrame(distance_results)
        time_check_index = df_results[df_results['time_window_check'] == False]['Route Iteration'].unique()
        df_results = df_results[~df_results['Route Iteration'].isin(time_check_index)]
        df_stochastic_distance = df_results.groupby(["Route Iteration","Distance Matrix Iteration"])["Total Distance"].sum().reset_index()
        df_stochastic_distance = df_stochastic_distance.groupby("Route Iteration")["Total Distance"].std().reset_index()

        df_stochastic_distance = df_stochastic_distance.sort_values(by="Total Distance", ascending=True).reset_index(drop=True)
        best_route_seq = df_stochastic_distance['Route Iteration'][0]
        df_best_tour = df_resultssim[(df_resultssim['job_id'] == job_id_num) & (df_resultssim['MonteCarlo Iteration'] == best_route_seq)][['tour_id','MonteCarlo Iteration']]
        final_results = pd.concat([final_results, df_best_tour], ignore_index=True)

    final_results.columns = ['tour_id', 'sim_seq']
    
    carrier_name = f"{dir_out}{ship_type}_county{count_num}_carrier_s{scenario}_y{target_year}"
    tour_name = f"{dir_out}{ship_type}_county{count_num}_freight_tours_s{scenario}_y{target_year}"
    load_name = f"{dir_out}{ship_type}_county{count_num}_payload_s{scenario}_y{target_year}"

    df_carrier = pd.DataFrame()
    df_tour = pd.DataFrame()
    df_load = pd.DataFrame()

    for sim_seq in range(num_montecarlo):
        df_carriertemp = pd.read_csv(f"{carrier_name}_sim{sim_seq}.csv")
        df_tourtemp = pd.read_csv(f"{tour_name}_sim{sim_seq}.csv")
        df_loadtemp = pd.read_csv(f"{load_name}_sim{sim_seq}.csv")

        df_carriertemp['sim_seq'] = sim_seq
        df_tourtemp['sim_seq'] = sim_seq
        df_loadtemp['sim_seq'] = sim_seq

        df_carrier = pd.concat([df_carrier, df_carriertemp], ignore_index=True)
        df_tour = pd.concat([df_tour, df_tourtemp], ignore_index=True)
        df_load = pd.concat([df_load, df_loadtemp], ignore_index=True)

    df_load = df_load.rename(columns = {'tourId':'tour_id'})
    df_carrier = df_carrier.rename(columns = {'tourId':'tour_id'})
    result_df_carrier = pd.merge(df_carrier, final_results, on=['tour_id', 'sim_seq'], how='inner')
    result_df_tour = pd.merge(df_tour, final_results, on=['tour_id', 'sim_seq'], how='inner')
    result_df_load = pd.merge(df_load, final_results, on=['tour_id', 'sim_seq'], how='inner')

    result_df_carrier = result_df_carrier.sort_values(by=['tour_id'])
    result_df_tour = result_df_tour.sort_values(by=['tour_id'])
    result_df_load = result_df_load.sort_values(by=['tour_id','sequenceRank'])

    result_df_carrier.to_csv(f"{carrier_name}.csv")
    result_df_tour.to_csv(f"{tour_name}.csv")
    result_df_load.to_csv(f"{load_name}.csv")

def main(args=None):
    """Main function.

    Takes input files names from console specifing the parameters of the vehicle routing problem.

    Args:
        -cy or --county_number: the county number in the scenario of interest
        -t or --travel_time_time: file with travel times between origin and destination census block group id
        -ef or --energy_file: file with origin-destination energy cost information.
        -evf or --energy_vehicle_file: file with average energy cost by vehicle type.
        -d or --distance_file: file with distance between origin and destination mesozones
        -ct or --freight_centroid_file: file that maps census block group ids to mesozones
        -cr or --carrier_file: file with carriers' information
        -pl or --payload_file: file with payloads' information
        -vt or --vehicle_type_file: file with vehicle type information
        -st or --scenario: specifies the name of the scenario 
        -yt or --analysis_year: year to be simulated in 20XX format
        -sr or --sample_rate: sample rate
        -ps or --path_to_max_stops_per_commodity_files: path to folder containing csv files for max stops per commodity 
        -mt or --max_time_to_solve_problem: max time in seconds to solve vehicle routing problem
        -fn or --separate_file_index: a separate number to use to save output files (This is an optional parameter)
    """
    try:
        parser = ArgumentParser()
        parser.add_argument("-cy", "--county-number", dest="county_num",
                            help="an integer indicating the county number", required=True, type=int)
        parser.add_argument("-t", "--travel_time_file", dest="travel_file",
                            help="travel time file in gz format", required=True, type=str)
        parser.add_argument("-ef", "--energy_file", dest="energy_file",
                            help="energy cost file in gz format", required=True, type=str)
        parser.add_argument("-evf", "--energy_vehicle_file", dest="energy_vehicle_file",
                            help="average energy cost by veh file in gz format", required=True, type=str)
        parser.add_argument("-d", "--distance_file", dest="dist_file",
                            help="distance file in csv format", required=True, type=str)
        parser.add_argument("-ct", "--freight_centroid_file", dest="CBGzone_file",
                            help="file that maps census block group ids to mesozones in geojson format", required=True, type=str)
        parser.add_argument("-cr", "--carrier_file", dest="carrier_file",
                            help="carrier file in csv format", required=True, type=str)
        parser.add_argument("-pl", "--payload_file", dest="payload_file",
                            help="payload file in csv format", required=True, type=str)
        parser.add_argument("-vt", "--vehicle_type_file", dest="vehicleType_file",
                            help="vehicle type file in csv format", required=True, type=str)
        parser.add_argument("-sn", "--scenario", dest="scenario",
                        help="scenario", required=True, type=str)                
        parser.add_argument("-yt", "--analysis_year", dest="target_year",
                    help="20XX", required=True, type=int)
        parser.add_argument("-sr", "--sample_rate", dest="sample_rate",
                    help="10", required=True, type=int)
        parser.add_argument("-ps", "--path_to_max_stops_per_commodity_files", dest="path_stops",
                    help="max stops per commodity file in csv format", required=True, type=str)  
        # max_time parameter added to tune how long we wait to get an answer to a problem
        parser.add_argument("-mt", "--max_time_to_solve_problem", dest="max_time",
                    help="max time in seconds to solve vehicle routing problem", default=900, type=float)
        parser.add_argument("-fn", "--separate_file_index", dest="file_idx",
                            help="an integer", default=9999, type=str)                        

        args = parser.parse_args()
        file_index=args.file_idx
        count_num = args.county_num     # county number 
        path_stops = args.path_stops    # path to file containing maximum stops per commodity for internal trips
        max_time = args.max_time        # Maximum time in seconds to solve the vehicle routing problem, default is 900 secs
        scenario = args.scenario
        year = args.target_year
        # Saving the created data frames
        if "B2B" in args.payload_file:
            ship_type = "B2B"
        elif "B2C" in args.payload_file:
            ship_type = "B2C"
        # TODO: add a try/catch here in case processing files fails
        tt_df, ec_df, dist_df, CBGzone_df, c_df, p_df, v_df, vc_df, ec_vehicletype_df = input_files_processing(args.travel_file, args.energy_file, args.energy_vehicle_file, args.dist_file, args.CBGzone_file, args.carrier_file, args.payload_file, args.vehicleType_file)
        num_montecarlo = 2

        results_df = pd.DataFrame(columns=["MonteCarlo Iteration", "job_id", "tour_id", "Vehicle ID", "Route", "Time", "Load", "Stop_duration_time", "Current Distance Matrix","time_windows", "Departure_time"])
        job_id_temp = 0
        global job_id
        global sim_seq
        global tour_id
        job_id = 0
        job_num = 0
        for sim_seq in range(num_montecarlo):

            tour_id = 0
            payload_i = 0
            depot_i = 0

            b_time = time()
        
            # data frames for the tour, carrier and payload
            tour_df = pd.DataFrame(columns = ['tour_id', 'departureTimeInSec', 'departureLocation_zone', 'maxTourDurationInSec',
                                            'departureLocation_x','departureLocation_y'])
            # Format for carrier data frame: carrierId,tourId, vehicleId,vehicleTypeId,depot_zone
            carrier_df = pd.DataFrame(columns = ['carrierId','tourId', 'vehicleId', 'vehicleTypeId','depot_zone', 'depot_zone_x', 'depot_zone_y'])
            # format for payload format
            # payloadId, sequenceRank, tourId, payloadType, weightInlb, requestType,locationZone,
            # estimatedTimeOfArrivalInSec, arrivalTimeWindowInSec_lower, arrivalTimeWindowInSec_upper,operationDurationInSec
            payload_df = pd.DataFrame(columns = ['payloadId','sequenceRank','tourId','payloadType','weightInlb','cummulativeWeightInlb',
                                                'requestType','locationZone','estimatedTimeOfArrivalInSec','arrivalTimeWindowInSec_lower',
                                                'arrivalTimeWindowInSec_upper','operationDurationInSec', 'locationZone_x', 'locationZone_y'])

            error_list = []
            error_list.append(['carrier', 'veh', 'commodity', 'index','reason'])
            
            # Add another look for commodity: loop by carrier, vehicle type and commodity type
            # The commodity will decide the limit on number of stops per vehicle:
            # randomly select stops limits and fix slack stop limits to maximum stops possible per commodity
            print('number of carriers is: ', len(p_df['carrier_id'].unique()))
            for carr_id in p_df['carrier_id'].unique():

            

            # for carr_id in ['B2C_2875881_1']:
                # Initialize parameters used for probelm setting
                try:
                    comm = -1
                    veh = ''
                    index= ''
                    veh_types = p_df[(p_df['carrier_id'] == carr_id)].veh_type.unique()
                    c_prob = c_df[c_df['carrier_id'] == carr_id]
                    c_prob = c_prob.dropna()
                    vc_prob = vc_df[vc_df['carrier_id']== carr_id]
                    vc_prob = vc_prob.dropna()
                    vc_prob = vc_prob.reset_index()

                    used_veh = []  # To save a list of used vehicles per carrier

                    for comm in p_df[p_df['carrier_id']==carr_id]['commodity'].unique():
                        for index in p_df[(p_df['carrier_id']==carr_id) & (p_df['commodity']==comm)]['ship_index'].unique():
                            for veh in veh_types:
                                if sim_seq == 0:
                                   job_num += 1
                                   job_id = job_id_temp
                                   job_id_temp += 1
                                else:
                                    job_id = job_id_temp%job_num
                                    job_id_temp += 1
                                # To simplify the problem, look at a small problem with same carrier and same commodity id and same vehicle type
                                df_prob = p_df[(p_df['carrier_id'] == carr_id) & (p_df['veh_type'] == veh) & (p_df['commodity']==comm) & (p_df['ship_index']==index)]
                                df_prob = df_prob.dropna()

                                total_load = sum(df_prob[(df_prob.carrier_id == carr_id) & (df_prob.veh_type == veh)]['weight'])
                                veh_capacity = 0
                                valid = True    # Boolean to indicate if the problem is valid
                                veh_num = 0
                                veh_capacity = int(v_df[v_df['veh_type_id'] == veh]['payload_capacity_weight'].values[0])
                                veh_num = int(vc_prob[veh.split("_")[0]+"_"+veh.split("_")[1]].values[0])

                                # temporary QC check
                                # print ("Carrier Id: {}".format(carr_id))    
                                # print ("veh_type: {0} veh_capacity: {1} veh_num: {2}".format(veh,veh_capacity,veh_num))    

                                max_veh_cap = veh_num*veh_capacity  # variable for saving the vehicle capacity

                                # Getting list of commodities carried by vehicle type
                                comm_list = v_df[v_df['veh_type_id'] == veh]['commodities'].values[0].split(', ')
                                comm_list[0] = comm_list[0][1:]
                                comm_list[len(comm_list)-1] = comm_list[len(comm_list)-1][:-1]

                                # Checking if problem is well formulated

                                if len(df_prob) == 0:
                                    # print('Could not solve problem for carrier ', carr_id, ': NO PAYLOAD INFO')
                                    # print('\n')
                                    error_list.append([carr_id, veh, comm, index, 'NO PAYLOAD INFO'])
                                    valid = False
                                
                                prob_type = str(df_prob.iloc[0]['job'])

                                if prob_type != 'delivery' and prob_type != 'pickup' and prob_type != 'pickup_delivery':
                                    print('Could not solve problem for carrier ', carr_id, ': INCORRECT PROBLEM TYPE: ', prob_type)
                                    print('\n')
                                    error_list.append([carr_id, veh, comm, index, 'INCORRECT PROBLEM TYPE: '+ str(prob_type)])
                                    valid = False
                                
                                elif path_stops == '':
                                    print('Could not solve problem for carrier ', carr_id, ': NO PATH TO STOPS FILE')
                                    print('\n')
                                    error_list.append([carr_id, veh, comm, index, 'NO PATH TO STOPS FILE'])
                                    valid = False

                                elif not any(str(int(comm)) == x  for x in comm_list):
                                    print('Could not solve problem for carrier ', carr_id, ': COMMODITY ', comm, ' NOT CARRIED BY VEHICLE TYPE ', veh)
                                    print('\n')
                                    error_list.append([carr_id, veh, comm, index, 'COMMODITY DOES NOT MATCH VEHICLE'])
                                    valid = False

                                elif len(vc_prob) == 0:
                                    print('Could not solve problem for carrier ', carr_id, ': NO VEHICLE TYPE INFO')
                                    print('\n')
                                    error_list.append([carr_id, veh, comm, index, 'NO VEHICLE TYPE INFO'])
                                    valid = False

                                elif len(c_prob) == 0:
                                    print('Could not solve problem for carrier ', carr_id, ': NO CARRIER INFO')
                                    print('\n')
                                    error_list.append([carr_id, veh, comm, index,'NO CARRIER INFO'])
                                    valid = False
                                
                                elif total_load > max_veh_cap:
                                    df_prob.sort_values(by=['weight'])
                                    valid = False
                                    print("Load is larger than vehicle capacity")
                                    print('Load is: ', total_load, ' num of veh: ', veh_num, ' total veh capacity is: ', max_veh_cap)
                                    while valid == False and (len(df_prob) > 0):
                                        message = 'Dropped payload : ', df_prob.iloc[-1]['payload_id'], ' with weight: ', df_prob.iloc[-1]['weight']
                                        error_list.append([carr_id, veh, message])
                                        print(message)
                                        df_prob = df_prob.iloc[:-1 , :]
                                        if  sum(df_prob['weight']) <= max_veh_cap:
                                            valid = True
                                    
                                    if not valid:
                                        print('Could not solve problem for carrier ', carr_id, ': SINGLE PAYLOAD WEIGHT GREATER THAN VEHICLE CAPACICY')
                                        print('\n')
                                        error_list.append([carr_id, veh, 'SINGLE PAYLOAD WEIGHT GREATER THAN VEHICLE CAPACICY'])
                                
                                if valid:

                                    # Depot location
                                    depot_loc = c_prob.loc[c_prob['carrier_id'] == carr_id]['depot_zone'].values[0]

                                    print('Solvign problem for carrier ', carr_id, ' with prob type', prob_type, ' and veh type ', veh,
                                    ' comm: ', comm, ' index: ', index)
                                    
                                    #saving small files for testing purposes:
                                    # df_prob.to_csv('Carrier_Tour_Plan/test_data/df_prob_pickup_delivery.csv', index=False)
                                    # v_df.to_csv('Carrier_Tour_Plan/test_data/v_df_pickup_delivery.csv', index=False)
                                    # vc_prob.to_csv('Carrier_Tour_Plan/test_data/vc_prob_pickup_delivery.csv', index=False)
                                    # c_prob.to_csv('Carrier_Tour_Plan/test_data/c_prob_pickup_delivery.csv', index=False)
                                    
                                    data = create_data_model(df_prob, depot_loc, prob_type, v_df, vc_prob, c_prob, carr_id,
                                                            CBGzone_df, tt_df, ec_df, ec_vehicletype_df, dist_df, veh, comm, index, path_stops)

                                    #print('the model: \\n')
                                    #print(data)
                                    # Now solving the problem
                                    if not data:
                                        print('model returned was none')
                                        error_list.append([carr_id, veh, comm, index, 'could not create data dictionary'])
                                    else:
                                        print('model was formulated correctly')

                                        data['time_matrix_origin'] = data['time_matrix'].copy()
                                        solutions = []
                                        
                                        #     # float_number = random.uniform(1, 1.5)

                                        datatemp = [[int(x * random.uniform(0.8, 1.2)) for x in row] for row in data['time_matrix_origin']]
                                        data['time_matrix'] = datatemp
                                        print('datatemp', datatemp)
                                        print('\n')
                                        print('time_matrix_origin', data['time_matrix_origin'])
                                        print('time_matrix',data['time_matrix'])
                                        # print(data['time_matrix'])
                                    #     used_veh = form_solve(data, tour_df, carr_id, carrier_df, payload_df,
                                    #                             prob_type, count_num, ship_type, c_prob, df_prob, max_time, index, comm,
                                    #                             tour_id, payload_i, depot_i)
                                    #     print('used veh: ', used_veh)
                                    #     # Saving small output files for testing purposes
                                    #     # tour_df.to_csv('test_data/tour_df_pickup_delivery_internal.csv', index=False)
                                    #     # carrier_df.to_csv('test_data/carrier_df_pickup_delivery_internal.csv', index=False)
                                    #     # payload_df.to_csv('test_data/payload_df_pickup_delivery_internal.csv', index=False)

                                    #     # Reduce number of vehicles depending on those useds
                                    #     if len(used_veh) > 0:
                                    #         veh_id = veh.split("_")[0]+"_"+veh.split("_")[1]
                                    #         vc_prob.loc[0,veh_id] = vc_prob.loc[0,veh_id]-len(used_veh)
                                        # used_veh = form_solve(data, tour_df, carr_id, carrier_df, payload_df,
                                        #                         prob_type, count_num, ship_type, c_prob, df_prob, max_time, index, comm,
                                        #                         tour_id, payload_i, depot_i)
                                        w1, w2 = 0.5, 0.5
                                        used_veh = form_solve(data, tour_df, carr_id, carrier_df, payload_df,
                                                    prob_type, count_num, ship_type, c_prob, df_prob, max_time, index, comm, error_list, results_df, w1, w2)
                                        print('used veh: ', used_veh)
                                        # Saving small output files for testing purposes
                                        # tour_df.to_csv('test_data/tour_df_pickup_delivery_internal.csv', index=False)
                                        # carrier_df.to_csv('test_data/carrier_df_pickup_delivery_internal.csv', index=False)
                                        # payload_df.to_csv('test_data/payload_df_pickup_delivery_internal.csv', index=False)

                                        # Reduce number of vehicles depending on those useds
                                        if len(used_veh) > 0:
                                            veh_id = veh.split("_")[0]+"_"+veh.split("_")[1]
                                            vc_prob.loc[0,veh_id] = vc_prob.loc[0,veh_id]-len(used_veh)



                                        # run_time = time() - b_time
                                        # # print('Time for the run: ', run_time)
                                        # # print('\n')



                                        # if not os.path.exists(config.fdir_main_output_tour + str(args.target_year)+"/"):
                                        #     os.makedirs(config.fdir_main_output_tour + str(args.target_year)+"/")
                                        # dir_out=config.fdir_main_output_tour + str(args.target_year)+"/"
                                        # #  Saving the carrier ids with errors
                                        # if len(error_list) > 0:
                                        #     with open(dir_out+"%s_county%s_error_%s.csv"%(ship_type, str(count_num), str(file_index) ), "w", newline="") as f:
                                        #         writer = csv.writer(f)
                                        #         writer.writerows(error_list)

                                        # # ' {0} Load({1}) -> '.format(node_list[l], temp_load)
                                        # if file_index == 9999:
                                        #     tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
                                        #     carrier_df.to_csv(dir_out+"{0}_county{1}_carrier_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
                                        #     payload_df.to_csv(dir_out+"{0}_county{1}_payload_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
                                        # else:
                                        #     tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year, sim_seq), index=False)
                                        #     carrier_df.to_csv(dir_out+"{0}_county{1}_carrier{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num,str(file_index),args.scenario,args.target_year, sim_seq), index=False)
                                        #     payload_df.to_csv(dir_out+"{0}_county{1}_payload{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year, sim_seq), index=False)
                                        # print ('Completed saving tour-plan files for {0} and county {1} and simulation{2}'.format(ship_type, count_num, sim_seq), '\n')                
                except Exception as e:
                    print('Could not solve problem for carrier: ', carr_id, ' : ', e)
                    error_list.append([carr_id, veh, comm, index, e])
                    # print('\n')

            run_time = time() - b_time
            # print('Time for the run: ', run_time)
            # print('\n')



            if not os.path.exists(config.fdir_main_output_tour + str(args.target_year)+"/"):
                os.makedirs(config.fdir_main_output_tour + str(args.target_year)+"/")
            dir_out=config.fdir_main_output_tour + str(args.target_year)+"/"
            #  Saving the carrier ids with errors
            if len(error_list) > 0:
                with open(dir_out+"%s_county%s_error_%s.csv"%(ship_type, str(count_num), str(file_index) ), "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(error_list)

            # ' {0} Load({1}) -> '.format(node_list[l], temp_load)
            if file_index == 9999:
                tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
                carrier_df.to_csv(dir_out+"{0}_county{1}_carrier_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
                payload_df.to_csv(dir_out+"{0}_county{1}_payload_s{2}_y{3}_sim{4}.csv".format(ship_type, count_num,args.scenario,args.target_year, sim_seq), index=False)
            else:
                tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year, sim_seq), index=False)
                carrier_df.to_csv(dir_out+"{0}_county{1}_carrier{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num,str(file_index),args.scenario,args.target_year, sim_seq), index=False)
                payload_df.to_csv(dir_out+"{0}_county{1}_payload{2}_s{3}_y{4}_sim{5}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year, sim_seq), index=False)
            print ('Completed saving tour-plan files for {0} and county {1} and simulation{2}'.format(ship_type, count_num, sim_seq), '\n')  
        results_df.to_csv(dir_out+"{0}_county{1}_resultsim{2}_s{3}_y{4}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year), index=False)
        vehicle_routing_result_summary(dir_out, ship_type, count_num, file_index, year, scenario, num_montecarlo)
        # run_time = time() - b_time
        # # print('Time for the run: ', run_time)
        # # print('\n')

        # if not os.path.exists(config.fdir_main_output_tour + str(args.target_year)+"/"):
        #     os.makedirs(config.fdir_main_output_tour + str(args.target_year)+"/")
        # dir_out=config.fdir_main_output_tour + str(args.target_year)+"/"     
        # #  Saving the carrier ids with errors
        # if len(error_list) > 0:
        #     with open(dir_out+"%s_county%s_error_%s.csv"%(ship_type, str(count_num), str(file_index) ), "w", newline="") as f:
        #         writer = csv.writer(f)
        #         writer.writerows(error_list)

        # # ' {0} Load({1}) -> '.format(node_list[l], temp_load)
        # if file_index == 9999:
        #     tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours_s{2}_y{3}.csv".format(ship_type, count_num,args.scenario,args.target_year), index=False)
        #     carrier_df.to_csv(dir_out+"{0}_county{1}_carrier_s{2}_y{3}.csv".format(ship_type, count_num,args.scenario,args.target_year), index=False)
        #     payload_df.to_csv(dir_out+"{0}_county{1}_payload_s{2}_y{3}.csv".format(ship_type, count_num,args.scenario,args.target_year), index=False)
        # else:    
        #     tour_df.to_csv(dir_out+"{0}_county{1}_freight_tours{2}_s{3}_y{4}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year), index=False)
        #     carrier_df.to_csv(dir_out+"{0}_county{1}_carrier{2}_s{3}_y{4}.csv".format(ship_type, count_num,str(file_index),args.scenario,args.target_year), index=False)
        #     payload_df.to_csv(dir_out+"{0}_county{1}_payload{2}_s{3}_y{4}.csv".format(ship_type, count_num, str(file_index),args.scenario,args.target_year), index=False)
        # print ('Completed saving tour-plan files for {0} and county {1}'.format(ship_type, count_num), '\n')
    
    except Exception as e:
        print('Could not run module, exception: ', e)   


if __name__ == "__main__":
    main()

