""" Tool to generate DTM from Drone Imagery in Agisoft Metashape
    CSF FILTER
    Build for:
    Version: 2.0
    Python Version: 3.9
    Addl. Dependencies req: numpy, laspy, CSF
"""
# Dependencies
import numpy as np
import laspy
from laspy.file import File
import Metashape
from tkinter import *
import os
from pathlib import Path
import fiona
import textwrap
from shapely.geometry import LineString, Point, shape
from PySide2 import QtGui, QtCore, QtWidgets

import random

# Reading project from Metashape


def lake_sample_point_processing():
    global doc, chunk, project_folder, project_path
    doc = Metashape.app.document
    chunk = doc.chunk
    project_path = doc.path
    project_folder = os.path.dirname(project_path)

    # Main window for GUI using Tkinter
    class MyWindow(QtWidgets.QDialog):
        def __init__(self, parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Sample Points inside Lake Boundary")
            self.setGeometry(500, 250, 500, 400)
            self.setFixedSize(500, 300)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter No. of Points per sq.m inside Lake (1-5):")
            self.t1 = QtWidgets.QLineEdit(self)
            self.t2 = QtWidgets.QLineEdit(self)
            self.t3 = QtWidgets.QLineEdit(self)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setValue(0)
            self.progress_bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.typeTxt = QtWidgets.QLabel()
            self.typeTxt.setText("Enter the name of")
            self.fieldTxt = QtWidgets.QLabel()
            self.fieldTxt.setText("Enter the name of the height attribute:")
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
            layout.addWidget(self.fieldTxt, 2, 0, 1, 2)
            layout.addWidget(self.t3, 2, 2)

            layout.addWidget(self.btnP1, 4, 1)

            layout.addWidget(self.progress_bar, 3, 1)
            # self.progress_bar.setGeometry(200, 240, 250, 40)

            self.setLayout(layout)

            self.exec()

        def execute(self):

            try:
                if not (0 < float(self.t1.text()) < 6) or not self.t2.text() or not self.t3.text():
                    raise ValueError
            except ValueError:
                message = "Enter Integer Value between 1 and 5 and fill all fields"
                Metashape.app.messageBox(textwrap.fill(message, 65))
                
                return None

            # Export Shapefiles from Metashape
            chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=False,
                               save_polygons=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
            shapefile_initial = Path(project_folder, 'shapes.shp')
            self.progress_bar.setValue(20)

            label_name = self.t2.text()
            combo_text = self.typeCmb.currentText()

            if combo_text=="Label:":
                split_label="NAME"
            elif combo_text=="Description:":
                split_label="DESCRIPTIO"
            elif combo_text=="Layer:":
                split_label="LAYER"


           
            lake_sample_shapefile_processing(shapefile_initial, label_name,split_label)
            self.progress_bar.setValue(40)

            shapefile_filename = Path(
                project_folder, 'lake_samples.shp')
            breakline_lasfile = Path(
                project_folder, 'lake_samples.las')

            height_name = self.t3.text()
            # Convert Shape file to Poly file using Fiona

            if os.path.exists(shapefile_filename):

                exucuted_function = lake_sample_point(
                    shapefile_filename, breakline_lasfile, float(self.t1.text()), height_name)
                self.progress_bar.setValue(90)

                if not exucuted_function == None:
                    self.close()
                    Metashape.app.messageBox(
                        textwrap.fill(exucuted_function, 65))
                    
                    samplelake_remove_assets()
                    return None

                chunk.importPointCloud(
                    project_folder + '/lake_samples.las', crs=chunk.crs, replace_asset=False)

                message = "Sampled Points imported to the Project"
                self.close()
                Metashape.app.messageBox(textwrap.fill(message, 65))
                samplelake_remove_assets()
                
                return None

            else:

                message = "There are no shapes for given field"
                self.close()
                Metashape.app.messageBox(textwrap.fill(message, 65))
               
                samplelake_remove_assets()
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)


def lake_sample_point(input_shape, output_las, density, height):

    random_points = []
    # Open the shapefile and extract 3D points

    with fiona.open(input_shape) as src:

        for feature in src:
            polygon = shape(feature['geometry'])
            polygon_area = polygon.area
            num_sample_points = int(polygon_area*density)
            schema = src.schema['properties']

            if height in schema:
                if feature['properties'][height] is None:
                    return "Enter heights in all the height fields"
                else:

                    float_height = feature['properties'][height]
                    lake_height = float(float_height)

                    for _ in range(num_sample_points):
                        while True:
                            x = random.uniform(
                                polygon.bounds[0], polygon.bounds[2])
                            y = random.uniform(
                                polygon.bounds[1], polygon.bounds[3])
                            point = Point(x, y)

                            if polygon.contains(point):
                                random_points.append([x, y, lake_height])
                                break

            else:
                return "The Lake shapefile does not have the field {height}."

        all_points = np.vstack(random_points)
        header = laspy.LasHeader(point_format=3, version="1.2")
        header.scales = np.array([0.01, 0.01, 0.01])
        header.offsets = np.min(all_points, axis=0)

        # define LAS File
        las_write = laspy.LasData(header=header)
        las_write.x = all_points[:, 0]
        las_write.y = all_points[:, 1]
        las_write.z = all_points[:, 2]

        # Set ground classification for all points
        # 2 represents ground classification
        las_write.raw_classification = np.full(len(all_points), 2)
        las_write.write(output_las)
        return None

def samplelake_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'lake_samples.shp')
    lasfilename = Path(project_folder, 'lake_samples.las')
    others_filename = Path(project_folder, 'others.shp')
    
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'lake_samples.shx'))
            os.remove(Path(project_folder, 'lake_samples.dbf'))
            os.remove(Path(project_folder, 'lake_samples.cpg'))
            os.remove(Path(project_folder, 'lake_samples.prj'))
            
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
    if os.path.exists(lasfilename):
        try:
            os.remove(lasfilename)
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

def lake_sample_shapefile_processing(shapefile_path, input_label,split_label):
    input_shapefile = shapefile_path
    # Create a directory to store the output shapefiles
    output_directory = project_folder
    os.makedirs(output_directory, exist_ok=True)
    output_shapefiles = {}
    split_attribute = split_label # Default is DESCRIPTIO as per Metashape

    # Iterate through features and split into output shapefiles
    with fiona.open(input_shapefile) as src:
        schema = src.schema.copy()
      
        for feature in src:
            label = feature['properties'][split_attribute]
            # geometry_type = feature['geometry']['type']
            if label not in output_shapefiles:
                if label == input_label:
                    output_shapefile_path = os.path.join(output_directory, f"lake_samples.shp")

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
                   

        # Close output shapefiles



label = "DTM Tools/Sample points inside Lakes"
Metashape.app.addMenuItem(label, lake_sample_point_processing)
print("To execute this script press {}".format(label))
