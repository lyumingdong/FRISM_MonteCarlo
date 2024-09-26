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
