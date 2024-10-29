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
import os
from pathlib import Path
import CSF
import textwrap
from PySide2 import QtGui, QtCore, QtWidgets

# Define the Main Function to call from Menu


def CSF_processing():
    # Reading project from Metashape

    global doc, chunk, project_path, project_folder

    doc = Metashape.app.document
    chunk = doc.chunk
    project_path = doc.path
    project_folder = os.path.dirname(project_path)

    # Main window for GUI using Tkinter
    class MyWindow(QtWidgets.QDialog):
        def __init__(self, parent):
            QtWidgets.QDialog.__init__(self, parent)

            self.setWindowTitle("Classify Ground Points using CSF Filter")
            self.setGeometry(500, 250, 500, 400)
            self.setFixedSize(500, 400)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Cloth Resolution (1.0 - 1.5):")
            self.typeTxt = QtWidgets.QLabel()
            self.typeTxt.setText("Class Threshold (0.01 - 0.5)")
            self.t1 = QtWidgets.QLineEdit(self)
            self.t2 = QtWidgets.QLineEdit(self)

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setValue(0)
            self.progress_bar.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.type2Txt = QtWidgets.QLabel()
            self.type2Txt.setText("Terrain Type")
            self.typeCmb = QtWidgets.QComboBox()
            ASSET_TYPES = ["Flat", "Relief", "Steep Slope"]
            for type in ASSET_TYPES:
                self.typeCmb.addItem(type)

            layout = QtWidgets.QGridLayout()
            layout.setContentsMargins(20, 0, 20, 0)
            layout.addWidget(self.typeTxt, 1, 0, 1, 2)
            layout.addWidget(self.type2Txt, 2, 0)
            layout.addWidget(self.typeCmb, 2, 2)
            layout.addWidget(self.chunkTxt, 0, 0, 1, 2)
            layout.addWidget(self.t1, 0, 2)
            layout.addWidget(self.t2, 1, 2)

            layout.addWidget(self.btnP1, 4, 1)

            layout.addWidget(self.progress_bar, 3, 1)
            # self.progress_bar.setGeometry(200, 240, 250, 40)

            self.setLayout(layout)

            self.exec()

        def execute(self):

            # Performs well within this values
            try:
                if 0.8 < float(self.t1.text()) < 2.5 and 0.005 < float(self.t2.text()) < 1:
                    combo_text = self.typeCmb.currentText()

                    if combo_text == "Flat":
                        terrain = 3
                    elif combo_text == "Relief":
                        terrain = 2
                    elif combo_text == "Steep Slope":
                        terrain = 1
                    # Export Pointcloud to Project Folder
                    coordSystem = Metashape.app.getCoordinateSystem(
                        "Select Coordinate System", doc.chunk.crs)  # get coordinate system
                    doc.chunk.crs = coordSystem

                    # export as point_cloud_classification
                    las_filename = Path(
                        project_folder, 'point_cloud_classification.las')

                    # Export Point Cloud. Filter to be added - to be optimised without exports and noise filtered
                    chunk.exportPointCloud(project_folder + '/point_cloud_classification.las',
                                           source_data=Metashape.PointCloudData, crs=chunk.crs)

                    self.progress_bar.setValue(20)
                    # Perform CSF Filter
                    csf = CSF.CSF()
                    csf.params.bSloopSmooth = False
                    csf.params.cloth_resolution = float(self.t1.text())
                    csf.params.iterations = 500
                    csf.params.rigidness = terrain
                    csf.params.class_threshold = float(self.t2.text())
                    input_File = laspy.read(las_filename)
                    xyz = np.vstack((input_File.x, input_File.y,
                                    input_File.z)).transpose()
                    csf.setPointCloud(xyz)
                    ground = CSF.VecInt()
                    non_ground = CSF.VecInt()
                    csf.do_filtering(ground, non_ground)
                    points = input_File.points
                    out_File = laspy.LasData(input_File.header)

                    self.progress_bar.setValue(40)

                    out_File.points = points
                    classification = [1 for i in range(
                        0, len(points))]  # 1 for non-ground
                    for i in range(0, len(ground)):
                        classification[ground[i]] = 2

                    out_File.classification = classification

                    # OverWrite CSF Filtered Las File as point_cloud_classification
                    out_File.write(las_filename)

                    self.progress_bar.setValue(90)

                    chunk.importPointCloud(
                        project_folder + '/point_cloud_classification.las', crs=chunk.crs, replace_asset=False)
                    message = " Classified Point Cloud imported "
                    self.close()
                    Metashape.app.messageBox(textwrap.fill(message, 65))

                    return None

                else:
                    message = " Enter values in the range mentioned "
                    Metashape.app.messageBox(textwrap.fill(message, 65))
                    self.close()
                    return None

            except ValueError:
                message = " Enter values in the range mentioned "
                Metashape.app.messageBox(textwrap.fill(message, 65))
                self.close()
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)


label = "DTM Tools/CSF Filter"
Metashape.app.addMenuItem(label, CSF_processing)
print("To execute this script press {}".format(label))
