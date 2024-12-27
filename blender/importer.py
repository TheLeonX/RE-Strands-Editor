import bpy
from .addon import SUPPORTED_IMPORT_FORMATS

import struct
import os
import bpy
import sys
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from mathutils import Matrix, Vector, Euler, Quaternion
import math
from typing import Tuple, List

def create_collection(bb_max, bb_min, width_avg, width_max, width_min, name="NewCollection"):
    # Check if collection already exists, otherwise create a new one
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    print(f"Created new collection: {name}")
    
    # Assign color to the collection (works in viewport for Blender 3.x)
    collection.color_tag = 'COLOR_06'
    
    collection["Bounding Box Max"] = Vector([bb_max[0],-bb_max[2],bb_max[1]])
    collection["Bounding Box Min"] = Vector([bb_min[0],-bb_min[2],bb_min[1]])
    collection["Width Average"] = width_avg
    collection["Width Max"] = width_max
    collection["Width Min"] = width_min
    return collection

def add_object_to_collection(collection, object):
    # Get the collection
    if not collection:
        raise ValueError(f"Collection '{collection.name}' does not exist!")
    
    # Add objects to the collection
    if object.name not in collection.objects:
        for col in object.users_collection:
            col.objects.unlink(object)

        collection.objects.link(object)
        print(f"Added object '{object.name}' to collection '{collection.name}'")
    else:
        print(f"Object '{object.name}' is already in collection '{collection.name}'")


# Helper functions to parse binary data
def parse_positions(bin_data):
    positions = []
    entry_size = 16
    for i in range(0, len(bin_data), entry_size):
        data = bin_data[i:i + entry_size]
        if len(data) < entry_size:
            break
        x, y, z, attr1, _ = struct.unpack("fffHH", data)
        radius = attr1 / 100000.0
        positions.append((x, -z, y, radius))
    return positions

def parse_curve_data(bin_data):
    curve_entries = []
    entry_size = 4
    for i in range(0, len(bin_data), entry_size):
        data = bin_data[i:i + entry_size]
        if len(data) < entry_size:
            break
        raw_value = struct.unpack("I", data)[0]
        point_id = raw_value & 0x0FFFFFFF
        flag = (raw_value >> 28) & 0xF
        curve_entries.append((point_id, flag))
    return curve_entries

def parse_guiding_data(bin_data):
    guiding_entries = []
    entry_size = 24  # Each entry is 24 bytes
    for i in range(0, len(bin_data), entry_size):
        data = bin_data[i:i + entry_size]
        if len(data) < entry_size:
            break

        # Unpack the entry
        main_curve_idx, second_curve_idx, third_curve_idx, \
        main_point_idx, second_point_idx, third_point_idx, \
        weight_main, weight_second, weight_third, \
        bouncy1, bouncy2, bouncy3 = struct.unpack("HHHHHHeeeeee", data)

        guiding_entries.append({
            "main_curve_idx": main_curve_idx,
            "second_curve_idx": second_curve_idx,
            "third_curve_idx": third_curve_idx,
            "main_point_idx": main_point_idx,
            "second_point_idx": second_point_idx,
            "third_point_idx": third_point_idx,
            "weight_main": weight_main,
            "weight_second": weight_second,
            "weight_third": weight_third,
            "bouncy": (bouncy1, bouncy2, bouncy3)
        })

    return guiding_entries

def parse_uv_map_data(bin_data):
    uv_map = []
    entry_size = 8
    for i in range(0, len(bin_data), entry_size):
        data = bin_data[i:i + entry_size]
        if len(data) < entry_size:
            break
        U,V = struct.unpack("ff", data)
        uv_map.append((U, V))
    return uv_map

def create_curves_object(name,file_path, positions, curve_data, guiding_data, surface_uv_map):

    # Check if the object with the same name exists and delete it if necessary
    '''existing_obj = bpy.data.objects.get(name)
    if existing_obj:
        bpy.data.objects.remove(existing_obj, do_unlink=True)'''


    curve_data_block = bpy.data.curves.new(name=name, type="CURVE")
    curve_data_block.dimensions = '3D'
    current_points = []

    for index, flag in curve_data:
        x, y, z, radius = positions[index]
        if flag == 1:
            if current_points:
                add_spline_to_curve(curve_data_block, current_points)
            current_points = [(x, y, z, radius)]
        elif flag == 2:
            current_points.append((x, y, z, radius))
            x1, y1, z1, radius = positions[index+1]
            current_points.append((x1, y1, z1, radius))

            add_spline_to_curve(curve_data_block, current_points)
            current_points = []
        elif flag == 0:
            current_points.append((x, y, z, radius))

    if current_points:
        add_spline_to_curve(curve_data_block, current_points)
    
    object_name = os.path.basename(file_path).replace("_strand.strands.20", "")
    curve_obj = bpy.data.objects.new(name, curve_data_block)
    bpy.context.collection.objects.link(curve_obj)
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)
    bpy.ops.object.convert(target='CURVES')
    bpy.ops.geometry.attribute_add(name="surface_uv_coordinate", domain='CURVE', data_type='FLOAT2')
    curve_uv_map = curve_obj.data.attributes["surface_uv_coordinate"]

    for idx, curve in enumerate(curve_uv_map.data):
        curve.vector = surface_uv_map[idx]

    curve_obj.select_set(False)


    for collection in bpy.data.collections:
        if object_name in collection.name:
            for armature in collection.objects:
                if object_name+" Armature" in armature.name:
                    if armature.type == 'ARMATURE':
                        objects_with_armature_parent = [obj for obj in bpy.context.scene.objects if obj.parent == armature]
                        for obj in objects_with_armature_parent:
                            curve_obj.parent = obj
                            curve_obj.data.surface = obj
                            curve_obj.data.surface_uv_map = obj.data.uv_layers[0].name
    

    return curve_obj

def add_spline_to_curve(curve_data_block, points):
    spline = curve_data_block.splines.new(type='POLY')
    spline.points.add(len(points) - 1)
    for i, (x, y, z, radius) in enumerate(points):
        spline.points[i].co = (x, y, z, 1)
        spline.points[i].radius = radius

# Operator to load hair curves
class IMPORT_OT_hair_curves(bpy.types.Operator, ImportHelper):
    bl_idname = "import_hair.strands"
    bl_label = "Import Hair Strands"
    bl_options = {"UNDO"}

    filename_ext = ".strands.20"
    filter_glob: StringProperty(
        default="*.strands.20",
        options={"HIDDEN"},
        maxlen=255,
    )

    def execute(self, context):
        
        
        with open(self.filepath, "rb") as f:
            data = f.read()
            magic, = struct.unpack("4s", data[:4])
            print(2)
            if magic == b"STRD":
                pos_hq_offset = 188
                pos_hq_size = struct.unpack("I", data[28:32])[0]
                curve_hq_offset = pos_hq_offset + pos_hq_size
                curve_hq_size = struct.unpack("I", data[44:48])[0]
                guide_hq_offset = pos_hq_offset + pos_hq_size + curve_hq_size + struct.unpack("I", data[60:64])[0] + struct.unpack("I", data[76:80])[0]
                guide_hq_size = struct.unpack("I", data[140:144])[0]

                pos_lq_offset = guide_hq_offset + guide_hq_size
                pos_lq_size = struct.unpack("I", data[32:36])[0]
                curve_lq_offset = pos_lq_offset + pos_lq_size
                curve_lq_size = struct.unpack("I", data[48:52])[0]
                guide_lq_offset = pos_lq_offset + pos_lq_size + curve_lq_size + struct.unpack("I", data[64:68])[0] + struct.unpack("I", data[80:84])[0]
                guide_lq_size = struct.unpack("I", data[144:148])[0]

                uv_map_offset = guide_lq_offset + guide_lq_size
                uv_map_size = struct.unpack("I", data[100:104])[0]

                pos_hq = data[pos_hq_offset:pos_hq_offset + pos_hq_size]
                curve_hq = data[curve_hq_offset:curve_hq_offset + curve_hq_size]
                guiding_hq = data[guide_hq_offset:guide_hq_offset + guide_hq_size]
                pos_lq = data[pos_lq_offset:pos_lq_offset + pos_lq_size]
                curve_lq = data[curve_lq_offset:curve_lq_offset + curve_lq_size]
                guiding_lq = data[guide_lq_offset:guide_lq_offset + guide_lq_size]

                surface_uv_map = data[uv_map_offset:uv_map_offset + uv_map_size]

                bounding_box_vector_max = Vector(struct.unpack("3f", data[0x6C:0x78]))
                bounding_box_vector_min = Vector(struct.unpack("3f", data[0x78:0x84]))

                
                width_avg = struct.unpack("f", data[0xB0:0xB4])
                width_max = struct.unpack("f", data[0xB4:0xB8])
                width_min = struct.unpack("f", data[0xB8:0xBC])

                positions_HQ_LOD = parse_positions(pos_hq)
                curve_entries_HQ_LOD = parse_curve_data(curve_hq)
                guiding_HQ_LOD = parse_guiding_data(guiding_hq)
                positions_LQ_LOD = parse_positions(pos_lq)
                curve_entries_LQ_LOD = parse_curve_data(curve_lq)
                guiding_LQ_LOD = parse_guiding_data(guiding_lq)
                
                uv_map_data = parse_uv_map_data(surface_uv_map)
                
                object_name = os.path.basename(self.filepath).replace("_strand.strands.20", "")
                hq_obj = create_curves_object(object_name+"_" + "HIGH_LOD",self.filepath, positions_HQ_LOD, curve_entries_HQ_LOD, guiding_HQ_LOD, uv_map_data)
                lq_obj = create_curves_object(object_name+"_" + "LOW_LOD",self.filepath, positions_LQ_LOD, curve_entries_LQ_LOD, guiding_LQ_LOD, uv_map_data)
                collection_name = os.path.basename(self.filepath).replace(".20", "")
                strands_col = create_collection(bounding_box_vector_max, bounding_box_vector_min, width_avg, width_max, width_min, collection_name)
                add_object_to_collection(strands_col, hq_obj)
                add_object_to_collection(strands_col, lq_obj)

                self.report({"INFO"}, "Hair Strands imported successfully.")
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, "Failed to import strands: Not a valid strand file.")
                return {"CANCELLED"}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
# Register and unregister classes
classes = [
    IMPORT_OT_hair_curves,
]

def cleanse_modules():
    for module_name in sorted(sys.modules.keys()):

        if module_name.startswith(__name__):
            del sys.modules[module_name]

def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_hair_curves.bl_idname, text="Hair Strands (.strands.20)")

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    cleanse_modules()
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
