# DTM and Breakline Processing Tool in Agisoft Metashape

This tool is a Python-based plugin for Agisoft Metashape (version 2.0) designed to facilitate **Digital Terrain Model (DTM) generation** and **breakline processing** from drone-captured imagery. It leverages Python (3.9) and Metashape's API to automate terrain classification and the generation of point clouds, allowing users to specify custom breaklines, interpolate breakline points, and apply terrain classifications via the **CSF (Cloth Simulation Filtering)** method.

## Features
1. **Breakline Point Generation**
   - Extracts breaklines from shapefiles.
   - Generates points along breaklines with specified densities and exports them as `.las` point clouds.
   - Supports shapefile filtering to classify specific breaklines.

2. **Ground Point Classification with CSF**
   - Uses the Cloth Simulation Filter (CSF) to classify ground and non-ground points.
   - Provides adjustable parameters for cloth resolution, class threshold, and terrain type.
   - Exports classified point clouds for DTM generation.

3. **Automated DTM Workflow**
   - Export shapefiles and point clouds directly from Metashape’s interface.
   - Automates breakline and point cloud import/export for faster project management.

## Dependencies
- Python 3.9
- [Agisoft Metashape](https://www.agisoft.com/) (Version 2.0)
- `numpy` - for numerical computations
- `laspy` - for LAS point cloud processing
- `CSF` - for ground classification
- `fiona` and `shapely` - for shapefile processing and geometry manipulations
- `PySide2` - for GUI elements in Metashape

## Installation
Ensure all dependencies are installed. This tool works directly within Agisoft Metashape; install dependencies using the following commands for the Agisoft Metshape Python Interpreter:

Open CMD in [Metashape Python Installation folder]
```
python.exe -m pip install numpy cloth-simulation-filter laspy fiona shapely PySide2
```

## Usage
### Launching the Plugin
1. Place the .py files in Metashape installation folder/scripts
2. Open Agisoft Metashape.
3. Navigate to the menu option created by this plugin (`DTM Tools > Breaklines to Points`).

### Breakline Processing
1. Specify the number of points per meter along breaklines.
2. Choose the breakline classification type: Label, Description, or Layer.
3. The tool interpolates breakline points and exports them to `.las` format.

### CSF Ground Point Classification
1. Define the cloth resolution and class threshold.
2. Select the terrain type (Flat, Relief, Steep Slope).
3. Execute the filter to classify and export ground points for DTM generation.

### File Cleanup
The tool automatically cleans up intermediate files after processing, leaving only essential outputs.

## Example Output
This tool generates:
- `.las` files for classified ground points.
- Shapefiles for breaklines and additional classifications.

## Acknowledgements
This tool was developed to streamline DTM and breakline processing in drone-based photogrammetry workflows using Agisoft Metashape.
