#!/usr/bin/python3

# A helper to install the recipes to python-for-android.

import os
import shutil
import subprocess
import sys

def copy_to_recipe_folder(folder_dir):
    for f in os.listdir(os.path.dirname(__file__)):
        if f.endswith(".py") and not f.startswith("__init__"):
            if os.path.exists(os.path.join(folder_dir, f)):
                os.remove(os.path.join(folder_dir, f))
            shutil.copyfile(os.path.join(
                os.path.dirname(__file__, f)), os.path.join(
                folder_dir, f))

def potential_site_package_dirs():
    import sysconfig
    dirs = list(sysconfig.get_paths().values())
    output = subprocess.check_output([sys.executable,
        "-m", "site", "--user-site"])
    try:
        output = output.decode('utf-8', 'replace')
    except AttributeError:
        pass
    dirs = [dirpath for dirpath in output.split("\n") if \
        len(dirpath) > 0] + dirs
    return dirs    

def install():
    for dirpath in potential_site_package_dirs():
        p4a_path = os.path.join(dirpath, "python-for-android")
        if os.path.exists(p4a_path):
            print("Installing to python-for-android package: " + 
                str(p4a_path))
            copy_to_recipe_folder(os.path.join(p4a_path,
                "pythonforandroid", "recipes"))

if __name__ == "__main__":
    install()
