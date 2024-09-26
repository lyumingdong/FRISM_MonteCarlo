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
