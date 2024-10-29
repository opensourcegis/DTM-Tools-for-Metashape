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
from shapely.geometry import LineString, Point, mapping, shape
import textwrap
from scipy.spatial import KDTree


def river_processing():
    # Reading project from Metashape
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

            self.setWindowTitle("HydroFlattening of Rivers")
            self.setGeometry(500, 250, 500, 400)
            self.setFixedSize(500, 400)

            self.btnP1 = QtWidgets.QPushButton("&Execute")
            self.btnP1.clicked.connect(self.execute)

            self.chunkTxt = QtWidgets.QLabel()
            self.chunkTxt.setText("Enter River Center Desciption:")
            self.typeTxt = QtWidgets.QLabel()
            self.typeTxt.setText("Enter River Edge Description")
            self.t1 = QtWidgets.QLineEdit(self)
            self.t2 = QtWidgets.QLineEdit(self)
            self.t3 = QtWidgets.QLineEdit(self)
            self.t4 = QtWidgets.QLineEdit(self)

            self.type2Txt = QtWidgets.QLabel()
            self.type2Txt.setText("Enter Upstream height:")
            self.type3Txt = QtWidgets.QLabel()
            self.type3Txt.setText("Enter Downstream height:")
        

            layout = QtWidgets.QGridLayout()
            layout.setContentsMargins(20, 0, 20, 0)
            layout.addWidget(self.typeTxt, 1, 0, 1,2)
            layout.addWidget(self.type2Txt, 2, 0,1,2)
            layout.addWidget(self.type3Txt, 3, 0,1,2)
        
            layout.addWidget(self.chunkTxt, 0, 0, 1, 2)
            layout.addWidget(self.t1, 0, 2)
            layout.addWidget(self.t2, 1, 2)
            layout.addWidget(self.t3, 2, 2)
            layout.addWidget(self.t4, 3, 2)

            layout.addWidget(self.btnP1, 4, 2)

            # self.progress_bar.setGeometry(200, 240, 250, 40)

            self.setLayout(layout)

            self.exec()

        def execute(self):

            center_label = self.t1.text()
            edge_label = self.t2.text()

            if center_label and edge_label:
                # Export Shapefiles from Metashape
                chunk.exportShapes(project_folder + '/shapes.shp', save_polylines=True,
                                   polygons_as_polylines=True, crs=chunk.crs)  # Export Point Cloud. Filter to be added
                shapefile_initial = Path(project_folder, 'shapes.shp')

                # Extract breaklines, rivercenter, riveredge and lakes from shapefile
                
                river_shapefile_processing(
                    shapefile_initial, center_label, edge_label)
                #self.progress_bar.setValue(30)
                

                riveredge_filename = Path(project_folder, 'riveredge.shp')
                rivercenter_filename = Path(project_folder, 'rivercenter.shp')
                # riveredge_lasfile = Path(project_folder, 'riveredge_points.las')

                # Convert Shape file to Poly file using Fiona
                if os.path.exists(riveredge_filename) and os.path.exists(rivercenter_filename):

                    if river_is_float(self.t3.text()) and river_is_float(self.t4.text()):
                        hydroflattening(rivercenter_filename, riveredge_filename, float(
                            self.t3.text()), float(self.t4.text()))
                        #self.progress_bar.setValue(80)
                        chunk.importPointCloud(
                            project_folder + '/riveredge_points.las', crs=chunk.crs, replace_asset=False)
                        message = "Edge Point Clouds Imported"
                        river_remove_assets()
                        Metashape.app.messageBox(textwrap.fill(message, 65))
                        self.close()
                        return None
                    else:
                        # print("There are no breaklines")
                        message = "Enter Valid Upstream and Downstream Heights."
                        Metashape.app.messageBox(textwrap.fill(message, 65))
                        river_remove_assets()
                        self.close()
                        return None

                else:
                    # print("There are no breaklines")
                    message = "There are No Riveredges and Rivercenters. Add Rivers to use this tool."
                    Metashape.app.messageBox(textwrap.fill(message, 65))
                    river_remove_assets()
                    self.close()
                    return None
            else:
                message = "Enter All Field Names"
                Metashape.app.messageBox(textwrap.fill(message, 65))
                
                return None

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()
    MyWindow(parent)


def hydroflattening(centerline_shapefile, riveredge_shapefile, upstream, downstream):
    input_shapefile = centerline_shapefile
    input_river_edge = riveredge_shapefile

    riveredge_lasfile = Path(project_folder, 'riveredge_points.las')

    start_height = upstream   # actual start height
    end_height = downstream     # actual end height

    adjusted_points = []
    polylines = []

    with fiona.open(input_shapefile, 'r') as source:
        for feature in source:
            segment = LineString(feature['geometry']['coordinates'])
            length = segment.length
            slope = (end_height - start_height) / length

            for i, (x, y, z) in enumerate(segment.coords):
                distance_from_start = segment.project(Point(x, y))
                new_height = start_height + slope * distance_from_start
                # Append adjusted point
                adjusted_points.append(f'{x} {y} {new_height}\n')

    for i in range(len(adjusted_points) - 1):
        parts_current = adjusted_points[i].strip().split()
        parts_next = adjusted_points[i + 1].strip().split()

        if len(parts_current) >= 3 and len(parts_next) >= 3:
            x1, y1, z1 = map(float, parts_current[:3])
            x2, y2, z2 = map(float, parts_next[:3])
            polylines.append([(x1, y1, z1), (x2, y2, z2)])

    centerline_points = []
    points_density_per_line = 50
    for polyline in polylines:   # Generate point clouds along each polyline
        points = np.array(polyline)
        dist = np.linalg.norm(points[0] - points[-1])
        interpolated_points = np.linspace(
            points[0], points[-1], round(points_density_per_line*dist))

        centerline_points.extend(interpolated_points)

    # Create KDTree for fast nearest neighbor search on centerline points
    centerline_tree = KDTree([(x, y) for x, y, _ in centerline_points])
    height_file = []
    # Open river edge shapefile for reading
    with fiona.open(input_river_edge, 'r') as source:
        # Open the output .poly file for writing

        for feature in source:
            geometry = feature['geometry']
            coordinates = geometry['coordinates']

            # Create a LineString from the river edge coordinates
            river_edge_line = LineString(coordinates)

            interpolated_points = []
            step = 0.2
            distance = 0.0
            while distance < river_edge_line.length:
                point = river_edge_line.interpolate(distance)
                interpolated_points.append(point)
                distance += step

            # Find nearest centerline point for each interpolated point
            for interpolated_point in interpolated_points:
                x, y = interpolated_point.x, interpolated_point.y
                # Find nearest point on centerline
                _, index = centerline_tree.query((x, y))
                _, _, height = centerline_points[index]
                height_file.append(f'{x} {y} {height}\n')
            height_file.append("\n")

        edge_points = []
        for i in range(len(height_file) - 1):
            parts_current = height_file[i].strip().split()
            parts_next = height_file[i + 1].strip().split()

            if len(parts_current) >= 3 and len(parts_next) >= 3:
                x1, y1, z1 = map(float, parts_current[:3])
                x2, y2, z2 = map(float, parts_next[:3])
                edge_points.append([(x1, y1, z1), (x2, y2, z2)])

    point_clouds = []

    points_density_per_line = 100

    for polyline in edge_points:   # Generate point clouds along each polyline
        points = np.array(polyline)
        dist = np.linalg.norm(points[0] - points[-1])
        interpolated_points = np.linspace(
            points[0], points[-1], round(points_density_per_line*dist))
        point_clouds.append(interpolated_points)
    # Combine all point clouds into a single array
    all_points = np.vstack(point_clouds)

    header = laspy.LasHeader(point_format=3, version="1.2")
    header.scales = np.array([0.01, 0.01, 0.01])
    header.offsets = np.min(all_points, axis=0)

    las_write = laspy.LasData(header=header)
    las_write.x = all_points[:, 0]
    print(all_points[:, 0])
    las_write.y = all_points[:, 1]
    las_write.z = all_points[:, 2]

    # Set ground classification for all points
    # 2 represents ground classification
    las_write.raw_classification = np.full(len(all_points), 2)
    las_write.write(riveredge_lasfile)

def river_remove_assets():
    initial_filename = Path(project_folder, 'shapes.shp')
    shapefile_filename = Path(project_folder, 'rivercenter.shp')
    edge_filename = Path(project_folder, 'riveredge.shp')
    lasfile = Path(project_folder, 'riveredge_points.las')
    others_filename= Path(project_folder, 'others.shp')
    if os.path.exists(shapefile_filename):
        try:
            os.remove(shapefile_filename)
            os.remove(Path(project_folder, 'rivercenter.shx'))
            os.remove(Path(project_folder, 'rivercenter.dbf'))
            os.remove(Path(project_folder, 'rivercenter.cpg'))
            os.remove(Path(project_folder, 'rivercenter.prj'))
        except:
            pass
    if os.path.exists(edge_filename):
        try:
            os.remove(edge_filename)
            os.remove(Path(project_folder, 'riveredge.shx'))
            os.remove(Path(project_folder, 'riveredge.dbf'))
            os.remove(Path(project_folder, 'riveredge.cpg'))
            os.remove(Path(project_folder, 'riveredge.prj'))
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
    
    if os.path.exists(lasfile):
        try:
            os.remove(lasfile)
        except:
            pass


def river_shapefile_processing(shapefile_path, river_center, river_edge):
    input_shapefile = shapefile_path
    # Create a directory to store the output shapefiles
    output_directory = project_folder
    os.makedirs(output_directory, exist_ok=True)

    split_attribute = "DESCRIPTIO"  # Default is DESCRIPTIO as per Metashape

    # Initialize a dictionary to store output shapefiles
    output_shapefiles = {}

    # Iterate through features and split into output shapefiles
    with fiona.open(input_shapefile) as src:
        schema = src.schema.copy()

        for feature in src:
            label = feature['properties'][split_attribute]
            if label not in output_shapefiles:
                if label == river_edge:
                    print('label', label)
                    output_shapefile_path = os.path.join(
                        output_directory, f"riveredge.shp")

                    output_shapefile = fiona.open(
                        output_shapefile_path, 'w', 'ESRI Shapefile', schema)
                    output_shapefiles[label] = output_shapefile
                elif label == river_center:
                    print('label', label)
                    output_shapefile_path = os.path.join(
                        output_directory, f"rivercenter.shp")

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
     # Close output shapefiles
    for label, output in output_shapefiles.items():
        output.close()


def river_is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


label = "DTM Tools/HydroFlattening Rivers"
Metashape.app.addMenuItem(label, river_processing)
print("To execute this script press {}".format(label))
