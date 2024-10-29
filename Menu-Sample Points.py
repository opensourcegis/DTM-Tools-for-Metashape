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
from PySide2 import QtGui, QtCore, QtWidgets
import os
from pathlib import Path
import fiona
import textwrap
from shapely.geometry import LineString, Point, shape
import trimesh


# Reading project from Metashape


def break_sample_point_processing():
    global doc, chunk, project_folder, project_path
    doc = Metashape.app.document
    chunk = doc.chunk
    project_path = doc.path
    project_folder = os.path.dirname(project_path)

    # Main window for GUI using Tkinter
    class MyWindow(QtWidgets.QDialog):
        def __init__(self, parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Sample Points inside Breakline Polygon")
            self.setGeometry(500, 250, 500, 300)
            self.setFixedSize(500, 300)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter No. of Points per sq.m required (10-50)")
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

        def execute(self):

            try:
                if not (9 < int(self.t1.text()) < 51):
                    raise ValueError
            except ValueError:
                message = "Enter Integer Value between 10 and 50"
                Metashape.app.messageBox(textwrap.fill(message, 65))
              
                return None
           
            combo_text = self.typeCmb.currentText()
            if combo_text=="Label:":
                    split_label="NAME"
            elif combo_text=="Description:":
                split_label="DESCRIPTIO"
            elif combo_text=="Layer:":
                split_label="LAYER"

                # Export Shapefiles from Metashape
            chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=False,
                               save_polygons=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
            shapefile_initial = Path(project_folder, 'shapes.shp')
            self.progress_bar.setValue(30)

            label_name = self.t2.text()
            if label_name:
                sample_break_shapefile_processing(
                    shapefile_initial, split_label,label_name)
            else:
                sample_break_shapefile_processing(shapefile_initial,split_label)

            self.progress_bar.setValue(60)
            shapefile_filename = Path(
                project_folder, 'breaklines_samples.shp')
            breakline_lasfile = Path(
                project_folder, 'breaklines_samples.las')

            # Convert Shape file to Poly file using Fiona
            if os.path.exists(shapefile_filename):
                break_sample_point(
                    shapefile_filename, breakline_lasfile, int(self.t1.text()))
                self.progress_bar.setValue(90)
                chunk.importPointCloud(
                    project_folder + '/breaklines_samples.las', crs=chunk.crs, replace_asset=False)

                message = "Sampled Points imported to the Project"
                self.close()
                Metashape.app.messageBox(textwrap.fill(message, 65))
                samplebreak_remove_assets()
                return None
                
            else:

                message = "There are no shapes for given field"
                Metashape.app.messageBox(textwrap.fill(message, 65))
                self.close()
                samplebreak_remove_assets()
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)


def break_sample_point(input_shape, output_las, density=20):
    mesh_points = []

    # Open the shapefile and extract 3D points
    with fiona.open(input_shape) as src:

        for feature in src:
            polygon = shape(feature['geometry'])
            geometry = feature['geometry']
            coordinates = geometry['coordinates']
            points = np.vstack(coordinates[0])

            mesh = trimesh.Trimesh(vertices=points, faces=[
                                   list(range(len(coordinates[0])))])

            mesh_area = mesh.area

            num_points = int(mesh_area)*density
            # Sample points on the mesh
            sampled_points, face_indices = trimesh.sample.sample_surface_even(
                mesh, num_points)
            # mesh_points.extend(sampled_points)

            # all_points1=[]
            for i in range(len(sampled_points)):
                if polygon.contains(Point(sampled_points[i])):
                    mesh_points.append(sampled_points[i])
        # all_points1 = [point for point in mesh_points if polygon.contains(Point(point))]
        all_points = np.array(mesh_points)
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

def samplebreak_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'breaklines_samples.shp')
    lasfilename = Path(project_folder, 'breaklines_samples.las')
    others_filename = Path(project_folder, 'others.shp')
    
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'breaklines_samples.shx'))
            os.remove(Path(project_folder, 'breaklines_samples.dbf'))
            os.remove(Path(project_folder, 'breaklines_samples.cpg'))
            os.remove(Path(project_folder, 'breaklines_samples.prj'))
            
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



def sample_break_shapefile_processing(shapefile_path, split_label,input_label=None):
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
                    # print(label)
                    output_shapefile_path = os.path.join(
                    output_directory, f"breaklines_samples.shp")
                    output_shape= fiona.open(
                        output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                    output_shapefiles[label] = output_shape
                else:
                    output_shapefile_path = os.path.join(
                            output_directory, f"others.shp")

                    output_shape= fiona.open(
                        output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                    output_shapefiles[label] = output_shape
            else:
                output_shape=output_shapefiles[label]


                # Write the new feature to the output shapefile
            output_shape.write(feature)
    
    for label, output in output_shapefiles.items():
        output.close()

label = "DTM Tools/Sample Points inside polygon"
Metashape.app.addMenuItem(label, break_sample_point_processing)
print("To execute this script press {}".format(label))
