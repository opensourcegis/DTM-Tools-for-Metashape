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
from shapely.geometry import LineString, Point, mapping, shape
from PySide2 import QtGui, QtCore, QtWidgets

# Main function to call from Menu


def lake_processing():
    global doc, chunk, project_folder, project_path

    doc = Metashape.app.document
    chunk = doc.chunk
    project_path = doc.path
    project_folder = os.path.dirname(project_path)
    # point_cloud = chunk.point_cloud

    # Main window for GUI using Tkinter

    class MyWindow(QtWidgets.QDialog):
        def __init__(self, parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Add Points to Lake Boundary")
            self.setGeometry(500, 250, 500, 400)
            self.setFixedSize(500, 300)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter No. of Points per .m along Lake:")
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
            ASSET_TYPES = ["Description:","Label:", "Layer:"]
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
            #QtCore.QObject.connect(self.btnP1, QtCore.SIGNAL("clicked()"), self.execute)

        def execute(self):
            try:
                if not (19 < int(self.t1.text()) < 201):
                    raise ValueError
            except ValueError:
                message = "Enter Integer Value between 20 and 200"
                Metashape.app.messageBox(textwrap.fill(message, 65))
            
                return None

            try:
                if not self.t2.text() or not self.t3.text():
                    raise ValueError
            except ValueError:
                message = "Enter the Field names"
                Metashape.app.messageBox(textwrap.fill(message, 65))
               
                return None

            # Export Shapefiles from Metashape
            chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=True,
                               polygons_as_polylines=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
            shapefile_initial = Path(project_folder, 'shapes.shp')

            combo_text = self.typeCmb.currentText()

            if combo_text=="Label:":
                split_label="NAME"
            elif combo_text=="Description:":
                split_label="DESCRIPTIO"
            elif combo_text=="Layer:":
                split_label="LAYER"

            # Extract breaklines, rivercenter, riveredge and lakes from shapefile
            lake_shapefile_processing(shapefile_initial, self.t2.text(),split_label)
            self.progress_bar.setValue(30)

            shapefile_filename = Path(project_folder, 'lake.shp')
            lake_lasfile = Path(project_folder, 'lake.las')

            # Convert Shape file to Poly file using Fiona
            if os.path.exists(shapefile_filename):

                # Perform the Main Function
                execute_function = lake_shapefile_to_las_interpolated(
                    shapefile_filename, lake_lasfile, int(self.t1.text()), self.t3.text())
                self.progress_bar.setValue(80)

                # Check to error returns
                if not execute_function == None:
                    Metashape.app.messageBox(
                        textwrap.fill(execute_function, 65))
                    self.close()
                    lake_remove_assets()
                    return None
                self.progress_bar.setValue(90)
                chunk.importPointCloud(
                    project_folder + '/lake.las', crs=chunk.crs, replace_asset=False)
                message = "Points imported to the Project"
                
                Metashape.app.messageBox(textwrap.fill(message, 65))
                self.close()
                lake_remove_assets()
                return None

            else:
                message = "There are no shapes for the given field names"
                Metashape.app.messageBox(textwrap.fill(message, 65))
                lake_remove_assets()
                self.close()
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)


def lake_shapefile_to_las_interpolated(shape_filepath, output_file_path, density_per_line, height_name):

    poly_file = []

    with fiona.open(shape_filepath, 'r') as source:
        for feature in source:
            segment = LineString(feature['geometry']['coordinates'])
            schema = source.schema['properties']
            if height_name in schema:
                if feature['properties'][height_name] is None:
                    return "Enter heights in all the height fields"
                else:
                    for coord in segment.coords:
                        float_height = feature['properties'][height_name]
                        lake_height = float(float_height)
                        # Append adjusted point
                        poly_file.append(
                            f"{coord[0]} {coord[1]} {lake_height}\n")
                    poly_file.append("\n")

            else:

                return f"The Lake shapefile does not have the field {height_name}."

    polylines = []
    point_clouds = []

    for i in range(len(poly_file) - 1):
        parts_current = poly_file[i].strip().split()
        parts_next = poly_file[i + 1].strip().split()

        if len(parts_current) >= 3 and len(parts_next) >= 3:
            x1, y1, z1 = map(float, parts_current[:3])
            x2, y2, z2 = map(float, parts_next[:3])
            polylines.append([(x1, y1, z1), (x2, y2, z2)])

    points_density_per_line = density_per_line

    for polyline in polylines:   # Generate point clouds along each polyline
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

def lake_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'lake.shp')
    lake_lasfile = Path(project_folder, 'lake.las')
    others_filename= Path(project_folder, 'others.shp')
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'lake.shx'))
            os.remove(Path(project_folder, 'lake.dbf'))
            os.remove(Path(project_folder, 'lake.cpg'))
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
    
    if os.path.exists(lake_lasfile):
        try:
            os.remove(lake_lasfile)
        except:
            pass


def lake_shapefile_processing(shapefile_path, label_name,split_label):
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
            # if label not in output_shapefiles:
            if label not in output_shapefiles:
                if label == label_name:
                    output_shapefile_path = os.path.join(
                    output_directory, f"lake.shp")

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

                output_shapefile = output_shapefiles[label]
            
            output_shapefile.write(feature)
                    
    for label, output in output_shapefiles.items():
        output.close()


label = "DTM Tools/Lake Breaklines"
Metashape.app.addMenuItem(label, lake_processing)
print("To execute this script press {}".format(label))
