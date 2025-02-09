import bpy
from .addon import SUPPORTED_EXPORT_FORMATS
import struct
import random
from time import time
import sys
import os
import mathutils
import math

def get_collections(self, context):
    items = [(col.name, col.name.replace('.strands', ''), f"Collection: {col.name}") 
             for col in bpy.data.collections if '.strands' in col.name]
    if not items:
        items.append(('NONE', "No Collections with .strands", "No collections with .strands found"))
    return items

def get_mesh_objects(self, context):
    items = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH']
    if not items:
        items.append(('NONE', "No Meshes", "No mesh objects found"))
    return items

def timed(func):
    def inner(*args, **kwargs):
        t0 = time()
        obj_name = bpy.data.objects[args[0]].name if args else 'Unknown Object'
        result = func(*args, **kwargs)
        elapsed = time() - t0
        print(f'Hair strand "{obj_name}" exported in {elapsed:.5f} seconds')
        return result
    return inner

def get_objects_in_collection(self, context):
    collection_name = self.targetCollection
    if collection_name == 'NONE':
        return [('NONE', "No strands", "No strands available")]
    collection = bpy.data.collections.get(collection_name)
    if collection:
        items = [(obj.name, obj.name, f"Strands: {obj.name}") for obj in collection.objects if 'CURVES' in obj.type]
        if not items:
            items.append(('NONE', "No LOD", "No LODs in this collection"))
        return items
    return [('NONE', "No LODs", "No LODs found")]

def get_width_average(input_collection):
    collection = bpy.data.collections.get(input_collection)
    return collection["Width Average"][0] if collection else 0.0

def get_width_max(input_collection):
    collection = bpy.data.collections.get(input_collection)
    return collection["Width Max"][0] if collection else 0.0

def get_width_min(input_collection):
    collection = bpy.data.collections.get(input_collection)
    return collection["Width Min"][0] if collection else 0.0

def convert_curves_to_curve(source_curves_name):
    source_curves = bpy.data.objects.get(source_curves_name)
    if not source_curves or source_curves.type != 'CURVES':
        print(f"Object '{source_curves_name}' is not a valid CURVES object.")
        return None
    bpy.context.view_layer.objects.active = source_curves
    source_curves.select_set(True)
    bpy.ops.object.convert(target='CURVE')
    print(f"Temporary CURVE object '{source_curves.name}' created.")
    return source_curves

@timed
def write_strands(curve_object, auto_radius, enable_physic, invert_roots):
    pos_data      = bytearray()
    curve_data    = bytearray()
    root_data     = bytearray()
    point_data    = bytearray()
    guide_data    = bytearray()
    hair_root_positions = []  # World-space hair root positions

    curve = bpy.data.objects.get(curve_object)
    global_point_id = 0

    if curve.type == 'CURVES':
        positions  = curve.data.attributes["position"].data
        curves     = curve.data.curves
        radius_atr = curve.data.attributes["radius"].data if "radius" in curve.data.attributes else None
        cumulative_points = 0

        for curve_idx, curve_item in enumerate(curves):
            start_idx = cumulative_points
            num_points = curve_item.points_length
            cumulative_points += num_points

            indices = list(range(start_idx, start_idx + num_points))
            if invert_roots:
                indices.reverse()

            # Transform raw position to world space.
            root_attr = positions[indices[0]].vector
            hair_root = curve.matrix_world @ root_attr
            hair_root_positions.append(hair_root)

            first_point_id = global_point_id
            if num_points < 2:
                continue

            for j, point_idx in enumerate(indices):
                pos = positions[point_idx].vector
                # Conversion: (x, z, -y)
                pos_tuple = (pos.x, pos.z, -pos.y)

                if auto_radius or not radius_atr:
                    radius = 0.00003 if (j == 0 or j == (num_points - 1)) else random.uniform(0.00011, 0.00015)
                else:
                    radius = float(radius_atr[point_idx].value)
                radius_clamped = min(max(int(radius * 105000), 0), 65535)
                curve_position = int((j / (num_points - 1)) * 255)
                pos_data.extend(struct.pack('<3f', *pos_tuple))
                pos_data.extend(struct.pack('<H', radius_clamped))
                pos_data.extend(struct.pack('<B', curve_position))
                pos_data.extend(struct.pack('<B', 0)) #somehow changes color of hair strands

                id_value = global_point_id
                if j == 0:
                    id_value += 0x10000000
                elif j == (num_points - 2):
                    id_value += 0x20000000
                if j != (num_points - 1):
                    curve_data.extend(struct.pack('<I', id_value))
                point_data.extend(struct.pack('<I', curve_idx))
                guide_data.extend(struct.pack('<H', curve_idx))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<H', j))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<h', -1))
                guide_data.extend(struct.pack('<e', 1 if enable_physic else 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                guide_data.extend(struct.pack('<e', 0))
                global_point_id += 1

            root_data.extend(struct.pack('<I', first_point_id))

    return pos_data, curve_data, root_data, point_data, guide_data, hair_root_positions

class ExportMyFormat(bpy.types.Operator):
    bl_idname  = "export_hair.strands"
    bl_label   = "Export Hair Strands"
    bl_options = {'PRESET'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    targetCollection: bpy.props.EnumProperty(
        name="",
        description="Collection with hair strands",
        items=get_collections,
        update=lambda self, context: update_objects(self, context)
    )
    
    target_HIGH_LOD_obj: bpy.props.EnumProperty(
        name="",
        description="HIGH LOD CURVES object",
        items=get_objects_in_collection
    )

    enable_HIGH_auto_radius: bpy.props.BoolProperty(
        name="Enable auto width",
        description="Export recommended radius for HIGH LOD hair strands"
    )
    target_LOW_LOD_obj: bpy.props.EnumProperty(
        name="",
        description="LOW LOD CURVES object",
        items=get_objects_in_collection
    )
    enable_LOW_auto_radius: bpy.props.BoolProperty(
        name="Enable auto width",
        description="Export recommended radius for LOW LOD hair strands"
    )

    enable_dynamics: bpy.props.BoolProperty(
        name="Enable hair physic",
        description="Enables hair physics per strand",
        default=True
    )

    enable_random_uv_map: bpy.props.BoolProperty(
        name="Random UV Map",
        description="Randomize UV coordinates per strand (otherwise use attribute data)"
    )

    invert_roots: bpy.props.BoolProperty(
        name="Invert roots",
        description="Export positions in reverse order",
        default=False
    )

    width_average_prop: bpy.props.FloatProperty(
        name="Width Average",
        description="Average width value",
        default=0.0
    )
    width_max_prop: bpy.props.FloatProperty(
        name="Width Max",
        description="Maximum width value",
        default=0.0
    )
    width_min_prop: bpy.props.FloatProperty(
        name="Width Min",
        description="Minimum width value",
        default=0.0
    )

    create_sbd_file: bpy.props.BoolProperty(
        name="Create .sbd file",
        description="Generate .sbd file for hair rigging",
        default=True
    )

    def execute(self, context):
        if self.targetCollection == 'NONE':
            self.report({'ERROR'}, "No collection selected for export.")
            return {'CANCELLED'}
        collection = bpy.data.collections.get(self.targetCollection)
        High_obj = bpy.data.objects.get(self.target_HIGH_LOD_obj)
        uv_map_vectors = []
        if "surface_uv_coordinate" in High_obj.data.attributes:
            uv_map_vectors = High_obj.data.attributes["surface_uv_coordinate"].data
        else:
            self.enable_random_uv_map = True
            print("No UV attribute")
        if collection:
            export_file = bytearray()

            (pos_HIGH, curve_HIGH, root_HIGH,
             point_HIGH, guide_HIGH, hair_roots) = write_strands(
                self.target_HIGH_LOD_obj,
                self.enable_HIGH_auto_radius,
                self.enable_dynamics,
                self.invert_roots)
            (pos_LOW, curve_LOW, root_LOW,
             point_LOW, guide_LOW, _) = write_strands(
                self.target_LOW_LOD_obj,
                self.enable_LOW_auto_radius,
                self.enable_dynamics,
                self.invert_roots)
            
            UV_map_data = bytearray()
            for entry in range(int(len(root_HIGH)/4)):
                if self.enable_random_uv_map:
                    uv_map = [random.uniform(0.0, 1.0), random.uniform(0.0, 1.0)]
                else:
                    uv_map = [uv_map_vectors[entry].vector[0], uv_map_vectors[entry].vector[1]]
                UV_map_data.extend(struct.pack('ff', uv_map[0], uv_map[1]))

            export_file.extend(struct.pack('4s8x', 'STRD'.encode('utf-8')))
            export_file.extend(struct.pack('I', int(len(curve_HIGH)/4)))
            export_file.extend(struct.pack('I8x', int(len(curve_LOW)/4)))
            export_file.extend(struct.pack('I', int(len(pos_HIGH))))
            export_file.extend(struct.pack('I8x', int(len(pos_LOW))))
            export_file.extend(struct.pack('I', int(len(curve_HIGH))))
            export_file.extend(struct.pack('I8x', int(len(curve_LOW))))
            export_file.extend(struct.pack('I', int(len(root_HIGH))))
            export_file.extend(struct.pack('I8x', int(len(root_LOW))))
            export_file.extend(struct.pack('I', int(len(point_HIGH))))
            export_file.extend(struct.pack('I8x', int(len(point_LOW))))
            export_file.extend(struct.pack('I', int(len(curve_HIGH)/0x10)))
            export_file.extend(struct.pack('I', int(len(curve_LOW)/0x10)))
            export_file.extend(struct.pack('I', int(len(UV_map_data))))
            export_file.extend(struct.pack('I', int(len(root_HIGH)/0x4)))
            export_file.extend(struct.pack('3f', collection['Bounding Box Max'][0],
                                           collection['Bounding Box Max'][2],
                                           -collection['Bounding Box Max'][1]))
            export_file.extend(struct.pack('3f8x', collection['Bounding Box Min'][0],
                                           collection['Bounding Box Min'][2],
                                           -collection['Bounding Box Min'][1]))
            export_file.extend(struct.pack('I', int(len(guide_HIGH))))
            export_file.extend(struct.pack('I28x', int(len(guide_LOW))))
            export_file.extend(struct.pack('f', self.width_average_prop))
            export_file.extend(struct.pack('f', self.width_max_prop))
            export_file.extend(struct.pack('f', self.width_min_prop))

            export_file += pos_HIGH + curve_HIGH + root_HIGH + point_HIGH + guide_HIGH
            export_file += pos_LOW + curve_LOW + root_LOW + point_LOW + guide_LOW
            export_file += UV_map_data
            
            with open(self.filepath, 'wb') as f:
                f.write(export_file)
            self.report({'INFO'}, f"Exporting hair strands: {collection.name}")

            if self.create_sbd_file:
                # Use surface mesh from High LOD curves: object.data.surface
                surface_obj = getattr(High_obj.data, "surface", None)
                if not surface_obj:
                    self.report({'ERROR'}, "Surface mesh not selected. Please select a surface mesh in the Data tab for curves.")
                    return {'CANCELLED'}
                sbd_file = bytearray()
                sbd_file.extend(struct.pack('4s4x', 'SDBD'.encode('utf-8')))
                num_entries = len(hair_roots)
                sbd_file.extend(struct.pack('I', num_entries * 20))
                
                depsgraph = context.evaluated_depsgraph_get()
                surface_eval = surface_obj.evaluated_get(depsgraph)
                mesh = surface_eval.to_mesh()

                num_verts = len(mesh.vertices)
                kd_vert = mathutils.kdtree.KDTree(num_verts)
                for i, v in enumerate(mesh.vertices):
                    co_world = v.co
                    kd_vert.insert(co_world, i)
                kd_vert.balance()

                # Build a KD‑tree for face centers.
                num_faces = len(mesh.polygons)
                kd_face = mathutils.kdtree.KDTree(num_faces)
                for poly in mesh.polygons:
                    kd_face.insert(poly.center, poly.index)
                kd_face.balance()

                vertex_uv = {}
                if mesh.uv_layers.active:
                    uv_layer = mesh.uv_layers.active.data
                    uv_dict = {i: [] for i in range(num_verts)}
                    for loop in mesh.loops:
                        uv_dict[loop.vertex_index].append(uv_layer[loop.index].uv[:])
                    for idx, uv_list in uv_dict.items():
                        if uv_list:
                            avg_u = sum(uv[0] for uv in uv_list) / len(uv_list)
                            avg_v = sum(uv[1] for uv in uv_list) / len(uv_list)
                            vertex_uv[idx] = (avg_u, avg_v)
                        else:
                            vertex_uv[idx] = (0.0, 0.0)
                else:
                    for i in range(num_verts):
                        vertex_uv[i] = (0.0, 0.0)

                # For each hair root, find the closest face using the face KD‑tree.
                for root in hair_roots:
                    co, face_index, dist = kd_face.find(root)
                    poly = mesh.polygons[face_index]
                    if poly and len(poly.vertices) >= 3:
                        verts = list(poly.vertices)[:3]
                        verts_multiplied = [int(idx * 12) for idx in verts]
                        uvs = [vertex_uv.get(idx, (0.0, 0.0)) for idx in verts]
                        avg_u = sum(uv[0] for uv in uvs) / 3.0
                        avg_v = sum(uv[1] for uv in uvs) / 3.0
                        sbd_file.extend(struct.pack("<3I2f",
                                                    verts_multiplied[0],
                                                    verts_multiplied[1],
                                                    verts_multiplied[2],
                                                    avg_u, avg_v))
                    else:
                        sbd_file.extend(struct.pack("<3I2f",
                                                    0,
                                                    0,
                                                    0,
                                                    -1, -1))

                sbd_filepath = self.filepath.replace('_strand.strands.20', '.sbd.7')
                with open(sbd_filepath, 'wb') as sbd:
                    sbd.write(sbd_file)
                surface_eval.to_mesh_clear()

            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Collection not found.")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = os.path.join(bpy.path.abspath("//"), self.targetCollection + ".20")
        if self.targetCollection != 'NONE':
            self.width_min_prop = float(get_width_min(self.targetCollection))
            self.width_max_prop = float(get_width_max(self.targetCollection))
            self.width_average_prop = float(get_width_average(self.targetCollection))
            coll = bpy.data.collections.get(self.targetCollection)
            if len(coll.objects) > 1:
                self.target_LOW_LOD_obj = coll.objects[1].name
        else:
            self.width_min_prop = 0.000225486015551724
            self.width_max_prop = 0.000280199252301827
            self.width_average_prop = 0.000005102024806546
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Target Collection:")
        layout.prop(self, "targetCollection", icon="COLLECTION_COLOR_06")
        layout.prop(self, "enable_dynamics")
        layout.prop(self, "enable_random_uv_map")
        layout.prop(self, "create_sbd_file")
        layout.prop(self, "invert_roots")
        layout.label(text="Width Settings:")
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
        # Removed surface mesh combo box; now using High LOD curves' data.surface.

def update_objects(self, context):
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
