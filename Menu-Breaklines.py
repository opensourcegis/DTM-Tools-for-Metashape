""" Tool to generate DTM from Drone Imagery in Agisoft Metashape
    CSF FILTER
    Build for:
    Version: 2.0
    Python Version: 3.9
    Addl. Dependencies req: numpy, laspy, CSF
"""
# Dependencies
import numpy as np
import sys
import laspy
from laspy.file import File
import Metashape
from tkinter import *
import os
from pathlib import Path
import fiona
from shapely.geometry import LineString, Point, mapping, shape
import textwrap
from PySide2 import QtGui, QtCore, QtWidgets
import Metashape



# Main function to call from Menu

def breakline_processing():
    # Reading project from Metashape
    global doc, chunk, project_folder, project_path

    doc = Metashape.app.document
    chunk = doc.chunk
    project_path = doc.path
    project_folder = os.path.dirname(project_path)

    # Main window for GUI
    class MyWindow(QtWidgets.QDialog):
        def __init__(self,parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Add Points to Breaklines")
            self.setGeometry(500, 250, 500, 300)
            self.setFixedSize(500, 300)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter No. of Points per .m along Breaklines:")
            self.t1 = QtWidgets.QLineEdit(self)
            self.t2 = QtWidgets.QLineEdit(self)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setValue(0)
            self.progress_bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.typeTxt = QtWidgets.QLabel()
            self.typeTxt.setText("Enter the name of")
            self.typeCmb = QtWidgets.QComboBox()
            ASSET_TYPES = ["Label:", "Description:", "Layer:"]
            for type in ASSET_TYPES:
                self.typeCmb.addItem(type)

            layout = QtWidgets.QGridLayout()
            layout.setContentsMargins(20, 0, 20, 0)
            layout.addWidget(self.typeTxt, 1, 0)
            layout.addWidget(self.typeCmb, 1, 1)
            layout.addWidget(self.chunkTxt, 0, 0, 1, 2)
            layout.addWidget(self.t1, 0, 2)
            layout.addWidget(self.t2, 1, 2)

            layout.addWidget(self.btnP1, 3, 1)

            layout.addWidget(self.progress_bar, 2, 1)
            # self.progress_bar.setGeometry(200, 240, 250, 40)

            self.setLayout(layout)

            self.exec()

            #QtCore.QObject.connect(self.btnP1, QtCore.SIGNAL("clicked()"), self.execute)

        def execute(self):

            try:
                if not (19 < int(self.t1.text()) < 201):
                    raise ValueError
            except ValueError:
                message = "Enter Integer Value between 20 and 200"
                Metashape.app.messageBox(textwrap.fill(message, 65))
    
                return None
              
            self.progress_bar.setValue(10)

            input_label = self.t2.text()
            combo_text = self.typeCmb.currentText()

            if combo_text=="Label:":
                split_label="NAME"
            elif combo_text=="Description:":
                split_label="DESCRIPTIO"
            elif combo_text=="Layer:":
                split_label="LAYER"

            # Export Shapefiles from Metashape
            chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=True,
                               polygons_as_polylines=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
            shapefile_initial = Path(project_folder, 'shapes.shp')

            self.progress_bar.setValue(20)            
            # Extract breaklines, rivercenter, riveredge and lakes from shapefile
            if input_label:
                break_shapefile_processing(shapefile_initial,split_label,input_label)
            else:
               
                break_shapefile_processing(shapefile_initial,split_label)
            
            shapefile_filename = Path(project_folder, 'breaklines.shp')
            breakline_lasfile = Path(project_folder, 'breaklines.las')

            self.progress_bar.setValue(40)

            # Pass Extracted shapes to points function
            if os.path.exists(shapefile_filename):
                
                try:
                    break_shapefile_to_las_interpolated(
                        shapefile_filename, breakline_lasfile, int(self.t1.text()))
                except:
                    message = "Error. Check your Inputs"
                    Metashape.app.messageBox(textwrap.fill(message, 65))
                    break_remove_assets()
                    self.close()

                
                self.progress_bar.setValue(70)
                chunk.importPointCloud(
                    project_folder + '/breaklines.las', crs=chunk.crs, replace_asset=False)

                # Import Completed
                self.progress_bar.setValue(90)
                break_remove_assets()
                message = "Breakline Points imported to project."
                Metashape.app.messageBox(textwrap.fill(message, 65))
                self.close()
                
            else:
                # print Error ("There are no breaklines")
                break_remove_assets()
                message = "There are No Breaklines or check fields entered. Add breaklines to use this tool."
                Metashape.app.messageBox(textwrap.fill(message, 65))
                self.close()
                


    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)

# Main fucntion to convert shape to points


def break_shapefile_to_las_interpolated(shape_filepath, output_file_path, density_per_line=None):

    poly_file = []
    with fiona.open(shape_filepath, 'r') as source:
        # Open the output .poly file for writing
        for feature in source:
            geometry = feature['geometry']
            coordinates = geometry['coordinates']
            poly_file_line = LineString(coordinates)
            for coord in poly_file_line.coords:
                poly_file.append(
                    f"{coord[0]} {coord[1]} {coord[2] if len(coord) > 2 else 0}\n")
            poly_file.append("\n")

    polylines = []
    point_clouds = []

    for i in range(len(poly_file) - 1):
        parts_current = poly_file[i].strip().split()
        parts_next = poly_file[i + 1].strip().split()

        if len(parts_current) >= 3 and len(parts_next) >= 3:
            x1, y1, z1 = map(float, parts_current[:3])
            x2, y2, z2 = map(float, parts_next[:3])
            polylines.append([(x1, y1, z1), (x2, y2, z2)])

    if density_per_line is None:
        for polyline in polylines:   # Generate point clouds along each polyline without interpolation - to be removed
            points = np.array(polyline)
            point_clouds.append(points)
            all_points = np.vstack(point_clouds)
            header = laspy.LasHeader(point_format=3, version="1.2")
            header.scales = np.array([0.001, 0.001, 0.001])
            header.offsets = np.min(all_points, axis=0)

            # define LAS File
            las_write = laspy.LasData(header=header)
            las_write.x = all_points[:, 0]
            las_write.y = all_points[:, 1]
            las_write.z = all_points[:, 2]

            # Set ground classification for all points
            # 2 represents ground classification
            las_write.raw_classification = np.full(len(all_points), 2)
            las_write.write(output_file_path)
        return None
    else:
        points_density_per_line = density_per_line

        for polyline in polylines:   # Generate point clouds along each polyline with interpolation - to be optimised
            points = np.array(polyline)
            dist = np.linalg.norm(points[0] - points[-1])
            interpolated_points = np.linspace(
                points[0], points[-1], round(points_density_per_line*dist))
            point_clouds.append(interpolated_points)

        # Combine all point clouds into a single array
        all_points = np.vstack(point_clouds)
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.scales = np.array([0.001, 0.001, 0.001])
        header.offsets = np.min(all_points, axis=0)

        # define LAS File
        las_write = laspy.LasData(header=header)
        las_write.x = all_points[:, 0]
        las_write.y = all_points[:, 1]
        las_write.z = all_points[:, 2]

        # Set ground classification for all points
        # 2 represents ground classification
        las_write.raw_classification = np.full(len(all_points), 2)
        las_write.write(output_file_path)
        return None


def break_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'breaklines.shp')
    breakline_lasfile = Path(project_folder, 'breaklines.las')
    others_filename= Path(project_folder, 'others.shp')
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'breaklines.shx'))
            os.remove(Path(project_folder, 'breaklines.dbf'))
            os.remove(Path(project_folder, 'breaklines.cpg'))
        except:
            pass
    if os.path.exists(initial_filename):
        try:
            os.remove(initial_filename)
            os.remove(Path(project_folder, 'shapes.prj'))
            os.remove(Path(project_folder, 'shapes.dbf'))
            os.remove(Path(project_folder, 'shapes.shx'))
        except:
            pass
    
    if os.path.exists(others_filename):
        try:
            os.remove(others_filename)
            os.remove(Path(project_folder, 'others.shx'))
            os.remove(Path(project_folder, 'others.dbf'))
            os.remove(Path(project_folder, 'others.cpg'))
        except:
            pass
    
    if os.path.exists(breakline_lasfile):
        try:
            os.remove(breakline_lasfile)
        except:
            pass

    


def break_shapefile_processing(shapefile_path, split_label,input_label=""):
    input_shapefile = shapefile_path
    # Create a directory to store the output shapefiles
    output_directory = project_folder
    os.makedirs(output_directory, exist_ok=True)

    split_attribute = split_label  # Default is DESCRIPTIO as per Metashape

    # Initialize a dictionary to store output shapefiles
    output_shapefiles = {}

    # Iterate through features and split into output shapefiles
    with fiona.open(input_shapefile) as src:
        schema = src.schema.copy()
        
        for feature in src:
            label = feature['properties'][split_attribute]

            if label not in output_shapefiles:
                # if label not in output_shapefiles:
                if label == None or label == input_label:
                    output_shapefile_path = os.path.join(
                    output_directory, f"breaklines.shp")

                    output_shapefile = fiona.open(
                        output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                    output_shapefiles[label] = output_shapefile
                else:
                    output_shapefile_path = os.path.join(
                            output_directory, f"others.shp")

                    output_shapefile = fiona.open(
                        output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                    output_shapefiles[label] = output_shapefile
            else:
                
                output_shapefile=output_shapefiles[label]
            
            output_shapefile.write(feature)
    
    for label, output in output_shapefiles.items():
        output.close()




label = "DTM Tools/Breaklines to points"
Metashape.app.addMenuItem(label, breakline_processing)
print("To execute this script press {}".format(label))
