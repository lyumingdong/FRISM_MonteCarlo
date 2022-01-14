# FRISM: FReight Integrated Simulation Model
### Contributors
Kyungsoo Jeong: <Kyungsoo.Jeong@nrel.gov>
<br>
Juliette Ugirumurera: <jugirumu@nrel.gov>
<br>

## Description
FRISM simulates day-to-day freight activities including end-consumer shopping, distribution channel, and carrier operation with e-commerce dynamics between passenger and freight travel.

## Setup python environment
```linux
conda env create -f environment.yml
```
Activate conda environment to run the code:
```linux
conda activate frism
```

## Generating Freight Tours
To generate freight tours, solve the vehicle routing problem as bellow:
<br>
```
cd src/Simulation/
python VRP_OR-tools.py -t <travel time gz file> -d <distance csv file> -ct <freight centroid csv file> -cr <carrier csv file> -pl <payload csv file> -vt <vehicle type csv file>
```

This will output three files in the src/Sim_outputs/Tour_plan folder:
<br>
**_payload.csv**: csv file with payload information, when and where they were delivered.
<br>
**_carrier.csv**: csv file with tour information for each carrier and its vehicles.
<br>
**_freight_tours.csv**: csv file with freight tour information including departure location, departure time and maximum duration.

If there are carriers for which tours could be generated for some reason, they can be found in **error.csv** under src/Sim_ou
 folder.
