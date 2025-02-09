bl_info = {
    "name": "RE Hair Strands Import/Export ",
    "author": "TheLeonX",
    "version": (1, 1),
    "blender": (4, 2, 0),
    "location": "File > Import/Export",
    "description": "Import and Export hair strands files from Resident Evil 4 Remake.",
    "category": "Import-Export",
}

import bpy
import sys
from .blender import addon, importer, exporter
def cleanse_modules():
    for module_name in sorted(sys.modules.keys()):

        if module_name.startswith(__name__):
            del sys.modules[module_name]
def register():
    addon.register()
    importer.register()
    exporter.register()

def unregister():
    addon.unregister()
    importer.unregister()
    exporter.unregister()
    cleanse_modules()


if __name__ == "__main__":
    register()