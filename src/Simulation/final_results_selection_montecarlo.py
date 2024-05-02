from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas as pd
import os
import sys


county = sys.argv[1]
year = sys.argv[2]
scenario = sys.argv[3]
sample_rate = sys.argv[4]

# county = 21
# year = 2018
# scenario = "base"
# sample_rate = 10

carrier_name = "B2C_county" + str(county) + "_carrier_s" + scenario + "_y" + str(year) 
tour_name = "B2C_county" + str(county) + "_freight_tours_s" + scenario + "_y" + str(year)
load_name = "B2C_county" + str(county) + "_payload_s" + scenario + "_y" + str(year)
result_name = "B2C_county" + str(county) + "_resultsim9999_s" + scenario + "_y" + str(year)

df_resultssim = pd.read_csv(result_name + '.csv')

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



df_carrier = pd.DataFrame()
df_tour = pd.DataFrame()
df_load = pd.DataFrame()

for sim_seq in range(3):
    df_carriertemp = pd.read_csv(carrier_name + "_sim" + str(sim_seq) + '.csv')
    df_tourtemp = pd.read_csv(tour_name + "_sim" + str(sim_seq) + '.csv')
    df_loadtemp = pd.read_csv(load_name + "_sim" + str(sim_seq) + '.csv')
    
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
result_df_carrier.to_csv(carrier_name +'.csv')
print('carrier saved')
result_df_tour.to_csv(tour_name+'.csv')
print('tour saved')
result_df_load.to_csv(load_name+'.csv')
print('load saved')

