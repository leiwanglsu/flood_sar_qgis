# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SARFloodAT
                                 A QGIS plugin
 SAR Flood Mapping
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-10-02
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Lei Wang
        email                : leiwang@lsu.edu
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import Qgis, QgsMessageLog, QgsApplication



# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .SARFloodMapping_dialog import (geeDataDialog,PrepareImageDialog,
                                     RegionGrowDialog, RegionSplitDialog, 
                                     BimodalDialog, FilterDialog,InterpDialog,
                                     AllStepsDialog)

import os.path
from .scripts.geeData import getGeeData
from .scripts.imagePrep import imagePrep
from .scripts.utils import readImageGDAL,writeImageGDAL
from .scripts.region_split import region_split
from .scripts.multigamma import bimodalFit
from .scripts.filter import filterOutliers
from .scripts.idw2flood import interpFlood
from .scripts.rgrow import regionGrow
from .scripts.tasks import MyBackgroundTask,example_task_function
import numpy as np
def example_func(a, b):
    print("example function, a * b")
    return a * b
class SARFloodAT:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SARFloodAT_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SAR Flood Mapping')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.tm = QgsApplication.taskManager()


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SARFloodAT', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SARFloodMapping/icon.png'
        menu_items = {
            "geeData":self.loadGeeData,
            "Mosaic and clipping": self.imagePreparation,
            "Region grow": self.regionGrow,
            "Multiresolution tiling": self.regionSplit,
            "Bimodal fitting": self.bimodalFitting,
            "Filter outliers": self.filterOutliers,
            "Interpolation and thresholding": self.idwThresholding,
        }
        for idx,key in enumerate(menu_items):
            
            self.add_action(
                icon_path,
                text=self.tr(f"step {idx+1}: {key}"),
                callback=menu_items[key],
                parent=self.iface.mainWindow())
        self.add_action(
                icon_path,
                text=self.tr(f"All steps 3 - 7"),
                callback=self.allSteps,
                parent=self.iface.mainWindow())
        # will be set False in run()
        self.geeData = False
        self.prepImage = False
        self.regrow_flag = False
        self.region_split_flag = False
        self.bimodal_flag = False
        self.filter_flag = False
        self.interpFlood_flag = False
        self.allsteps_flag = False



    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SAR Flood Mapping'),
                action)
            self.iface.removeToolBarIcon(action)

    def loadGeeData(self):
        if self.geeData == False:
            self.geeData = True
            self.gee_dlg = geeDataDialog()
        self.gee_dlg.show()
        result = self.gee_dlg.exec_()
        # See if OK was pressed
        if result:
            import ee
            ee.Initialize()
            workspace = self.gee_dlg.mQgsFileWidget.filePath()
            extent = self.gee_dlg.mSExtent.text()
            s1_date = self.gee_dlg.mSDate.text()
            wkid = self.gee_dlg.mSWKID.text()
            bDownloadJRC = self.gee_dlg.bDownloadJRC
            bDownloadS1 = self.gee_dlg.bDownloadS1
            #QgsMessageLog.logMessage(f'{workspace},{extent},{s1_date},{wkid}', 'SARFloodMapping Plugin',level=Qgis.Info)
            getGeeData(workspace,extent,s1_date,wkid,download_jrc=bDownloadJRC,download_s1=bDownloadS1)
    def regionGrow(self):
        if self.regrow_flag == False:
            self.regrow_flag = True
            self.rgrow_dlg = RegionGrowDialog()
        self.rgrow_dlg.show()
        result = self.rgrow_dlg.exec_()
        # See if OK was pressed
        if result:        
            seed_image_path = self.rgrow_dlg.mSeedImage.filePath()
            grow_image_path = self.rgrow_dlg.mGrowImage.filePath()
            threshold = float(self.rgrow_dlg.mThreshold.text())
            workspace = self.rgrow_dlg.mWorkspace.filePath()
            task1 = MyBackgroundTask("regionGrow",regionGrow, 
                                     workspace,seed_image_path, grow_image_path,threshold)
            self.tm.addTask(task1)            
            #regionGrow(workspace,seed_image_path, grow_image_path,threshold)
            
    def regionSplit(self):
        if self.region_split_flag == False:
            self.region_split_flag = True
            self.regionSplit_dlg = RegionSplitDialog()  
        self.regionSplit_dlg.show()
        result = self.regionSplit_dlg.exec_()
        if result:
            workspace = self.regionSplit_dlg.mWorkspace.filePath()
            waterImg = self.regionSplit_dlg.mWater.filePath()
            threshold = float(self.regionSplit_dlg.mThreshold.text())
            tile_size = float(self.regionSplit_dlg.mTilesize.text())
            levels = int(self.regionSplit_dlg.mLevels.text()) 
            task1 = MyBackgroundTask("Multiresolution tiling",region_split,
                                    workspace=workspace,
                                    water_image_path=waterImg,
                                    threshold=threshold,
                                    tile_size=tile_size,
                                    levels=levels)
            self.tm.addTask(task1)            
            # region_split(workspace=workspace,
            #                 water_image_path=waterImg,
            #                 threshold=threshold,
            #                 tile_size=tile_size,
            #                 levels=levels) 
    def bimodalFitting(self):
        if self.bimodal_flag == False:
            self.bimodal_flag = True
            self.bimodal_dlg = BimodalDialog()
        self.bimodal_dlg.show()
        self.bimodal_dlg.exec_()  
        if self.bimodal_dlg.result():
            workspace = self.bimodal_dlg.mWorkspace.filePath()
            sarImg = self.bimodal_dlg.mSAR.filePath()
            regions = self.bimodal_dlg.mRegions.filePath()
            gamma = self.bimodal_dlg.mGamma.text()



            task1 = MyBackgroundTask("Bimodal fitting",bimodalFit,
                                    workspace=workspace,
                                    sarImage = sarImg,
                                    regions = regions,
                                    gamma = gamma)
            self.tm.addTask(task1)
            # bimodalFit(workspace=workspace,
            #             sarImage = sarImg,
            #             regions = regions,
            #             gamma = gamma)
    def imagePreparation(self):
        if self.prepImage == False:
            self.prepImage = True
            self.prepareImage_dlg = PrepareImageDialog()
        self.prepareImage_dlg.show()
        result = self.prepareImage_dlg.exec_()
        # See if OK was pressed
        if result:        
            workspace = self.prepareImage_dlg.mWorkspace.filePath()
            sarImg = self.prepareImage_dlg.mSAR.filePath().split('" "')
            sarImg = [f.strip('"') for f in sarImg if f]
            jrcImg = self.prepareImage_dlg.mJRC.filePath()
            threshold = int(self.prepareImage_dlg.mThreshold.text())
            lower_left = self.prepareImage_dlg.mLL.text()
            upper_right = self.prepareImage_dlg.mUR.text()
            task1 = MyBackgroundTask("imagePrep",imagePrep,
                                     sarImg,jrcImg,workspace,threshold,lower_left, upper_right)
            self.tm.addTask(task1)             
        #   imagePrep(sarImg,jrcImg,workspace,threshold,lower_left, upper_right)
            
    def filterOutliers(self):
        if self.filter_flag == False:
            self.filter_flag = True
            self.filterDialog = FilterDialog()
        self.filterDialog.show()
        result = self.filterDialog.exec_()
        if result:
            workspace = self.filterDialog.mWorkspace.filePath()
            threshold_pnts = self.filterDialog.mThresholdPoints.filePath()
            BC = self.filterDialog.mBC.text()
            task1 = MyBackgroundTask("filterOutliers",filterOutliers,
                                    workspace = workspace,
                                    threshold_points = threshold_pnts,
                                    BC = BC)
            self.tm.addTask(task1)              
            # filterOutliers(workspace = workspace,
            #                threshold_points = threshold_pnts,
            #                BC = BC)
    def idwThresholding(self):
        if self.interpFlood_flag == False:
            self.interpFlood_flag = True
            self.interpDialog = InterpDialog()
        self.interpDialog.show()
        result = self.interpDialog.exec_()
        if result:
            workspace = self.interpDialog.mWorkspace.filePath()
            threhsold_pnts = self.interpDialog.mThresholdPnts.filePath()
            field_name = self.interpDialog.mField.text()
            sarImg = self.interpDialog.mSAR.filePath()
            power_term = float(self.interpDialog.mPower.text())
            task1 = MyBackgroundTask("interpFlood",interpFlood,
                                    workspace = workspace,
                                    threshold_points = threhsold_pnts,
                                    field = field_name,
                                    sarImage = sarImg,
                                    power = power_term)
            self.tm.addTask(task1)               
            # interpFlood(workspace = workspace,
            #             threshold_points = threhsold_pnts,
            #             field = field_name,
            #             sarImage = sarImg,
            #             power = power_term)
    def allSteps(self):
                
        if self.allsteps_flag == False:
            self.allsteps_flag = True
            self.allstepsDialog = AllStepsDialog()
        self.allstepsDialog.show()
        result = self.allstepsDialog.exec_()
        if result:
            workspace = self.allstepsDialog.mWorkspace.filePath()
            
            # step 1 Image preparation
            sarImg = self.allstepsDialog.mSAR.filePath().split('" "')
            sarImg = [f.strip('"') for f in sarImg if f]
            jrcImg = self.allstepsDialog.mJRC.filePath()
            threshold_water_occurrence = float(self.allstepsDialog.mThresholdOccurence.text())
            lower_left = self.allstepsDialog.mLL.text()
            upper_right = self.allstepsDialog.mUR.text()
            task1 = MyBackgroundTask("imagePrep",imagePrep,
                            sarImg,jrcImg,workspace,threshold_water_occurrence,lower_left, upper_right)
            current_task = task1
            
            #step 2 rgrow
            sarImg = os.path.join(workspace,"sar.tif")
            inital_water_threshold = float(self.allstepsDialog.mThresholdWater.text())

            out_image_path = os.path.join(workspace,"permanent_water.tif")
            seed_image_path = os.path.join(workspace,"jrc_watermask.tif")
            next_task = MyBackgroundTask("regionGrow",regionGrow,
                                     workspace,seed_image_path, sarImg,inital_water_threshold)
            current_task.next_task = next_task
            current_task = next_task
            

            # Step 3 region split
            threshold_water_percent = float(self.allstepsDialog.mThresholdPercent.text())
            tilesize = float(self.allstepsDialog.mTilesize.text())
            levels = int(self.allstepsDialog.mLevels.text())

            next_task = MyBackgroundTask("Multiresolution tiling", region_split,
                                    workspace=workspace,
                                    water_image_path=out_image_path,
                                    threshold=threshold_water_percent,
                                    tile_size=tilesize,
                                    levels=levels) 
            current_task.next_task = next_task
            current_task = next_task
            
            #step 4 bimodal fitting
            gamma_parameter = self.allstepsDialog.mGamma.text()

            regions = os.path.join(workspace,"regions.shp")
            next_task = MyBackgroundTask("Bimodal fitting",bimodalFit, 
                                     workspace=workspace,
                                    sarImage = sarImg,
                                    regions = regions,
                                    gamma = gamma_parameter)
            current_task.next_task = next_task
            current_task = next_task            

            # step 5 filter
            threshold_pnts = os.path.join(workspace,"threshold.shp")
            BC = float(self.allstepsDialog.mBC.text())
            
            next_task = MyBackgroundTask("FilterOutliers", filterOutliers,
                                    workspace = workspace,
                                    threshold_points = threshold_pnts,
                                    BC = BC)          
            current_task.next_task = next_task
            current_task = next_task              

            # Step 6 interpolation
            power = float(self.allstepsDialog.mPower.text())
            thresohld_filtered = os.path.join(workspace,"threshold_filtered.shp")
            
            next_task = MyBackgroundTask("Interpolate", interpFlood,
                                    workspace = workspace,
                                    threshold_points = thresohld_filtered,
                                    field = "threshold",
                                    sarImage = sarImg,
                                    power = power)
            current_task.next_task = next_task
            current_task = next_task             
            # Chain tasks sequentially

            self.tm.addTask(task1)

           

