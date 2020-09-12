#!/bin/bash
ls -l /opt/qunex/niutilities
find /opt/qunex/niutilities/niutilities -type f | xargs grep -l "toHCPLS"
find /opt/qunex/niutilities/niutilities -type f | xargs grep "toHCPLS"
find /opt/qunex/niutilities/niutilities -type f | xargs grep -l "mapIO"
find /opt/qunex/niutilities/niutilities -type f | xargs grep "mapIO"
echo "cat /opt/qunex/niutilities/niutilities/g_process.py"
cat /opt/qunex/niutilities/niutilities/g_process.py
echo "cat /opt/qunex/niutilities/niutilities/HCP/ge_HCP.py"
cat /opt/qunex/niutilities/niutilities/HCP/ge_HCP.py
echo "cat /opt/qunex/niutilities/niutilities/g_commands.py"
cat /opt/qunex/niutilities/niutilities/g_commands.py
echo "cat /opt/qunex/niutilities/niutilities/g_utilities.py"
cat /opt/qunex/niutilities/niutilities/g_utilities.py

