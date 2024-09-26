# Vehicle Routing Problem (VRP) Solver with Combined Energy and Time Objectives

## Introduction

This document provides a detailed explanation of a Python script designed to generate vehicle tour plans while considering timing, load, and energy constraints. The script solves a Vehicle Routing Problem (VRP) by combining energy consumption and travel time into a single objective function. It uses Google's OR-Tools library to optimize routes for a fleet of vehicles, ensuring efficient delivery or pickup operations.

A key feature of this script is the incorporation of **Monte Carlo simulation** to find the most robust route under uncertainty. By running multiple simulations with variable inputs, the script selects routes that perform best across different scenarios, enhancing reliability and efficiency.

**Note**: The VRP solver is integrated into a larger simulation framework and is executed via a wrapper script called `Run_frism.py`. This script orchestrates various modules, including the VRP solver, to simulate freight transportation scenarios.

## Dependencies

The script relies on several Python libraries and packages:

- **Pandas**: For data manipulation.
- **GeoPandas**: For geospatial data handling.
- **NumPy**: For numerical operations.
- **OR-Tools**: Google's optimization tools for solving VRP.
- **Shapely**: For geometric operations.
- **Random**: For generating random numbers.
- **Time**: For tracking execution time.
- **Argparse**: For parsing command-line arguments.
- **OS** and **Sys**: For system operations and command-line argument handling.
## Overview of Functions

The VRP solver script (`VRP_OR-tools_Stops_veh_tech.py`) contains several key functions:

### 1. `tt_cal(...)`

Calculates travel time between an origin and destination using either geospatial IDs or mesozone distances.

```python
def tt_cal(org_meso, dest_meso, org_geoID, dest_geoID, sel_tt, sel_dist):
    # Function body
```

**Description:**

- **Purpose**: Retrieves the travel time between an origin and destination.
- **Logic**:
  - Attempts to find travel time using geospatial IDs (`org_geoID`, `dest_geoID`).
  - If not available, calculates travel time based on mesozone distances (`org_meso`, `dest_meso`).
  - Assumes an average speed of 40 mph for distance-based calculation.
- **Returns**: Travel time in minutes.

### 2. `ec_cal(...)`

Calculates energy cost between an origin and destination based on vehicle type and mesozone distances.

```python
def ec_cal(org_meso, dest_meso, org_geoID, dest_geoID, sel_ec, sel_dist, ec_vehicletype_df, veh_type):
    # Function body
```
**Description:**

- **Purpose**: Retrieves the energy cost between an origin and destination.
- **Logic**:
  - Attempts to find energy cost using geospatial IDs and vehicle type.
  - If not available, calculates energy cost based on mesozone distances and vehicle's primary fuel rate.
  - Energy costs are normalized (e.g., divided by `1.3E8`).
- **Returns**: Energy cost in appropriate units.

### 3. `get_geoId(...)`

Retrieves the geospatial ID corresponding to a given mesozone.

```python
def get_geoId(zone, CBGzone_df):
    # Function body
```
**Description:**

- **Purpose**: Maps a mesozone ID to its corresponding geospatial ID.
- **Returns**: The geospatial ID (`org_geoID`) or `-1` if not found.

### 4. `create_data_model(...)`

Creates the data model required for the VRP, including time matrices, energy matrices, demands, time windows, and vehicle capacities.

```python
def create_data_model(df_prob, depot_loc, prob_type, v_df, f_prob, c_prob, carrier_id,
                      CBGzone_df, tt_df, ec_df, ec_vehicletype_df, dist_df, veh, commodity, ship_index, path_stops):
    # Function body
```
**Description:**

- **Purpose**: Prepares all the necessary data structures for the VRP.
- **Key Components**:
  - **Time Matrix (`time_matrix`)**: Travel times between nodes.
  - **Energy Matrix (`energy_matrix`)**: Energy costs between nodes.
  - **Demands (`demands`)**: Load demands at each node.
  - **Time Windows (`time_windows`)**: Allowed arrival times at nodes.
  - **Vehicle Capacities (`vehicle_capacities`)**: Capacities of each vehicle.
  - **Pickups and Deliveries (`pickups_deliveries`)**: Pairings of pickup and delivery nodes for shipments.
- **Logic**:
  - Initializes data structures.
  - Iterates over payloads to populate nodes and constraints.
  - Calculates time and energy matrices using `tt_cal` and `ec_cal`.
  - Accounts for vehicle types and capacities.
- **Returns**: A dictionary `data` containing all VRP parameters.

### 5. `ec_cal(...)`

Processes input files to generate dataframes necessary for VRP formulation.

```python
def input_files_processing(travel_file, energy_file, energy_vehicle_file, dist_file, CBGzone_file, carrier_file, payload_file, vehicleType_file):
    # Function body
```
**Description:**

- **Purpose**: Reads and processes input files, returning dataframes for use in VRP setup.
- **Inputs**: Paths to various CSV and GeoJSON files.
- **Processes**:
  - Reads travel time, energy cost, distance, and zone mapping files.
  - Reads carrier, payload, and vehicle type information.
  - Cleans and preprocesses data.
- **Returns**: Multiple dataframes (`tt_df`, `ec_df`, `dist_df`, etc.) for use in the VRP.

### 6. `form_solve(...)`

Formulates and solves the VRP by combining energy and time into a single objective function.

```python
def form_solve(data, tour_df, carr_id, carrier_df, payload_df, prob_type, count_num, ship_type, c_prob, 
               df_prob, max_time, index, comm, error_list, results_df, w1, w2):
    # Function body
```
******Description:**

- **Purpose**: Sets up and solves the VRP using OR-Tools.
- **Key Steps**:
  - **Index Manager**: Maps nodes to indices.
  - **Routing Model**: Defines the VRP model.
  - **Cost Functions**:
    - **Combined Cost Callback**: Combines time and energy costs using weights `w1` and `w2`.
  - **Constraints**:
    - Time windows.
    - Vehicle capacities.
    - Pickup and delivery relationships.
  - **Solver Parameters**:
    - Time limits.
    - Solution strategies.
- **Monte Carlo Simulation Integration**:
  - Adjusts travel times randomly within a certain range to simulate variability.
  - Runs multiple simulations to assess different scenarios.
- **Returns**: A list of used vehicles (`used_veh`) and updates the `results_df` with simulation results.


### 7. `print_solution(...)`

Formulates and solves the VRP by combining energy and time into a single objective function.

```python
def form_solve(data, tour_df, carr_id, carrier_df, payload_df, prob_type, count_num, ship_type, c_prob, 
               df_prob, max_time, index, comm, error_list, results_df, w1, w2):
    # Function body
```
**Description:**

- **Purpose**: Parses the solution from the solver and updates dataframes.
- **Actions**:
  - Iterates over vehicles and routes.
  - Records tour information (start times, nodes visited).
  - Updates payload data with sequence ranks and times.
  - Calculates cumulative loads.
- **Updates**:
  - `tour_df`: Tour details.
  - `carrier_df`: Carrier and vehicle associations.
  - `payload_df`: Shipment details per tour.
  - `results_df`: Simulation results for analysis.

### 8. `vehicle_routing_result_summary(...)`

Analyzes and summarizes the VRP results, selecting the best routes based on stochastic simulations.

```python
def vehicle_routing_result_summary(dir_out, ship_type, count_num, file_index, target_year, scenario, num_montecarlo):
    # Function body
```
**Description:**

- **Purpose**: Post-processes simulation results to select the optimal routes.
- **Monte Carlo Simulation Emphasis**:
  - Aggregates results from multiple simulations.
  - Calculates variability (e.g., standard deviation) in total distances.
  - Identifies the most robust routes that perform best across simulations.
- **Process**:
  - Reads simulation result files.
  - Calculates total distances for routes.
  - Checks time window constraints.
  - Selects routes with minimum distance and valid time windows.
  - Merges results into final output files.
- **Outputs**: Finalized dataframes for carrier, tour, and payload information.

### 9. `main(args=None)`

The main function that orchestrates the VRP solving process by parsing arguments, processing data, and invoking the solver.

```python
def main(args=None):
    # Function body
```
**Description:**

- **Purpose**: Entry point of the script.
- **Actions**:
  - Parses command-line arguments.
  - Processes input files.
  - Iterates over carriers, commodities, and vehicle types.
  - Sets up and solves the VRP for each case.
  - Runs multiple simulations for stochastic analysis.
  - Saves results and outputs.
- **Monte Carlo Simulation Integration**:
  - Runs a loop over a defined number of Monte Carlo iterations.
  - Adjusts travel times randomly to simulate real-world variability.
  - Collects results from each simulation for analysis.


---

### Data Processing

The script begins by processing various input files that contain essential data:

- **Travel Time Data**: Origin-destination travel times.
- **Energy Cost Data**: Energy consumption between locations.
- **Distance Data**: Distances between mesozones.
- **Carrier Data**: Information about carriers and their depots.
- **Payload Data**: Details of the shipments or deliveries.
- **Vehicle Type Data**: Vehicle capacities, types, and other attributes.

The `input_files_processing` function reads these files and prepares dataframes for further processing.

## VRP Model Formulation

The VRP is formulated using OR-Tools' `RoutingModel`. The key components of the model are:

- **Nodes**: Representing the depot and delivery/pickup locations.
- **Time Matrix**: Travel times between nodes.
- **Energy Matrix**: Energy costs between nodes.
- **Demands**: Load requirements at each node.
- **Time Windows**: Allowed time frames for arrivals at each node.
- **Vehicle Capacities**: Load capacities for each vehicle.
- **Vehicles**: The fleet of vehicles available for routing.

## Combining Energy and Time in the Objective Function

### Objective Function Formulation

The script combines energy consumption and travel time into a single objective function to optimize both factors simultaneously. This is achieved by defining a **combined cost callback** function:

```python
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
```

In this function:

- **`time_cost`**: The travel time between nodes, including any stop durations.
- **`energy_cost`**: The energy consumed between nodes.
- **`w1` and `w2`**: Weights assigned to time and energy costs, respectively.

### Weight Parameters

The weights `w1` and `w2` allow for adjusting the importance of time versus energy in the optimization:

- **If `w1` > `w2`**: Time is prioritized over energy.
- **If `w2` > `w1`**: Energy consumption is prioritized over travel time.

These weights are passed as parameters when invoking the `form_solve` function:

```python
used_veh = form_solve(
    data, tour_df, carr_id, carrier_df, payload_df,
    prob_type, count_num, ship_type, c_prob, df_prob,
    max_time, index, comm, error_list, results_df, w1, w2
)
```

### Setting the Objective in OR-Tools

After defining the combined cost callback, it is registered with the routing model:
```python
transit_callback_index = routing.RegisterTransitCallback(combined_cost_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
```
This tells the solver to use the combined cost as the objective function when evaluating the cost of moving from one node to another.

---

## Incorporating Monte Carlo Simulation for Robust Route Selection

### Purpose of Monte Carlo Simulation

Real-world conditions such as travel times and energy consumption are subject to variability due to factors like traffic congestion, weather, and vehicle performance. To account for this uncertainty, the script uses **Monte Carlo simulation** to:

- **Assess Route Robustness**: Evaluate how routes perform under different random variations.
- **Identify Optimal Routes**: Select routes that consistently perform well across simulations.
- **Enhance Reliability**: Ensure the chosen routes are less sensitive to variability.

### Implementation Details

#### Adjusting Travel Times Randomly

Within each Monte Carlo iteration, the script introduces randomness to the travel times:

```python
# Store the original time matrix
data['time_matrix_origin'] = data['time_matrix'].copy()

# Adjust travel times by a random factor between 0.8 and 1.2
datatemp = [
    [int(x * random.uniform(0.8, 1.2)) for x in row]
    for row in data['time_matrix_origin']
]
data['time_matrix'] = datatemp
```
This simulates variability in travel times, such as delays or faster-than-expected travel.

#### Running Multiple Simulations

The script runs multiple iterations (e.g., num_montecarlo = 2) to generate different scenarios:

```python
num_montecarlo = 2
for sim_seq in range(num_montecarlo):
    # Adjust travel times and solve the VRP
    ...
```

Each iteration represents a different possible state of the world, providing a broader assessment of route performance.

#### Collecting and Analyzing Results

After running all simulations, the script aggregates the results:

- **Stores Routes and Costs**: Keeps track of routes, distances, and whether time windows were met.
- **Calculates Variability**: Computes statistics like standard deviation of total distances.
- **Selects Best Routes**: Identifies routes that have the lowest total distance and meet all constraints across simulations.

### Selecting the Most Robust Route

After generating the simulation results, a separate **post-processing script** is used to analyze the outcomes and select the most robust route.

#### Post-Processing Code Overview

The post-processing code performs the following steps:

1. **Read Simulation Results**: Loads the simulation results from CSV files.
2. **Parse Route Data**: Converts string representations of routes and matrices back into usable data structures.
3. **Calculate Total Distance**: Computes the total distance for each route using the distance matrix and stop durations.
4. **Check Time Windows**: Verifies that each route satisfies the time window constraints.
5. **Aggregate Results**: Collects distances and checks across simulations.
6. **Select Best Route**: Identifies the route with the least variability in total distance (lowest standard deviation) and valid time windows.
7. **Merge Final Results**: Combines data for the best routes into final output files.

#### Example Post-Processing Code

[Please refer to the post-processing code provided in the previous section.]

#### Benefits of This Approach

- **Risk Mitigation**: By considering variability, the selected route is less likely to be adversely affected by unforeseen events.
- **Performance Assurance**: Ensures that the chosen route performs consistently well, rather than being optimal only under ideal conditions.
- **Data-Driven Decision Making**: Provides quantitative metrics to support route selection.

### Saving Final Results

After identifying the most robust routes, the script saves the final results:
```python
# Merge final results with original data
result_df_carrier = pd.merge(df_carrier, final_results, on=['tour_id', 'sim_seq'], how='inner')
result_df_tour = pd.merge(df_tour, final_results, on=['tour_id', 'sim_seq'], how='inner')
result_df_load = pd.merge(df_load, final_results, on=['tour_id', 'sim_seq'], how='inner')

# Save the final dataframes to CSV files
result_df_carrier.to_csv(carrier_name + '.csv', index=False)
result_df_tour.to_csv(tour_name + '.csv', index=False)
result_df_load.to_csv(load_name + '.csv', index=False)
```
## Running the VRP Solver via `Run_frism.py`

### Overview of `Run_frism.py`

The `Run_frism.py` script is a wrapper that orchestrates various modules, including the VRP solver. It accepts command-line arguments and calls the VRP solver with appropriate parameters.

### Command-Line Usage

To run the entire simulation, including the VRP solver, use the following command:

```bash
python Run_frism.py [county number] [year] [scenario name] [sampling rate] [Y or N] [region]
```
#### Example:
```bash
python Run_frism.py 21 2018 base 10 Y AT
```

In this example, the parameters are:

- **County Number**: `21`
- **Year**: `2018`
- **Scenario Name**: `base`
- **Sampling Rate**: `10`
- **Data Generation Flag (Y or N)**: `Y`
- **Region**: `AT` (e.g., Austin)

### Parameters Explained

- **`[county number]`**: An integer representing the county number in the scenario.
- **`[year]`**: The target analysis year (e.g., `2018`).
- **`[scenario name]`**: The name of the scenario (e.g., `base`, `future_scenario`).
- **`[sampling rate]`**: The sample rate for data generation (e.g., `10`).
- **`[Y or N]`**: A flag indicating whether to generate data (`Y`) or not (`N`).
- **`[region]`**: The region identifier (e.g., `AT` for Austin).

### How `Run_frism.py` Calls the VRP Solver

Within `Run_frism.py`, the VRP solver is called using `os.system()` with the appropriate parameters:

```python
os.system("python VRP_OR-tools_Stops_veh_tech.py \
    -cy {county} \
    -t ../../../FRISM_input_output_{region}/Sim_inputs/Geo_data/tt_df_cbg.csv.gz \
    -d ../../../FRISM_input_output_{region}/Sim_inputs/Geo_data/Austin_od_dist.csv \
    -ct ../../../FRISM_input_output_{region}/Sim_inputs/Geo_data/Austin_freight_centroids.geojson \
    -cr ../../../FRISM_input_output_{region}/Sim_outputs/Shipment2Fleet/{year}/B2C_carrier_county{county}_shipall_s{scenario}_y{year}_sr{sample_rate}.csv \
    -pl ../../../FRISM_input_output_{region}/Sim_outputs/Shipment2Fleet/{year}/B2C_payload_county{county}_shipall_s{scenario}_y{year}_sr{sample_rate}.csv \
    -vt ../../../FRISM_input_output_{region}/Sim_outputs/Shipment2Fleet/{year}/vehicle_types_s{scenario}_y{year}.csv \
    -sn {scenario} \
    -yt {year} \
    -ps ../../../FRISM_input_output_{region}/Sim_outputs/Tour_constraint/")
```
**Note**: The actual paths are constructed using the parameters provided to `Run_frism.py`.


### Running the Simulation via `Run_frism.py`

To run the simulation, including the VRP solver, use the following command:

```bash
python Run_frism.py [county number] [year] [scenario name] [sampling rate] [Y or N] [region]
```
#### Example:
```python
python Run_frism.py 21 2018 base 10 Y AT
```
