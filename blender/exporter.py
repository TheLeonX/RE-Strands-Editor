import bpy
from .addon import SUPPORTED_EXPORT_FORMATS
import struct
import random
from time import time
import sys
import os
def get_collections(self, context):
    """Get a list of collections in the scene that contain '.strands' in their name, and remove '.strands' from the display name."""
    items = [(col.name, col.name.replace('.strands', ''), f"Collection: {col.name}") 
             for col in bpy.data.collections if '.strands' in col.name]
    if not items:
        items.append(('NONE', "No Collections with .strands", "No collections with .strands found"))
    return items

# For debug purposes
def timed(func):
    def inner(*args, **kwargs):
        t0 = time()
         # Extract object name if possible
        obj_name = bpy.data.objects[args[0]].name if args else 'Unknown Object'
        result = func(*args, **kwargs)
        elapsed = time() - t0
        print(f'Hair strand "{obj_name}" exported in {elapsed:.5f} seconds')

        return result

    return inner

def get_objects_in_collection(self, context):
    """Get a list of objects in the selected collection."""
    collection_name = self.targetCollection
    if collection_name == 'NONE':
        return [('NONE', "No strands", "No strands available")]
    
    collection = bpy.data.collections.get(collection_name)
    if collection:
        # Get all objects in the collection
        items = [(obj.name, obj.name, f"Strands: {obj.name}") for obj in collection.objects if 'CURVES' in obj.type]
        if not items:
            items.append(('NONE', "No LOD", "No LODs in this collection"))
        return items
    return [('NONE', "No LODs", "No LODs found")]

def get_width_average(input_collection):
    """Get a list of objects in the selected collection."""
    collection_name = input_collection
    if collection_name == 'NONE':
        return [('NONE', "No strands", "No strands available")]
    
    collection = bpy.data.collections.get(collection_name)
    if collection:
        return collection["Width Average"][0]
    
    return [('NONE', "No strands", "No strands available")]

def get_width_max(input_collection):
    """Get a list of objects in the selected collection."""
    collection_name = input_collection
    if collection_name == 'NONE':
        return [('NONE', "No strands", "No strands available")]
    
    collection = bpy.data.collections.get(collection_name)
    if collection:
        return collection["Width Max"][0]
    
    return [('NONE', "No strands", "No strands available")]

def get_width_min(input_collection):
    """Get a list of objects in the selected collection."""
    collection_name = input_collection
    if collection_name == 'NONE':
        return [('NONE', "No strands", "No strands available")]
    
    collection = bpy.data.collections.get(collection_name)
    if collection:
        return collection["Width Min"][0]
    
    return [('NONE', "No strands", "No strands available")]

def convert_curves_to_curve(source_curves_name):
    # Get the source CURVES object
    source_curves = bpy.data.objects.get(source_curves_name)
    if not source_curves or source_curves.type != 'CURVES':
        print(f"Object '{source_curves_name}' is not a valid CURVES object.")
        return None

    # Create a new CURVE object
    bpy.context.view_layer.objects.active = source_curves
    source_curves.select_set(True)
    bpy.ops.object.convert(target='CURVE')

    print(f"Temporary CURVE object '{source_curves.name}' created.")
    return source_curves


@timed
def write_strands(curve_object, auto_radius, enable_physic):
    # Prepare binary data
    pos_data = bytearray()
    curve_data = bytearray()
    root_data = bytearray()
    point_data = bytearray()
    guide_data = bytearray()

    curve = bpy.data.objects.get(curve_object)
    curve_id = 0
    global_point_id = 0  # Initialize global ID for points

    if curve.type == 'CURVES':  # Check for 'CURVES' type
        points = curve.data.points
        curves = curve.data.curves
        positions = curve.data.attributes["position"].data
        radius_atr= []
        if "radius" in curve.data.attributes:
            radius_atr = curve.data.attributes["radius"]

        cumulative_points = 0  # Track the starting index for each curve

        for curve_idx, curve_item in enumerate(curves):
            start_idx = cumulative_points
            num_points = curve_item.points_length
            end_idx = start_idx + num_points
            cumulative_points += num_points

            first_point_id = global_point_id  # Save the global ID of the first point in the curve

            if num_points < 2:
                continue  # Skip curves with fewer than 2 points

            for point_idx in range(start_idx, end_idx):
                position = positions[point_idx].vector  # Access the position

                # Convert Blender positions to x, y, z
                position = (position.x, position.z, -position.y)

                # Calculate radius
                if auto_radius or "radius" not in curve.data.attributes:
                    if point_idx == start_idx or point_idx == end_idx - 1:
                        radius = 0.00003  # Fixed radius for root and end
                    else:
                        radius = random.uniform(0.00011, 0.00015)  # Random radius for other points
                else:
                    radius = float(radius_atr.data[point_idx].value)  # Use radius from the `points` collection

                radius_clamped = min(max(int(radius * 105000), 0), 65535)  # Clamp radius to uint16 range

                # Calculate stretched position along the curve length, scaled to 0-255
                curve_position = int(((point_idx - start_idx) / (num_points - 1)) * 255)  # Linear interpolation
                curve_position_clamped = min(max(curve_position, 0), 255)

                # Export position, radius, and curve position
                pos_data.extend(struct.pack('<3f', *position))  # Write 3 floats
                pos_data.extend(struct.pack('<H', radius_clamped))  # Write radius as uint16
                pos_data.extend(struct.pack('<B', curve_position_clamped))  # Write curve position as uint8
                pos_data.extend(struct.pack('<B', curve_idx % 256))  # Write curve ID as uint8

                # Determine start, end, or middle
                id_value = global_point_id
                if point_idx == start_idx:
                    id_value += 0x10000000  # Start point
                elif point_idx == end_idx - 2:  # Point before the last
                    id_value += 0x20000000  # Before end point

                # Export ID to curve_data (skip the last point)
                if point_idx != end_idx - 1:
                    curve_data.extend(struct.pack('<I', id_value))

                # Export curve ID to point_data
                point_data.extend(struct.pack('<I', curve_idx))

                # Export additional data to guide_data
                guide_data.extend(struct.pack('<H', curve_idx))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<H', point_idx - start_idx))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<h', -1))
                if enable_physic:
                    guide_data.extend(struct.pack('<e', 1))
                else:
                    guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))

                global_point_id += 1  # Increment global ID for each point

            # Add the first point's global ID to root_data
            root_data.extend(struct.pack('<I', first_point_id))

            curve_id += 1

    return pos_data, curve_data, root_data, point_data, guide_data


class ExportMyFormat(bpy.types.Operator):
    bl_idname = "export_hair.strands"
    bl_label = "Export Hair Strands"
    bl_options = {'PRESET'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    targetCollection: bpy.props.EnumProperty(
        name="",
        description="Set the collection containing the meshes to be exported",
        items=get_collections,
        update=lambda self, context: update_objects(self, context)
    )
    
    target_HIGH_LOD_obj: bpy.props.EnumProperty(
        name="",
        description="HIGH LOD Mesh",
        items=get_objects_in_collection
    )

    enable_HIGH_auto_radius: bpy.props.BoolProperty(
        name="Enable auto width",
        description="Will export recommended radius for HIGH LOD hair strands"

    )
    target_LOW_LOD_obj: bpy.props.EnumProperty(
        name="",
        description="LOW LOD Mesh",
        items=get_objects_in_collection
    )
    enable_LOW_auto_radius: bpy.props.BoolProperty(
        name="Enable auto width",
        description="Will export recommended radius for LOW LOD hair strands"
    )

    enable_dynamics: bpy.props.BoolProperty(
        name="Enable hair physic",
        description="Enables hair physic for each strand individually",
        default=True
    )

    enable_random_uv_map: bpy.props.BoolProperty(
        name="Random UV Map",
        description="Enables random UV map for each hair strand. Otherwise all values will be set to 0."
    )

    width_average_prop: bpy.props.FloatProperty(
        name="Width Average",
        description="Changes average Width value for all hair strands",
        default=0.0
    )
    width_max_prop: bpy.props.FloatProperty(
        name="Width Max",
        description="Changes average Width value for all hair strands",
        default=0.0
    )
    width_min_prop: bpy.props.FloatProperty(
        name="Width Min",
        description="Changes average Width value for all hair strands",
        default=0.0
    )

    create_sbd_file: bpy.props.BoolProperty(
        name="Create .sbd file",
        description="This file used for hair rigging. Might have issues cuz its WIP",
        default=True
    )
    def execute(self, context):
        if self.targetCollection == 'NONE':
            self.report({'ERROR'}, "No collection selected for export.")
            return {'CANCELLED'}
        # Export logic here, use the selected collection
        collection = bpy.data.collections.get(self.targetCollection)
        High_lod_curve = bpy.data.objects.get(self.target_HIGH_LOD_obj)
        uv_map_vectors = []
        if ("surface_uv_coordinate" in High_lod_curve.data.attributes):
            uv_map_vectors = High_lod_curve.data.attributes["surface_uv_coordinate"].data
        else:
            self.enable_random_uv_map = True
        if collection:
            export_file = bytearray()

            position_HIGH_data, curve_HIGH_data, root_HIGH_data, point_HIGH_data, guide_HIGH_data = write_strands(self.target_HIGH_LOD_obj, self.enable_HIGH_auto_radius, self.enable_dynamics)
            position_LOW_data, curve_LOW_data, root_LOW_data, point_LOW_data, guide_LOW_data = write_strands(self.target_LOW_LOD_obj, self.enable_LOW_auto_radius, self.enable_dynamics)
            
            UV_map_data = bytearray()
            uv_map_export = []
            for entry in range(int(len(root_HIGH_data)/4)):
                UV_map = [random.uniform(0.0, 1.0), random.uniform(0.0, 1.0)]

                if (self.enable_random_uv_map):
                    UV_map_data.extend(struct.pack('ff',UV_map[0],UV_map[1]))
                else:
                    UV_map_data.extend(struct.pack('ff',uv_map_vectors[entry].vector[0],uv_map_vectors[entry].vector[1]))

                uv_map_export.append(UV_map)

            export_file.extend(struct.pack('4s8x', 'STRD'.encode('utf-8'))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(curve_HIGH_data)/4)))
            export_file.extend(struct.pack('I8x', int(len(curve_LOW_data)/4))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(position_HIGH_data))))
            export_file.extend(struct.pack('I8x', int(len(position_LOW_data)))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(curve_HIGH_data))))
            export_file.extend(struct.pack('I8x', int(len(curve_LOW_data)))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(root_HIGH_data))))
            export_file.extend(struct.pack('I8x', int(len(root_LOW_data)))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(point_HIGH_data))))
            export_file.extend(struct.pack('I8x', int(len(point_LOW_data)))) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(curve_HIGH_data)/0x10)))
            export_file.extend(struct.pack('I', int(len(curve_LOW_data)/0x10)))
            export_file.extend(struct.pack('I', int(len(UV_map_data))))
            export_file.extend(struct.pack('I', int(len(root_HIGH_data)/0x4)))
            export_file.extend(struct.pack('3f', collection['Bounding Box Max'][0],collection['Bounding Box Max'][2],-collection['Bounding Box Max'][1]))
            export_file.extend(struct.pack('3f8x', collection['Bounding Box Min'][0],collection['Bounding Box Min'][2],-collection['Bounding Box Min'][1])) #skip 8 bytes
            export_file.extend(struct.pack('I', int(len(guide_HIGH_data))))
            export_file.extend(struct.pack('I28x', int(len(guide_LOW_data)))) #skip 28 bytes
            export_file.extend(struct.pack('f', self.width_average_prop))
            export_file.extend(struct.pack('f', self.width_max_prop))
            export_file.extend(struct.pack('f', self.width_min_prop))

            export_file+=position_HIGH_data+curve_HIGH_data+root_HIGH_data+point_HIGH_data+guide_HIGH_data
            export_file+=position_LOW_data+curve_LOW_data+root_LOW_data+point_LOW_data+guide_LOW_data
            export_file+=UV_map_data
            
            # Replace this with your actual export logic
            self.report({'INFO'}, f"Exporting hair strands: {collection.name}")
            with open(self.filepath, 'wb') as f:
                f.write(export_file)

            if self.create_sbd_file:
                sbd_file = bytearray()
                sbd_file.extend(struct.pack('4s4x', 'SDBD'.encode('utf-8'))) #skip 4 bytes
                sbd_file.extend(struct.pack('I', int(len(root_HIGH_data)/4) * 20))
                for entry in range(int(len(root_HIGH_data)/4)):
                    if self.enable_random_uv_map == False:
                        if (uv_map_vectors[entry].vector[0] != 0 and uv_map_vectors[entry].vector[1] != 0):
                            sbd_file.extend(struct.pack("3I2f", 156,204,228, uv_map_vectors[entry].vector[0],uv_map_vectors[entry].vector[1]))
                        else:
                            sbd_file.extend(struct.pack("3I2f", 156,204,228, uv_map_export[entry][0],uv_map_export[entry][1]))
                    else:
                            sbd_file.extend(struct.pack("3I2f", 156,204,228, uv_map_export[entry][0],uv_map_export[entry][1]))

                with open(self.filepath.replace('_strand.strands.20', '.sbd.7'), 'wb') as sbd:
                    sbd.write(sbd_file)
            
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Collection not found.")
            return {'CANCELLED'}



    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = os.path.join(
                bpy.path.abspath("//"), self.targetCollection+".20"
            )
        
        collection_name = self.targetCollection
        if collection_name and collection_name != 'NONE':
            self.width_min_prop = float(get_width_min(collection_name))
            self.width_max_prop = float(get_width_max(collection_name))
            self.width_average_prop = float(get_width_average(collection_name))
            collection = bpy.data.collections.get(collection_name)
            if len(collection.objects)>1:
                self.target_LOW_LOD_obj = collection.objects[1].name
        else:
            self.width_min_prop = 0.000225486015551724
            self.width_max_prop = 0.000280199252301827
            self.width_average_prop = 0.000005102024806546
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    def draw(self, context):
        layout = self.layout
        layout.label(text = "Target Collection:")
        layout.prop(self, "targetCollection", icon="COLLECTION_COLOR_06")
        layout.prop(self, "enable_dynamics")
        layout.prop(self, "enable_random_uv_map")
        layout.prop(self, "create_sbd_file")
        layout.label(text = "Width Settings:")
        layout.prop(self, "width_average_prop", text="Average")
        row = layout.row()
        row.prop(self, "width_min_prop", text="Min")
        row.prop(self, "width_max_prop", text="Max")
        layout.label(text="Target High LOD Strands:")
        layout.prop(self, "target_HIGH_LOD_obj", icon="CURVES")
        layout.prop(self, "enable_HIGH_auto_radius")
        layout.label(text="Target Low LOD Strands:")
        layout.prop(self, "target_LOW_LOD_obj", icon="CURVES")
        layout.prop(self, "enable_LOW_auto_radius")

def update_objects(self, context):
    """Update the objects list when a different collection is selected."""
    # Redraw the panel to update the objects dropdown
    self.width_min_prop = float(get_width_min(self.targetCollection))
    self.width_max_prop = float(get_width_max(self.targetCollection))
    self.width_average_prop = float(get_width_average(self.targetCollection))
    context.area.tag_redraw()

def cleanse_modules():
    for module_name in sorted(sys.modules.keys()):

        if module_name.startswith(__name__):
            del sys.modules[module_name]
            
def menu_func_export(self, context):
    self.layout.operator(ExportMyFormat.bl_idname, text="RE Strands (.strands.20)")

def register():
    bpy.utils.register_class(ExportMyFormat)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportMyFormat)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    cleanse_modules()
