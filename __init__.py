# ***** BEGIN GPL LICENSE BLOCK *****

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

# ***** END GPL LICENCE BLOCK *****

'''
This script is an importer and exporter for the Kingpin Model md2 and mdx.

The frames are named <frameName><N> with :<br>
 - <N> the frame number<br>
 - <frameName> the name choosen at the last marker
                (or 'frame' if the last marker has no name or if there is no last marker)

Skins are set using image textures in materials, if it is longer than 63 characters it is truncated.

Thanks to:
    DarkRain
    Bob Holcomb. for MD2_NORMALS taken from his exporter.
    David Henry. for the documentation about the MD2 file format.
    Bob Holcomb
    Sebastian Lieberknecht
    Dao Nguyen
    Bernd Meyer
    Damien Thebault
    Erwan Mathieu
    Takehiko Nawata


hypov8 log
==========
v1.1.1 (blender 2.79)
- fix teture bug
- added importing of GL commands. for enhanced uv pricision
- added skin search path for texcture not im nodel folder
- added multi part player model bbox fix. all parts must be visable in sceen
- fixed texture issue in glCommands. not checking for uv match, just vertex id

v1.2.0 (blender 2.80) jan 2020
- updated to work with new blender
- merged md2/mdx into 1 script
- loading/saving allows selection of both file types
- option for imported models to set timeline range if animated
- multi model selection support for exports
- hitbox will be created for each selected object

v1.2.1 (blender 2.80) nov 2020
- fixed a texture missing bug
- fixed texture string formatting
- export no longer fails if a skin was not found
- fixed skin string issue being null
- added matrix for non shape key exports


notes:
- setup model textures by adding using node and add an image for diffuse->color


todo:
- import. split model into mdx groups

'''


bl_info = {
    "name": "Kingpin Models (md2, mdx)",
    "description": "Importer and exporter for Kingpin file format (md2/mdx)",
    "author": "Update by Hypov8. See .py for prev authors",
    "version": (1, 2, 1),
    "blender": (2, 80, 0),
    "location": "File > Import/Export > Kingpin Models",
    "warning": "",  # used for warning icon and text in addons panel
    "wiki_url": "https://kingpin.info/",
    "tracker_url": "https://hypov8.kingpin.info",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}


if "bpy" in locals():
    import importlib
    if "import_kp" in locals():
        importlib.reload(import_kp)
    if "export_kp" in locals():
        importlib.reload(export_kp)


import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
    IntProperty,
)
from bpy.types import Operator  # B2.8
from bpy_extras.io_utils import ExportHelper, ImportHelper  # , unpack_list, unpack_face_list


class Import_MD2(bpy.types.Operator, ImportHelper):  # B2.8
    # class Import_MD2(bpy.types.Operator, ImportHelper): #B2.79
    '''Import Kingpin format file (md2/mdx)'''
    bl_idname = "import_kingpin.mdx"
    bl_label = "Import Kingpin model (md2/mdx)"
    # bl_options = {'', ''} #B2.8

    filename_ext = ".mdx"  # 2.8
    fImportAnimation: BoolProperty(
        name="Import animation",
        description="Import all frames",
        default=True,
    )
    fAddTimeline: BoolProperty(
        name="Import animation names",
        description="Import animation frame names to time line\n" +
        "WARNING: Removes all existing marker frame names",
        default=False,
    )

    filter_glob: StringProperty(  # 2.8
        default="*.md2;*.mdx",
        options={'HIDDEN'},
    )

    def execute(self, context):
        from . import import_kp

        # deselect any objects
        if bpy.ops.object.mode_set.poll():  # B2.8
            bpy.ops.object.mode_set(mode='OBJECT')  # B2.8
        if bpy.ops.object.select_all.poll():  # B2.8
            bpy.ops.object.select_all(action='DESELECT')  # B2.8

        keywords = self.as_keywords(ignore=(
            "filter_glob",
        ))
        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)  # TODO..

        if not import_kp.load(self, **keywords):
            return {'FINISHED'}

        bpy.context.view_layer.update()
        self.report({'INFO'}, "File '%s' imported" % self.filepath)
        return {'FINISHED'}

    def draw(self, context):  # 2.8
        layout = self.layout
        layout.prop(self, "fImportAnimation")
        sub = layout.column()
        sub.enabled = self.fImportAnimation
        sub.prop(self, "fAddTimeline", )


class Export_MD2(bpy.types.Operator, ExportHelper):  # B2.8
    # from . import export_kp
    # class Export_MD2(bpy.types.Operator, ExportHelper):  #B2.79
    '''Export selection to Kingpin file format (md2/md2)'''
    bl_idname = "export_kingpin.mdx"
    bl_label = "Export Kingpin Model (md2, mdx)"
    filename_ext = ".md2"  # md2 used later

    filter_glob: StringProperty(
        default="*.md2;*.mdx",
        options={'HIDDEN'},
    )
    fExportAnimation: BoolProperty(
        name="Export animation",
        description="Export all animation frames.\n" +
                    "Timeline range will be used",
        default=False,
    )
    fAnimationTimeline: BoolProperty(
        name="Use Timeline",
        description="Timeline range will be used",
        default=False,
    )
    fIsPlayerModel: BoolProperty(
        name="Player model seam fix",  # hypov8
        description="Use all visible sceen object to create bounding box size.\n" +
                    "This fixes seam algment issues in player models\n" +
                    "Show head, body, legs. Then export each selected part individually",
        default=False
    )
    eTextureNameMethod: EnumProperty(
        name="Skin",
        description="Skin naming method",
        items=(
            ('SHADENAME',
                "Material Name",
                "Use material name for skin.\n" +
                "Must include the file extension\n" +
                "eg.. models/props/test.tga\n" +
                "Image dimensions are sourced from nodes. 256 is use if no image exists"
             ),
            ('DATANAME',
             "Image Name",
                "Use image name from Material nodes\n" +
                "Must include the file extension\n" +
                "\"material name\" will be used if no valid textures are found\n" +
                "Image dimensions are sourced from nodes. 256 is use if no image exists"
             ),
            ('DATAPATH',
             "Image Path",
                "Use image path name from Material nodes\n" +
                "Path must contain a folder models/ or players/ or textures/ \n" +
                "\"material name\" will be used if no valid textures are found\n" +
                "Image dimensions are sourced from nodes. 256 is use if no image exists"
             ),

        ),
        default='SHADENAME',
    )
    fUseSharedBoundingBox: BoolProperty(
        name="Use shared bounding box across frames",
        description="Calculate a shared bounding box from all frames " +
                    "(used to avoid wobbling in static vertices but wastes resolution)",
        default=False,
    )
    fMergeHitbox: BoolProperty(
        name="Combine HitBox",
        description="When multiple objects are selected for export, a hitbox is created for each segment.\n" +
                    "This option combines them into single object and creates 1 large hitbox.\n" +
                    "These are used in multiplayer with \"dm_locational_damage 1\" set on server",
        default=False,
    )

    fStartFrame: IntProperty(
        name="Start Frame",
        description="Animated model start frame",
        min=0,
        max=1024,
        default=0,
    )
    fEndFrame: IntProperty(
        name="End Frame",
        description="Animated model end frame",
        min=0,
        max=1024,
        default=40,
    )

    check_extension = False  # 2.8 allow typing md2/mdx

    def __init__(self):
        self.properties.fStartFrame = bpy.context.scene.frame_start
        self.properties.fEndFrame = bpy.context.scene.frame_end

    def execute(self, context):
        from .export_kp import Export_MD2_fn
        print("__execute__")

        # store all selected objects
        # self.objects = context.selected_objects  # selected_editable_objects

        # duplicate the selected object
        # bpy.ops.object.duplicate()

        # the duplicated object is automatically selected
        self.objects = context.selected_objects

        # goto object mode
        if bpy.ops.object.mode_set.poll():  # B2.8
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)  # B2.8
        if bpy.ops.object.select_all.poll():  # B2.8
            bpy.ops.object.select_all(action='DESELECT')

        keywords = self.as_keywords(ignore=(
            "filter_glob",
            'check_existing',
            'fExportAnimation',
            'fIsPlayerModel',
            'fUseSharedBoundingBox',
            'fMergeHitbox',
            'eTextureNameMethod',
            'fStartFrame',
            'fEndFrame',
            'fAnimationTimeline',
        ))

        Export_MD2_fn(self, **keywords)

        # select inital objects
        for obj in self.objects:
            obj.select_set(state=True)  # 2.8

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "fExportAnimation")
        layout.prop(self, "fIsPlayerModel")
        sub = layout.column()
        sub.enabled = self.fExportAnimation
        sub.prop(self, "fStartFrame", )
        sub.prop(self, "fEndFrame")
        layout.prop(self, "eTextureNameMethod")
        layout.prop(self, "fMergeHitbox")
        layout.prop(self, "fUseSharedBoundingBox")

    def invoke(self, context, event):
        print("__invoke__")
        if not context.selected_objects:
            self.report({'ERROR'}, "Please, select an object to export!")
            return {'CANCELLED'}

        # if len(bpy.context.selected_objects) > 1:
        #     self.report({'ERROR'}, "Please, select exactly one object to export!")
        #     return {'CANCELLED'}

        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


#
# blender UI
def menu_func_export(self, context):
    self.layout.operator(Export_MD2.bl_idname, text="Kingpin Models (md2, mdx)")


def menu_func_import(self, context):
    self.layout.operator(Import_MD2.bl_idname, text="Kingpin Models (md2, mdx)")


def register():
    bpy.utils.register_class(Export_MD2)  # B2.8
    bpy.utils.register_class(Import_MD2)  # B2.8
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)  # B2.8
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)  # B2.8


def unregister():
    bpy.utils.unregister_class(Export_MD2)  # B2.8
    bpy.utils.unregister_class(Import_MD2)  # B2.8
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)  # B2.8
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)  # B2.8


if __name__ == "__main__":
    register()
