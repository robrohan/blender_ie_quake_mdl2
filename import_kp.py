'''
importer class/func

class KP_Util_Import

class Import_MD2(Operator, ImportHelper)

todo
import marker names from model

'''
import os
import bpy
import struct

from bpy.types import Operator  # B2.8
from bpy_extras.io_utils import ImportHelper, unpack_list
from bpy_extras.image_utils import load_image
from math import pi
from mathutils import Matrix

# import random
# import shutil


class Kingpin_Model_Reader:
    # def __init__(self, options):
    #     self.options = options
    #     self.object = None
    #     self.ident = 844121161
    #     self.version = 8
    #     print("test")
    #     return

    def makeObject(self):
        from bpy_extras import node_shader_utils
        print("Creating mesh", end='')
        int_frame = bpy.context.scene.frame_current
        bpy.context.scene.frame_set(0)

        #
        # 2.8 Create the mesh
        md2_mesh = bpy.data.meshes.new(self.name)
        md2_mesh.from_pydata(self.frames[0], [], self.tris)  # new 2.8 method
        print('.', end='')  # Finish mesh data

        #
        # 2.8 set uv data
        if self.numSkins > 0:
            uv_layer = md2_mesh.uv_layers.new(name=self.skins[0])  # 2.8
        else:
            uv_layer = md2_mesh.uv_layers.new(name="tris.tga")  # 2.8
        md2_mesh.uv_layers.active = uv_layer
        loops_uv = ()
        tri_idx = 0
        for face in md2_mesh.polygons:
            face.use_smooth = True
            uv_x = self.tris_uv[tri_idx]
            uvid = 0
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                uv_layer.data[loop_idx].uv = (self.uvs[uv_x[uvid]][0], self.uvs[uv_x[uvid]][1])
                uvid += 1
            tri_idx += 1
        print('.', end='')  # Finish uv data

        #
        # skins data
        if self.numSkins > 0:
            for skin in self.skins:
                # create a new material for each skin
                mat_id = bpy.data.materials.new(self.skins[0])  # hypov8 use mdx internal name
                # asign materal to mesh
                md2_mesh.materials.append(mat_id)

                # get materal node/links
                mat_id.use_nodes = True
                mat_nodes = mat_id.node_tree.nodes
                mat_links = mat_id.node_tree.links
                # delete existing node
                while(mat_nodes):
                    mat_nodes.remove(mat_nodes[0])

                # create diffuse texture nodes
                node_out = mat_nodes.new(type='ShaderNodeOutputMaterial')
                node_diff = mat_nodes.new(type='ShaderNodeBsdfDiffuse')
                node_tex = mat_nodes.new("ShaderNodeTexImage")

                # create links
                link_diff = mat_links.new(node_out.inputs['Surface'], node_diff.outputs['BSDF'])
                link_tex = mat_links.new(node_diff.inputs['Color'], node_tex.outputs['Color'])

                #
                # try to load tga/pcx image
                skinImg = loadImage(skin, self.filePath)  # KP_Util_Import
                if skinImg is None:
                    skinImg = bpy.data.images.new(skin, self.skinWidth, self.skinHeight)
                # skinImg. mapping = 'UV' #2.7
                skinImg.name = skin

                # link image to diffuse color
                node_tex.image = skinImg

                # skinTex = bpy.data.textures.new(skin, type='IMAGE')  # self.name + #hypov8 stop adding extra data
                # skinTex.image = skinImg
                # matTex = bpy.ops.texture.new()  # 2.7

            # assign materal to mesh
            # md2_mesh.materials.append(material)
        print('.', end='')  # Finish skin data

        # validate model
        md2_mesh.validate()
        md2_mesh.update()
        # scn_one = bpy.context.scene

        obj = bpy.data.objects.new(md2_mesh.name, md2_mesh)
        # base = bpy.context.scene.objects.link(obj)  # 2.7
        bpy.context.collection.objects.link(obj)  # 2.8
        # scn_one.objects.link(obj)  # 2.8
        # scn_one.collection.objects.link(obj)  # 2.8
        # bpy.context.scene.objects.active = obj  # 2.7
        # base.select = True
        obj.select_set(state=True)  # 2.8
        # obj.use_shape_key_edit_mode = True
        print("Done")

        # Animate
        if self.fImportAnimation and self.numFrames > 1:
            obj.use_shape_key_edit_mode = True
            if self.fAddTimeline:
                lastFName = ""
                bpy.data.scenes[0].timeline_markers.clear()

            for i in range(0, self.numFrames):
                progressStatus = i / self.numFrames * 100
                bpy.context.scene.frame_set(i)
                key = obj.shape_key_add(name=("frame_%i" % i), from_mix=False)
                # obj.data.vertices.foreach_set("co", unpack_list(self.frames[i]))
                key.data.foreach_set("co", unpack_list(self.frames[i]))
                # md2_mesh.transform(Matrix.Rotation(-pi / 2, 4, 'Z'))#2.7
                # set frame vertex data

                if self.fAddTimeline:  # import frame names
                    tmp_str = self.frame_names[i].rstrip(b'0123456789')
                    if lastFName != tmp_str:
                        bpy.data.scenes[0].timeline_markers.new(tmp_str.decode('utf-8'), frame=i)
                        lastFName = tmp_str

                if i > 0:
                    obj.data.shape_keys.key_blocks[i].value = 1.0
                    obj.data.shape_keys.key_blocks[i].keyframe_insert("value", frame=i)
                    obj.data.shape_keys.key_blocks[i].value = 0.0
                    obj.data.shape_keys.key_blocks[i].keyframe_insert("value", frame=(i - 1))
                    if i < self.numFrames - 1:
                        obj.data.shape_keys.key_blocks[i].keyframe_insert("value", frame=(i + 1))

                print("Animating - progress: %3i%%\r" % int(progressStatus), end='')

            # set sceen timeline to match imported model
            bpy.context.scene.frame_start = 0
            bpy.context.scene.frame_end = self.numFrames - 1

            print("Animating - progress: 100%.")

        # set frame back to old posi
        bpy.context.scene.frame_set(int_frame)

        bpy.context.view_layer.objects.active = obj  # 2.8
        bpy.context.view_layer.update()
        print("Model imported")

    def read(self, filePath):
        ''' open .md2 file and read contents '''
        self.filePath = filePath
        self.name = os.path.splitext(os.path.basename(filePath))[0]
        self.ext = os.path.splitext(os.path.basename(filePath))[1]
        self.skins = []
        self.uvs = []
        # test
        self.tris = []  # store triangle as 3 vertex index
        self.tris_uv = []
        self.frames = []
        self.frame_names = []

        # if self.ext not ".md2" or self.ext not ".mdx":
        #    return

        print("Reading: %s" % self.filePath, end='')
        # progressStatus = 0.0
        inFile = open(file=self.filePath, mode="rb")
        try:
            if self.isMdx:
                buff = inFile.read(struct.calcsize("<23i"))
                data = struct.unpack("<23i", buff)
                if data[0] != self.ident or data[1] != self.version:
                    raise NameError("Invalid MDX file")
                self.skinWidth = max(1, data[2])
                self.skinHeight = max(1, data[3])
                # framesize
                self.numSkins = data[5]
                self.numVerts = data[6]
                self.numTris = data[7]
                self.numGLCmds = data[8]
                if self.fImportAnimation:
                    self.numFrames = data[9]
                else:
                    self.numFrames = 1
                self.ofsSkins = data[13]
                self.ofsTris = data[14]
                self.ofsFrames = data[15]
                self.ofsGLCmds = data[16]
            else:
                buff = inFile.read(struct.calcsize("<17i"))
                data = struct.unpack("<17i", buff)
                if data[0] != self.ident or data[1] != self.version:
                    raise NameError("Invalid MD2 file")
                self.skinWidth = max(1, data[2])
                self.skinHeight = max(1, data[3])
                # framesize
                self.numSkins = data[5]
                self.numVerts = data[6]
                self.numUV = data[7]
                self.numTris = data[8]
                self.numGLCmds = data[9]    # hypo add:
                if self.fImportAnimation:
                    self.numFrames = data[10]
                else:
                    self.numFrames = 1
                self.ofsSkins = data[11]
                self.ofsUV = data[12]
                self.ofsTris = data[13]
                self.ofsFrames = data[14]
                self.ofsGLCmds = data[15]       # hypo add:

            # Skins
            if self.numSkins > 0:
                inFile.seek(self.ofsSkins, 0)
                for i in range(self.numSkins):
                    buff = inFile.read(struct.calcsize("<64s"))
                    data = struct.unpack("<64s", buff)
                    dataEx1 = data[0].decode("utf-8", "replace")
                    dataEx1 = dataEx1 + "\x00"  # append null. if string 64 chars
                    self.skins.append(asciiz(dataEx1))
                    # self.skins.append(asciiz(data[0].decode("utf-8", "replace")))  # KP_Util
            print('.', end='')

            # UV (software 1byte texture cords)
            if self.isMdx is False and self.numGLCmds <= 1:
                print(" (Model does not have GLCommands) ")
                inFile.seek(self.ofsUV, 0)
                for i in range(self.numUV):
                    buff = inFile.read(struct.calcsize("<2h"))
                    data = struct.unpack("<2h", buff)
                    # self.uvs.append((data[0] / self.skinWidth, 1 - (data[1] / self.skinHeight)))
                    # hypo add: index0
                    self.uvs.insert(
                        i, (data[0] / self.skinWidth, 1 - (data[1] / self.skinHeight)))

                # Tris (non GLCommand)
                inFile.seek(self.ofsTris, 0)
                for i in range(self.numTris):
                    buff = inFile.read(struct.calcsize("<6H"))
                    data = struct.unpack("<6H", buff)
                    self.tris.append((data[0], data[2], data[1]))
                    self.tris_uv.append((data[3], data[5], data[4]))  # 2.8 seperate uv
                    # self.tris_uv.append(data[3])  # 2.8 seperate uv
                    # self.tris_uv.append(data[5])  # 2.8 seperate uv
                    # self.tris_uv.append(data[4])  # 2.8 seperate uv todo:
                print('.', end='')

            else:
                # =====================================================================================
                # UV GLCommands (float texture cords)
                inFile.seek(self.ofsGLCmds, 0)
                uvIdx = 0

                def readGLVertex(inFile):
                    buff = inFile.read(struct.calcsize("<2f1l"))
                    data = struct.unpack("<2f1l", buff)
                    s = data[0]
                    t = 1.0 - data[1]  # flip Y
                    idx = data[2]
                    return (s, t, idx)

                # for glx in range(self.numGLCmds): #wont get to this number
                while 1:
                    if self.isMdx is True:
                        buff = inFile.read(struct.calcsize("<2l"))
                        data = struct.unpack("<2l", buff)
                    else:
                        buff = inFile.read(struct.calcsize("<l"))
                        data = struct.unpack("<l", buff)
                    # read strip
                    if data[0] >= 1:
                        numStripVerts = data[0]
                        v2 = readGLVertex(inFile)
                        v3 = readGLVertex(inFile)
                        self.uvs.append((v2[0], v2[1]))
                        self.uvs.append((v3[0], v3[1]))
                        uvIdx += 2
                        for i in range(1, (numStripVerts - 1), 1):
                            v1 = v2[:]  # new ref
                            v2 = v3[:]  # new ref
                            v3 = readGLVertex(inFile)
                            self.uvs.append((v3[0], v3[1]))
                            uvIdx += 1
                            if (i % 2) == 0:
                                self.tris.append((v1[2], v2[2], v3[2]))
                                self.tris_uv.append((uvIdx - 3, uvIdx - 2, uvIdx - 1))
                                # self.tris_uv.append(uvIdx-3)
                                # self.tris_uv.append(uvIdx - 2)
                                # self.tris_uv.append(uvIdx - 1)
                            else:
                                self.tris.append((v3[2], v2[2], v1[2]))
                                self.tris_uv.append((uvIdx - 1, uvIdx - 2, uvIdx - 3))
                                # self.tris_uv.append(uvIdx - 1)
                                # self.tris_uv.append(uvIdx - 2)
                                # self.tris_uv.append(uvIdx-3)
                    # read fan
                    elif data[0] <= -1:
                        numFanVerts = -data[0]
                        v1 = readGLVertex(inFile)
                        v3 = readGLVertex(inFile)
                        centreVert = uvIdx
                        self.uvs.append((v1[0], v1[1]))
                        self.uvs.append((v3[0], v3[1]))
                        uvIdx += 2
                        for i in range(1, (numFanVerts - 1), 1):
                            v2 = v3[:]  # new ref
                            v3 = readGLVertex(inFile)
                            uvIdx += 1
                            self.uvs.append((v3[0], v3[1]))
                            self.tris.append((v3[2], v2[2], v1[2]))
                            self.tris_uv.append((uvIdx - 1, uvIdx - 2, centreVert))
                            # self.tris_uv.append(uvIdx - 1)
                            # self.tris_uv.append(uvIdx - 2)
                            # self.tris_uv.append(centreVert)
                    else:
                        print("-= done gl =-")
                        break
                print('.', end='')
                # ===================================================================================

            # Frames
            inFile.seek(self.ofsFrames, 0)
            for i in range(self.numFrames):
                buff = inFile.read(struct.calcsize("<6f16s"))
                data = struct.unpack("<6f16s", buff)
                verts = []
                for j in range(self.numVerts):
                    buff = inFile.read(struct.calcsize("<4B"))
                    vert = struct.unpack("<4B", buff)
                    verts.append((data[0] * vert[0] + data[3],
                                  data[1] * vert[1] + data[4],
                                  data[2] * vert[2] + data[5]))
                self.frames.append(verts)  # todo append
                tmp_str = data[6].split(b'\x00')
                # tmp_str[0].decode('utf-8')
                self.frame_names.append(tmp_str[0])  # frame names

            print('.', end='')
        finally:
            inFile.close()
        print("Done")


def loadImage(mdxPath, filePath):
    # Handle ufoai skin name format
    fileName = os.path.basename(mdxPath)
    # if mdxPath[0] == '.':
    #   for ext in ['.png', '.jpg', '.jpeg']:
    #       fileName = mdxPath[1:] + ext
    #       if os.path.isfile(os.path.join(os.path.dirname(mdxPath), fileName)):
    #           break
    #       elif os.path.isfile(os.path.join(os.path.dirname(filePath), fileName)):
    #           break
    #   else:
    #       fileName = mdxPath[1:]
    image = load_image(fileName, dirname=os.path.dirname(mdxPath), recursive=False)
    if image is not None:
        return image
    image = load_image(fileName, dirname=os.path.dirname(filePath), recursive=False)
    if image is not None:
        return image

    # md2
    idxModels = filePath.find("models\\")
    idxPlayer = filePath.find("players\\")
    idxTextur = filePath.find("textures\\")

    outname = ""
    if idxModels >= 1:
        if filePath[0] == "/":
            outname = filePath[1:idxModels]
        else:
            outname = filePath[0:idxModels]
    elif idxPlayer >= 1:
        if filePath[0] == "/":
            outname = filePath[1:idxPlayer]  # trim
        else:
            outname = filePath[0:idxPlayer]  # trim

    idxModels = filePath.find("models\\")
    idxPlayer = filePath.find("players\\")
    idxTextur = filePath.find("textures\\")

    fullpath = outname + mdxPath
    fullpath = bpy.path.native_pathsep(fullpath)
    image = load_image(fileName, dirname=os.path.dirname(
        fullpath), recursive=False)
    print("\nfileName={}".format(fileName))
    print("path={}".format(fullpath))
    print("basepath={}".format(os.path.basename(fullpath)))
    print("dirname={}".format(os.path.dirname(fullpath)))
    if image is not None:
        return image

    print("image failed!!!")

    return None


def asciiz(s):
    for i, c in enumerate(s):
        if ord(c) == 0:
            return s[:i]


# def Import_MD2_fn(self, filename):
def load(self,
         filepath,
         *,
         fImportAnimation=False,
         fAddTimeline=False,
         relpath=None
         ):
    """

    """

    ext = os.path.splitext(os.path.basename(filepath))[1]
    if ext != '.md2' and ext != '.mdx':
        raise RuntimeError("ERROR: File not md2 or mdx")
        return False
    else:
        md2 = Kingpin_Model_Reader()
        md2.object = None
        md2.fImportAnimation = fImportAnimation
        md2.fAddTimeline = fAddTimeline
        if ext == '.mdx':
            md2.isMdx = True
            md2.ident = 1481655369
            md2.version = 4
        else:
            md2.isMdx = False
            md2.ident = 844121161
            md2.version = 8

        md2.read(self.filepath)
        md2.makeObject()

        return True
        # md2 = Kingpin_Model_Reader(self)
        # md2.read(self.filepath)
        # md2.makeObject()
