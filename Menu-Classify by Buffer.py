""" Tool to generate DTM from Drone Imagery in Agisoft Metashape
    CSF FILTER
    Build for:
    Version: 2.0
    Python Version: 3.9
    Addl. Dependencies req: numpy, laspy, CSF
"""
# Dependencies
import numpy as np

import Metashape
from tkinter import *
import os
from pathlib import Path
import fiona
from shapely.geometry import LineString, Point, mapping, shape
import textwrap
import time
from PySide2 import QtGui, QtCore, QtWidgets



def buffer_processing():
    # Reading project from Metashape
    global doc, chunk,project_folder,project_path,shapes

    doc = Metashape.app.document
    chunk = doc.chunk
    shapes=Metashape.Shapes
    project_path = doc.path
    project_folder = os.path.dirname(project_path)
    #point_cloud = chunk.point_cloud
    # Main window for GUI using Tkinter
    class MyWindow(QtWidgets.QDialog):
        def __init__(self, parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Classify points within Polygons")
            self.setGeometry(500, 250, 500, 200)
            self.setFixedSize(500, 300)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter Buffer (m):")
            self.t1 = QtWidgets.QLineEdit(self)
            self.t2 = QtWidgets.QLineEdit(self)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setValue(0)
            self.progress_bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.typeTxt = QtWidgets.QLabel()
            self.typeTxt.setText("Enter the name of")
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

            layout.addWidget(self.btnP1, 3, 1)

            layout.addWidget(self.progress_bar, 2, 1)
            # self.progress_bar.setGeometry(200, 240, 250, 40)

            self.setLayout(layout)

            self.exec()


        def execute(self):

            if 0.05< float(self.t1.text()) < 5.1:  # Best in this range

                chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=False,
                                   save_polygons=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
                shapefile_initial = Path(project_folder, 'shapes.shp')

                # Extract breaklines, rivercenter, riveredge and lakes from shapefile
                shapefile_filename = Path(project_folder, 'buffer.shp')

                input_label = self.t2.text()
                combo_text = self.typeCmb.currentText()

                if combo_text=="Label:":
                    split_label="NAME"
                elif combo_text=="Description:":
                    split_label="DESCRIPTIO"
                elif combo_text=="Layer:":
                    split_label="LAYER"
                if input_label:
                    buffer_shapefile(shapefile_initial,shapefile_filename,float(self.t1.text()),split_label,input_label)
                else:
                    buffer_shapefile(shapefile_initial,shapefile_filename,float(self.t1.text()),split_label)
                
                # Convert Shape file to Poly file using Fiona
                if os.path.exists(shapefile_filename):
               
                    new_group=chunk.shapes.addGroup()
                    new_group.label="Delete"
                    chunk.shapes.group=new_group
                    #chunk.shapes=chunk.shapes.groups[-1]
                    #chunk.shapes.groups[0].label="Required"
                    chunk.importShapes(project_folder + '/buffer.shp',crs=chunk.crs)

                    new =[]
                    for shape in list(chunk.shapes):
                        if shape.group==chunk.shapes.groups[-1]:
                            new.append(shape)
            

                    point_cloud=chunk.point_cloud
                    # shapes=chunk.shapes
                    point_cloud.selectPointsByShapes(new)
                    point_cloud.assignClassToSelection(target=1)
                    #chunk.shapes.group=chunk.shapes.groups[0]
                    
                    chunk.shapes.remove(chunk.shapes.groups[-1])
                    
                    for shape in list(chunk.shapes):
                        if shape.group==chunk.shapes.groups[-1]:
                            chunk.shapes.remove(shape)
                    chunk.shapes.group=chunk.shapes.groups[0]
                    chunk.shapes.remove(chunk.shapes.groups[-1]
                                            )       

                    message = "Points Classified for given Buffer"
                    self.close()
                    Metashape.app.messageBox(textwrap.fill(message, 65))
                    buffer_remove_assets()

                    
                    return None  
                else:
                
                    message = "There are no polygons in given field"
                    
                    Metashape.app.messageBox(textwrap.fill(message, 65))
                    buffer_remove_assets()
                    
                    return None

            else:
             
                message = "Enter value between 0.1 to 5"
                Metashape.app.messageBox(textwrap.fill(message, 65))
                
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)




def buffer_shapefile(input_shapefile,output_shapefile,buffer,split_label,input_label=None):
    # Open the input shapefile for reading
    output_directory=project_folder
    with fiona.open(input_shapefile, 'r') as src:

        # Get the schema and crs of the source shapefile
        schema = src.schema
        crs = src.crs
        
        output_shapefiles = {}

        # Create a new shapefile for writing with buffered polygons
        
        for feature in src:
                label = feature['properties'][split_label]
                if label not in output_shapefiles:
                    if feature['geometry']['type'] == 'Polygon'and label==input_label:
                    # Get the geometry of the feature
                        output_shape= fiona.open(
                            output_shapefile, 'w', 'ESRI Shapefile', schema, crs=crs)
                        output_shapefiles[label] = output_shape
                        geom = shape(feature['geometry'])

                        # Create a buffer of 5 meters around the polygon
                        buffered_geom = geom.buffer(buffer)  # Adjust the buffer distance as needed

                        # Create a new feature with the buffered geometry
                        feature = {
                            'geometry': mapping(buffered_geom),
                            'properties': feature['properties']
                        }
                    else:
                        output_shapefile_path = os.path.join(
                                output_directory, f"others.shp")

                        output_shape= fiona.open(
                            output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                        output_shapefiles[label] = output_shape
                else:
                    if feature['geometry']['type'] == 'Polygon':
                        geom = shape(feature['geometry'])
                        buffered_geom = geom.buffer(buffer)  # Adjust the buffer distance as needed

                        # Create a new feature with the buffered geometry
                        feature = {
                            'geometry': mapping(buffered_geom),
                            'properties': feature['properties']
                        }
                        output_shape=output_shapefiles[label]
                    else:
                        output_shapefile_path = os.path.join(
                                output_directory, f"others.shp")

                        output_shape= fiona.open(
                            output_shapefile_path, 'w', 'ESRI Shapefile', schema)


                # Write the new feature to the output shapefile
                output_shape.write(feature)
    
    for label, output in output_shapefiles.items():
        output.close()

def buffer_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'buffer.shp')
    others_filename = Path(project_folder, 'others.shp')
    
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'buffer.shx'))
            os.remove(Path(project_folder, 'buffer.dbf'))
            os.remove(Path(project_folder, 'buffer.cpg'))
            os.remove(Path(project_folder, 'buffer.prj'))
            
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

label = "DTM Tools/Classify Buffer Points"
Metashape.app.addMenuItem(label, buffer_processing)
print("To execute this script press {}".format(label))
