# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SARFloodAT
                                 A QGIS plugin
 SAR Flood Mapping
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-10-02
        copyright            : (C) 2024 by Lei Wang
        email                : leiwang@lsu.edu
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""
import os 
from .scripts.utils import *
import subprocess,sys,os
from subprocess import Popen, PIPE
   
   
#print("Checking needed packages from requirement.txt")
package_dir = os.path.dirname(__file__)    
python = os.path.join(os.path.dirname(sys.executable),"python.exe")
setup = os.path.join(os.path.dirname(sys.executable),"setup.py")
           
requirement_file = os.path.join(package_dir,'requirements.txt')
strings=[]

with open(requirement_file,'r') as f:
    lines=f.readlines()
    for l in lines:
        strings.append(l)
#print(f"Packages from requirements.txt{strings}")
import pkg_resources

for pack in strings:
    try:
        dist = pkg_resources.get_distribution(pack)
 #       print('{} ({}) is installed'.format(dist.key, dist.version))
    except pkg_resources.DistributionNotFound:
        print('{} is NOT installed'.format(pack))
        if create_message("Install libs","install the required libraries\n"+pack) == QMessageBox.Yes:
            try:
                p = Popen([python,"-m","pip","install",pack],stdout=PIPE, stderr=PIPE, text=True)  
                stdout, stderr = p.communicate()

                print(stdout) 
            except subprocess.CalledProcessError as e:
                print(f"Error occurred during extension build: {e}")
                stdout, stderr = p.communicate()
                print(stderr) 
    
            

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SARFloodAT class from file SARFloodAT.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .SARFloodMapping import SARFloodAT
    return SARFloodAT(iface)

