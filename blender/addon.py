# Common attributes and formats for import/export
import bpy
import sys

SUPPORTED_IMPORT_FORMATS = [("20", "Hair Strands (.strands.20)", "Hair Strands RE4R Format")]
SUPPORTED_EXPORT_FORMATS = [("20", "Hair Strands (.strands.20)", "Hair Strands RE4R Format")]

# Example shared properties
class AddonProperties(bpy.types.PropertyGroup):
    some_custom_property: bpy.props.StringProperty(
        name="Custom Property",
        description="A property shared across tools",
        default="Default Value"
    )

def cleanse_modules():
    for module_name in sorted(sys.modules.keys()):

        if module_name.startswith(__name__):
            del sys.modules[module_name]

def register():
    bpy.utils.register_class(AddonProperties)
    bpy.types.Scene.my_addon_props = bpy.props.PointerProperty(type=AddonProperties)

def unregister():
    bpy.utils.unregister_class(AddonProperties)
    del bpy.types.Scene.my_addon_props
    cleanse_modules()
