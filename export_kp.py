'''
exporter class/func

'''


import math
import os
import struct
# import shutil

if "bpy" in locals():
    import importlib
    if "common_kp" in locals():
        importlib.reload(common_kp)

import bpy
from bpy_extras.io_utils import ExportHelper
# from math import pi
from mathutils import Matrix, Euler


from .common_kp import (
    MD2_MAX_TRIANGLES,
    MD2_MAX_VERTS,
    MD2_MAX_FRAMES,
    MD2_MAX_SKINS,
    MD2_MAX_SKINNAME,
    MD2_NORMALS,
)


def isDepMatch(self, object):
    ''' does the Depsgraph object exist in selection'''
    for obj in self.objects:
        if obj.name == object.name:
            return True
    return False


def triangulateMesh_fn(object, depsgraph, tri=False):
    ''' only triangulate selected mesh '''
    if not object.type == 'MESH':
        return None, None

    depMesh = object.evaluated_get(depsgraph)  # .original.to_mesh()
    outMesh = depMesh.to_mesh()  # .original.to_mesh()
    outMesh.transform(object.matrix_world)  # added 1.21
    #  outMesh = object.data  # .original.to_mesh() # working old 2.8.0
    #  ###tmp_mesh.to_mesh_clear()disable if not used

    if outMesh is None or not object.type == 'MESH':
        depMesh.to_mesh_clear()
        return None, None

    if not outMesh.loop_triangles and outMesh.polygons:
        outMesh.calc_loop_triangles()
    return outMesh, depMesh


def calcSharedBBox_fn(self):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    min = [9999.0, 9999.0, 9999.0]
    max = [-9999.0, -9999.0, -9999.0]
    # for obj in self.objects:
    for object_instance in depsgraph.object_instances:
        obj = object_instance.object
        if isDepMatch(self, obj):  # obj.type == 'MESH':
            tmp_mesh, depMesh = triangulateMesh_fn(self, obj, depsgraph)
            if tmp_mesh is None:
                continue

            # md2_mesh.transform(matrix() @ obj.matrix_world)  # 2.8
            # md2_mesh.transform(Matrix.Rotation(math.pi / 2, 4, 'Z'))  # 2.7

            for vert in tmp_mesh.vertices:
                for i in range(3):
                    if vert.co[i] < min[i]:
                        min[i] = vert.co[i]
                    if vert.co[i] > max[i]:
                        max[i] = vert.co[i]
            depMesh.to_mesh_clear()  # 2.8 was disabled

    if self.bbox_min is None:
        self.bbox_min = [min[0], min[1], min[2]]
        self.bbox_max = [max[0], max[1], max[2]]
    else:
        for i in range(3):
            if self.bbox_min[i] > min[i]:
                self.bbox_min[i] = min[i]
            if self.bbox_max[i] < max[i]:
                self.bbox_max[i] = max[i]


def outFrame_fn(self, file, frameName="frame"):
    ''' build frame data '''
    # md2_mesh = self.object.to_mesh(bpy.context.scene, True, 'PREVIEW')  # 2.7
    depsgraph = bpy.context.evaluated_depsgraph_get()  # 2.8

    # md2_mesh.transform(matrix() @ self.object.matrix_world)  # 2.8
    # md2_mesh.transform(Matrix.Rotation(math.pi / 2, 4, 'Z'))  # 2.7

    min = [9999.0, 9999.0, 9999.0]
    max = [-9999.0, -9999.0, -9999.0]
    # ##### compute the bounding box ###############
    if not self.fUseSharedBoundingBox:  # .options
        # use bbox of selected item/s
        if not self.fIsPlayerModel:  # .options
            # for obj in self.objects:
            for object_instance in depsgraph.object_instances:
                obj = object_instance.object
                if isDepMatch(self, obj):  # obj.type == 'MESH':
                    tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph)
                    if tmp_mesh is None:
                        continue
                    for vert in tmp_mesh.vertices:
                        for i in range(3):
                            if vert.co[i] < min[i]:
                                min[i] = vert.co[i]
                            if vert.co[i] > max[i]:
                                max[i] = vert.co[i]
                    depMesh.to_mesh_clear()  # 2.8 was disabled
        else:
            # md2 PPM hypov8
            # calculate every 'visable' vertex in sceen to get player bbox
            # cant be used when using bbox for every frame (fUseSharedBoundingBox)
            # for obj in bpy.context.visible_objects:
            for object_instance in depsgraph.object_instances:
                obj = object_instance.object
                # if isDepMatch(self, obj):  # obj.type == 'MESH':
                if not obj.type == 'MESH':
                    continue

                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph)
                if tmp_mesh is None:
                    continue

                # tmpMesh.transform(matrix() @ tmpObj.matrix_world)  # 2.8
                # tmpMesh.transform(Matrix.Rotation(math.pi / 2, 4, 'Z'))  # 2.7

                for vert in tmp_mesh.vertices:
                    for i in range(3):
                        if vert.co[i] < min[i]:
                            min[i] = float(vert.co[i])
                        if vert.co[i] > max[i]:
                            max[i] = float(vert.co[i])
                depMesh.to_mesh_clear()  # 2.8 was disabled

        # print("bbox min({})\nbbox max({})\n".format(min, max))
        # #######################################
    else:
        # combined every grame BBox
        min = self.bbox_min
        max = self.bbox_max

    # mdx hitbox
    if self.isMdx:
        hitboxTmp = []
        hitboxMin = [9999, 9999, 9999]
        hitboxMax = [-9999, -9999, -9999]
        # for obj in self.objects:
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            if isDepMatch(self, obj):  # obj.type == 'MESH':
                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph)
                if tmp_mesh is None:
                    continue
                # seperate hitbox?
                if not self.fMergeHitbox:
                    hitboxMin = [9999, 9999, 9999]
                    hitboxMax = [-9999, -9999, -9999]

                for vert in tmp_mesh.vertices:
                    for i in range(3):
                        if vert.co[i] < hitboxMin[i]:
                            hitboxMin[i] = vert.co[i]
                        if vert.co[i] > hitboxMax[i]:
                            hitboxMax[i] = vert.co[i]

                depMesh.to_mesh_clear()  # 2.8 was disabled
                hitboxTmp.append([hitboxMin[0], hitboxMin[1], hitboxMin[2],
                                 hitboxMax[0], hitboxMax[1], hitboxMax[2]])
        if not self.fMergeHitbox:
            self.hitbox.append(hitboxTmp)
        else:
            self.hitbox.append([hitboxMin[0], hitboxMin[1], hitboxMin[2],
                               hitboxMax[0], hitboxMax[1], hitboxMax[2]])

    # deal with simple planes
    if (max[0] - min[0]) == 0.0:
        max[0] = 1.0
    if (max[1] - min[1]) == 0.0:
        max[1] = 1.0
    if (max[2] - min[2]) == 0.0:
        max[2] = 1.0

    # BL: some caching to speed it up:
    # -> sd_ gets the vertices between [0 and 255]
    #    which is our important quantization.
    sdx = (max[0] - min[0]) / 255.0
    sdy = (max[1] - min[1]) / 255.0
    sdz = (max[2] - min[2]) / 255.0
    isdx = float(255.0 / (max[0] - min[0]))
    isdy = float(255.0 / (max[1] - min[1]))
    isdz = float(255.0 / (max[2] - min[2]))

    # note about the scale: self.object.scale is already applied via matrix_world
    data = struct.pack("<6f16s",
                       # writing the scale of the model
                       sdx,
                       sdy,
                       sdz,
                       # now the initial offset (= min of bounding box)
                       min[0],
                       min[1],
                       min[2],
                       # and finally the name.
                       bytes(frameName[0:16], encoding="utf8"))
    file.write(data)  # frame header

    # for obj in self.objects:
    ofsetVertID = 0  # multi object
    for object_instance in depsgraph.object_instances:
        obj = object_instance.object
        if isDepMatch(self, obj):  # obj.type == 'MESH':
            tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph)
            if tmp_mesh is None:
                continue
            for vert in tmp_mesh.vertices:
                # find the closest normal for every vertex
                maxDot = -2.0
                bestNormalIndex = 0
                for iN in range(162):
                    # hypov8 no longer inverted x/y is this ok?
                    dot = vert.normal[0] * MD2_NORMALS[iN][0] + \
                        vert.normal[1] * MD2_NORMALS[iN][1] + \
                        vert.normal[2] * MD2_NORMALS[iN][2]

                    if dot > maxDot:
                        maxDot = dot
                        bestNormalIndex = iN

                # debug TODO cleanup
                vert1 = int(((float(vert.co[0]) - min[0]) * isdx) + 0.5)
                vert2 = int(((float(vert.co[1]) - min[1]) * isdy) + 0.5)
                vert3 = int(((float(vert.co[2]) - min[2]) * isdz) + 0.5)

                if bestNormalIndex >= 162:
                    bestNormalIndex = 162

                # and now write the normal. (compressed position. 256 bytes)
                data = struct.pack("<4B",
                                   #    int(((vert.co[0] - min[0]) * isdx) + 0.5),
                                   #    int(((vert.co[1] - min[1]) * isdy) + 0.5),
                                   #    int(((vert.co[2] - min[2]) * isdz) + 0.5),
                                   vert1,
                                   vert2,
                                   vert3,
                                   bestNormalIndex)

                file.write(data)  # write vertex and normal
            ofsetVertID += len(tmp_mesh.vertices)  # multi object
            depMesh.to_mesh_clear()  # 2.8 was disabled
    # print("finished writing frame")


def findStripLength_fn(self, mesh, startTri, startVert):
    ''' triangle strips '''
    from array import array
    # meshTextureFaces =  # self.mesh.tessface_uv_textures.active.data  #2.7
    meshTextureFaces = mesh.loop_triangles  # 'polygons  # 2.8
    numFaces = len(mesh.loop_triangles)  # 'polygons:  # tessfaces

    self.cmdVerts = []
    self.cmdTris = []
    self.cmdUV = []
    self.used[startTri] = 2

    # store first tri
    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[startVert % 3])  # vertices_raw
    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[(startVert + 2) % 3])
    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[(startVert + 1) % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[startVert % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[(startVert + 2) % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[(startVert + 1) % 3])

    stripCount = 1
    self.cmdTris.append(startTri)

    m1 = mesh.loop_triangles[startTri].vertices[(startVert + 2) % 3]
    m2 = mesh.loop_triangles[startTri].vertices[(startVert + 1) % 3]
    u1 = meshTextureFaces[startTri].loops[(startVert + 2) % 3]  # hypov8 add:
    u2 = meshTextureFaces[startTri].loops[(startVert + 1) % 3]  # hypov8 add:

    for triCounter in range(startTri + 1, numFaces):
        for k in range(3):
            uvID1 = meshTextureFaces[triCounter].loops[k]
            uvID2 = meshTextureFaces[triCounter].loops[(k + 1) % 3]
            if((mesh.loop_triangles[triCounter].vertices[k] == m1) and
               (mesh.loop_triangles[triCounter].vertices[(k + 1) % 3] == m2) and
               # compare texture floats. not indices
               (mesh.uv_layers[0].data[uvID1].uv[0] == mesh.uv_layers[0].data[u1].uv[0]) and
               (mesh.uv_layers[0].data[uvID1].uv[1] == mesh.uv_layers[0].data[u1].uv[1]) and
               (mesh.uv_layers[0].data[uvID2].uv[0] == mesh.uv_layers[0].data[u2].uv[0]) and
               (mesh.uv_layers[0].data[uvID2].uv[1] == mesh.uv_layers[0].data[u2].uv[1])
               ):  # hypov8 add: make sure uv also match
                if(self.used[triCounter] == 0):
                    if(stripCount % 2 == 1):  # is this an odd tri
                        m1 = mesh.loop_triangles[triCounter].vertices[(k + 2) % 3]
                        u1 = meshTextureFaces[triCounter].loops[(k + 2) % 3]
                    else:
                        m2 = mesh.loop_triangles[triCounter].vertices[(k + 2) % 3]
                        u2 = meshTextureFaces[triCounter].loops[(k + 2) % 3]

                    self.cmdVerts.append(mesh.loop_triangles[triCounter].vertices[(k + 2) % 3])
                    self.cmdUV.append(meshTextureFaces[triCounter].loops[(k + 2) % 3])
                    stripCount += 1
                    self.cmdTris.append(triCounter)

                    self.used[triCounter] = 2
                    triCounter = startTri + 1  # restart looking

    # clear used counter
    for usedCounter in range(numFaces):
        if self.used[usedCounter] == 2:
            self.used[usedCounter] = 0

    return stripCount  # debug


def findFanLength_fn(self, mesh, startTri, startVert):
    ''' triangle strips '''
    # meshTextureFaces =  # self.mesh.tessface_uv_textures.active.data  #2.7
    meshTextureFaces = mesh.loop_triangles  # 2.8
    numFaces = len(mesh.loop_triangles)  # 'polygons:  # tessfaces

    self.cmdVerts = []
    self.cmdTris = []
    self.cmdUV = []
    self.used[startTri] = 2

    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[startVert % 3])  # vertices_raw
    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[(startVert + 2) % 3])
    self.cmdVerts.append(mesh.loop_triangles[startTri].vertices[(startVert + 1) % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[startVert % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[(startVert + 2) % 3])
    self.cmdUV.append(meshTextureFaces[startTri].loops[(startVert + 1) % 3])

    fanCount = 1
    self.cmdTris.append(startTri)
    m2 = mesh.loop_triangles[startTri].vertices[(startVert + 0) % 3]
    m1 = mesh.loop_triangles[startTri].vertices[(startVert + 1) % 3]
    u2 = meshTextureFaces[startTri].loops[(startVert + 0) % 3]  # hypov8 add:
    u1 = meshTextureFaces[startTri].loops[(startVert + 1) % 3]  # hypov8 add:

    for triCounter in range(startTri + 1, numFaces):
        for k in range(3):
            uvID1 = meshTextureFaces[triCounter].loops[k]
            uvID2 = meshTextureFaces[triCounter].loops[(k + 1) % 3]

            if((mesh.loop_triangles[triCounter].vertices[k] == m1) and
               (mesh.loop_triangles[triCounter].vertices[(k + 1) % 3] == m2) and
                # compare texture floats. not indices
               (mesh.uv_layers[0].data[uvID1].uv[0] == mesh.uv_layers[0].data[u1].uv[0]) and
               (mesh.uv_layers[0].data[uvID1].uv[1] == mesh.uv_layers[0].data[u1].uv[1]) and
               (mesh.uv_layers[0].data[uvID2].uv[0] == mesh.uv_layers[0].data[u2].uv[0]) and
               (mesh.uv_layers[0].data[uvID2].uv[1] == mesh.uv_layers[0].data[u2].uv[1])
               ):  # hypov8 add: make sure uv also match

                if(self.used[triCounter] == 0):
                    m1 = mesh.loop_triangles[triCounter].vertices[(k + 2) % 3]
                    u1 = meshTextureFaces[triCounter].loops[(k + 2) % 3]

                    self.cmdVerts.append(mesh.loop_triangles[triCounter].vertices[(k + 2) % 3])
                    self.cmdUV.append(meshTextureFaces[triCounter].loops[(k + 2) % 3])
                    fanCount += 1
                    self.cmdTris.append(triCounter)

                    self.used[triCounter] = 2
                    triCounter = startTri + 1  # restart looking
                    # hypo todo: check this go back n test all tri again?

    # clear used counter
    for usedCounter in range(numFaces):
        if self.used[usedCounter] == 2:
            self.used[usedCounter] = 0

    return fanCount  # debug


def buildGLcommands_fn(self):
    ''' build gl commands '''
    print("Building GLCommands...")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    self.glCmdList = []

    # for obj in self.objects:
    mdxID = 0  # mdx hitbox index number
    ofsetVertID = 0   # multi object
    offsetTexID = 0
    numCommands = 0
    for object_instance in depsgraph.object_instances:
        obj = object_instance.object
        if isDepMatch(self, obj):  # obj.type == 'MESH':
            tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph, tri=True)
            if tmp_mesh is None:
                continue
            numFaces = len(tmp_mesh.loop_triangles)  # 'polygons:  # tessfaces
            self.used = [0] * numFaces
            # numCommands = 0

            for triCounter in range(numFaces):
                if self.used[triCounter] == 0:
                    # intialization
                    bestLength = 0
                    bestType = 0
                    bestVerts = []
                    bestTris = []
                    bestUV = []

                    for startVert in range(3):
                        cmdLength = findFanLength_fn(self, tmp_mesh, triCounter, startVert)
                        if (cmdLength > bestLength):
                            bestType = 1
                            bestLength = cmdLength
                            bestVerts = self.cmdVerts
                            bestTris = self.cmdTris
                            bestUV = self.cmdUV

                        cmdLength = findStripLength_fn(self, tmp_mesh, triCounter, startVert)
                        if (cmdLength > bestLength):
                            bestType = 0
                            bestLength = cmdLength
                            bestVerts = self.cmdVerts
                            bestTris = self.cmdTris
                            bestUV = self.cmdUV

                    # mark tris as used
                    for usedCounter in range(bestLength):
                        self.used[bestTris[usedCounter]] = 1

                    cmd = []
                    if bestType == 0:   # strip
                        num = bestLength + 2
                    else:               # fan
                        num = (-(bestLength + 2))

                    numCommands += 1
                    if self.isMdx:  # mdx
                        numCommands += 1  # sub-object number

                    uv_layer = tmp_mesh.uv_layers[0].data  # TODO only get 1 layer ok?
                    for cmdCounter in range(bestLength + 2):
                        # (u,v) in blender -> (u,1-v)
                        cmd.append((0.0 + uv_layer[bestUV[cmdCounter]].uv[0],
                                    1.0 - uv_layer[bestUV[cmdCounter]].uv[1],
                                    bestVerts[cmdCounter] + ofsetVertID))  # multi object
                        numCommands += 3

                    self.glCmdList.append((num, mdxID, cmd))

            #  multi part object offset
            ofsetVertID += len(tmp_mesh.vertices)  # 1 #self.ofsetVertID[mdxID]  # multi object
            offsetTexID += 2  # self.offsetTexID[mdxID]  # multi object
            mdxID += 1  # todo: ui option. prevent counter
            depMesh.to_mesh_clear()  # 2.8 was disabled
            del self.used, bestVerts, bestUV, bestTris, self.cmdVerts, self.cmdUV, self.cmdTris
    print("Finished GLCommands")
    print("numGlCommands=%i".format(numCommands))
    return numCommands
    # return 0  # debug software


def write_fn(self, filePath):
    ''' build a valid model and export '''
    depsgraph = bpy.context.evaluated_depsgraph_get()

    def getSkins_fn(objects, method):
        skins = []
        width = height = 256
        foundWH = False  # only use size from first valid iage

        triCount = 0
        for obj in objects:
            if obj.type == 'MESH':  # TODO
                for material in obj.data.materials:
                    texname = "tris.tga"
                    # get material name
                    if material:
                        texname = material.name

                    # option use texture name or texture path
                    if material and material.use_nodes:
                        for n in material.node_tree.nodes:
                            if n.type == 'TEX_IMAGE' and n.image:
                                # get image size
                                wSize = n.image.size[0]
                                hSize = n.image.size[1]
                                if not foundWH and hSize > 0 and wSize > 0:
                                    height = hSize
                                    width = wSize
                                    foundWH = True

                                if method == 'DATAPATH':
                                    tmpp = bpy.path.abspath(n.image.filepath, library=n.image.library)
                                    texname_tmp = os.path.normpath(tmpp)
                                    modelIdx = texname_tmp.find("models")
                                    plyerIdx = texname_tmp.find("players")
                                    textrIdx = texname_tmp.find("textures")

                                    if modelIdx >= 0:
                                        texname = texname_tmp[modelIdx:]
                                        texname = texname.replace('\\', '/')
                                    elif plyerIdx >= 0:
                                        texname = texname_tmp[plyerIdx:]
                                        texname = texname.replace('\\', '/')
                                    elif textrIdx >= 0:
                                        texname = texname_tmp[textrIdx:]
                                        texname = texname.replace('\\', '/')
                                elif method == 'DATANAME':
                                    texname = n.image.name

                                break  # only use first valid image from node.

                    # only unique
                    if material and texname not in skins and len(skins) <= MD2_MAX_SKINS:
                        skins.append(texname)

        if len(skins) < 1:
            # raise RuntimeError("There must be at least one skin")
            skins.append("tris.tga")
        # if len(skins) > MD2_MAX_SKINS:
        #    raise RuntimeError("There are too many skins (%i), at most %i are supported in model"
        #                      % (len(self.info.skins), MD2_MAX_SKINS))

        print("===============\n" +
              "Skins\n" +
              "===============" +
              "Count:  %i\n" +
              "Width:  %i\n" +
              "Height: %i".format(len(skins), width, height))
        for idx, skin in enumerate(skins):
            print("%i: %s".format(idx + 1, skin[0:MD2_MAX_SKINNAME]))
        print("===============")

        return width, height, skins

    def buildTexCoord(objects):
        # print("uv")  # TODO error if no uv?
        uvList = []
        uvDict = {}
        uvCount = 0
        # Create an UV coord dictionary to avoid duplicate entries and save space
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            if isDepMatch(self, obj):  # obj.type == 'MESH':
                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph, tri=True)
                if tmp_mesh is None:
                    continue
                if len(tmp_mesh.uv_layers) > 0:
                    # Make our own list so it can be sorted to reduce context switching
                    # face_index_pairs = [(face, index) for index, face in enumerate(tmp_mesh.polygons)]

                    if tmp_mesh.uv_layers[0].active:
                        meshTextureFaces = tmp_mesh.uv_layers[0].data

                        tmp_uvs = []
                        for meshTextureFace in meshTextureFaces:
                            tmp_uvs.append((meshTextureFace.uv[0], meshTextureFace.uv[1]))

                        for uv in tmp_uvs:
                            if uv not in uvDict.keys():
                                uvList.append(uv)
                                uvDict[uv] = uvCount
                                uvCount += 1
                else:
                    raise RuntimeError("Objest (%s) does not have any UV mapping"
                                       % (obj.name, MD2_MAX_SKINS))
                depMesh.to_mesh_clear()  # 2.8 was disabled

        return uvCount, uvList, uvDict

    def getPolyCount(objects):
        triCount = 0
        # for obj in objects:
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            if isDepMatch(self, obj):  # obj.type == 'MESH':
                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph, tri=True)
                if tmp_mesh is None:
                    continue
                triCount += len(tmp_mesh.loop_triangles)  # 'polygons:
                depMesh.to_mesh_clear()  # 2.8 was disabled

        if triCount > MD2_MAX_TRIANGLES:
            raise RuntimeError("Object has too many (triangulated) faces (%i), at most %i are supported in md2"
                               % (triCount, MD2_MAX_TRIANGLES))
        return triCount

    def getVertexCount(objects):
        vertCount = 0
        # for obj in objects:
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            if isDepMatch(self, obj):  # obj.type == 'MESH':
                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph, tri=True)
                if tmp_mesh is None:
                    continue
                vertCount += len(tmp_mesh.vertices)
                depMesh.to_mesh_clear()  # 2.8 was disabled

        if vertCount > MD2_MAX_TRIANGLES:
            raise RuntimeError("Object has too many (triangulated) faces (%i), at most %i are supported in md2"
                               % (vertCount, MD2_MAX_TRIANGLES))
        return vertCount

    def getObjectCount(objects):
        objectCount = 0
        for obj in objects:
            if obj.type == 'MESH':  # TODO
                objectCount += 1
                # merge objects
                if self.fMergeHitbox:
                    return 1

        return objectCount

    self.hitbox = []  # mdx hitbox
    self.vertCounter = []
    self.skinWidth, self.skinHeight, self.skins = getSkins_fn(self.objects, self.eTextureNameMethod)
    if self.skinWidth < 8:
        self.skinWidth = 64
    elif self.skinWidth > 480:
        self.skinWidth = 480

    if self.skinHeight < 8:
        self.skinHeight = 64
    elif self.skinHeight > 480:
        self.skinHeight = 480
    #
    self.numSkins = len(self.skins)
    self.numVerts = getVertexCount(self.objects)  # len(self.mesh.vertices)
    self.numUV, uvList, uvDict = buildTexCoord(self.objects)  # , uvDict isUnwrapped
    self.numTris = getPolyCount(self.objects)  # len(self.mesh.polygons)  # tessfaces
    #
    self.numGLCmds = 1 + buildGLcommands_fn(self)  # TODO slow

    self.numFrames = 1
    if self.fExportAnimation:  # .options
        self.numFrames = 1 + self.fEndFrame - self.fStartFrame
    if self.frames > MD2_MAX_FRAMES and self.fExportAnimation:  # todo: kp supports more
        raise RuntimeError("There are too many frames (%i), at most %i are supported in md2"
                           % (info.frames, MD2_MAX_FRAMES))

    self.frameSize = struct.calcsize("<6f16s") + struct.calcsize("<4B") * self.numVerts
    if self.isMdx:
        self.numSfxDefines = 0  # mdx
        self.numSfxEntries = 0  # mdx
        self.numSubObjects = getObjectCount(self.objects)  # mdx

        self.ofsSkins = struct.calcsize("<23i")  # mdx
        self.ofsTris = self.ofsSkins + struct.calcsize("<64s") * self.numSkins
        self.ofsFrames = self.ofsTris + struct.calcsize("<6H") * self.numTris
        self.ofsGLCmds = self.ofsFrames + self.frameSize * self.numFrames

        self.ofsVertexInfo = self.ofsGLCmds + struct.calcsize("<i") * self.numGLCmds  # mdx
        self.ofsSfxDefines = self.ofsVertexInfo + struct.calcsize("<i") * (self.numVerts)  # * self.numSubObjects
        self.ofsSfxEntries = self.ofsSfxDefines  # mdx
        self.ofsBBoxFrames = self.ofsSfxEntries  # mdx
        self.ofsDummyEnd = self.ofsBBoxFrames + struct.calcsize("<6i") * (self.numFrames * self.numSubObjects)  # mdx
        self.ofsEnd = self.ofsDummyEnd  # + struct.calcsize("<i")
    else:
        self.ofsSkins = struct.calcsize("<17i")
        self.ofsUV = self.ofsSkins + struct.calcsize("<64s") * self.numSkins
        self.ofsTris = self.ofsUV + struct.calcsize("<2h") * self.numUV
        self.ofsFrames = self.ofsTris + struct.calcsize("<6H") * self.numTris
        self.ofsGLCmds = self.ofsFrames + self.frameSize * self.numFrames
        self.ofsEnd = self.ofsGLCmds + struct.calcsize("<i") * self.numGLCmds

    file = open(filePath, "wb")
    try:
        # ####################
        # ### write header ###
        if self.isMdx:
            data = struct.pack("<23i",  # mdx
                               self.ident,
                               self.version,
                               self.skinWidth,
                               self.skinHeight,
                               self.frameSize,
                               self.numSkins,
                               self.numVerts,
                               self.numTris,
                               self.numGLCmds,
                               self.numFrames,
                               self.numSfxDefines,  # mdx
                               self.numSfxEntries,  # mdx
                               self.numSubObjects,  # mdx
                               self.ofsSkins,
                               self.ofsTris,
                               self.ofsFrames,
                               self.ofsGLCmds,
                               self.ofsVertexInfo,  # mdx
                               self.ofsSfxDefines,  # mdx
                               self.ofsSfxEntries,  # mdx
                               self.ofsBBoxFrames,  # mdx
                               self.ofsDummyEnd,  # mdx
                               self.ofsEnd)
        else:
            data = struct.pack("<17i",
                               self.ident,
                               self.version,
                               self.skinWidth,
                               self.skinHeight,
                               self.frameSize,
                               self.numSkins,
                               self.numVerts,
                               self.numUV,  # number of texture coordinates
                               self.numTris,
                               self.numGLCmds,
                               self.numFrames,
                               self.ofsSkins,
                               self.ofsUV,
                               self.ofsTris,
                               self.ofsFrames,
                               self.ofsGLCmds,
                               self.ofsEnd)
        file.write(data)

        # #############################
        # ### write skin file names ###
        for skinName in self.skins:  # enumerate(# TODO file path?
            data = struct.pack("<64s", bytes(skinName[0:MD2_MAX_SKINNAME], encoding="utf8"))
            file.write(data)  # skin name

        # ###############################
        # ### write software uv index ###
        if not self.isMdx:
            for uv in uvList:
                data = struct.pack("<2h",
                                   int(uv[0] * self.skinWidth),
                                   int((1 - uv[1]) * self.skinHeight)
                                   )
                file.write(data)  # uv
        del uvList

        # #################################
        # ### write triangle index data ###
        ofsetVertID = 0
        offsetTexID = 0
        objIdx = 0
        self.ofsetVertID = []
        self.offsetTexID = []
        for object_instance in depsgraph.object_instances:
            obj = object_instance.object
            if isDepMatch(self, obj):  # obj.type == 'MESH':
                tmp_mesh, depMesh = triangulateMesh_fn(obj, depsgraph, tri=True)
                if tmp_mesh is None:
                    continue
                v_Counter = 0
                uvCounter = 0
                for face in tmp_mesh.loop_triangles:  # 'polygons:  # 2.8
                    # 0,2,1 for good cw/ccw
                    data = struct.pack(
                        "<3H",  # ### write vert indices ###
                        face.vertices[0] + ofsetVertID,
                        face.vertices[2] + ofsetVertID,
                        face.vertices[1] + ofsetVertID
                    )
                    file.write(data)  # vert uv index data

                    uv0 = tmp_mesh.uv_layers[0].data[face.loops[0]].uv
                    uv1 = tmp_mesh.uv_layers[0].data[face.loops[1]].uv
                    uv2 = tmp_mesh.uv_layers[0].data[face.loops[2]].uv

                    data = struct.pack(
                        "<3H",  # ### write tex cord indices ###
                        # uvDict[(uvs[0][0], uvs[0][1])],
                        # uvDict[(uvs[2][0], uvs[2][1])],
                        # uvDict[(uvs[1][0], uvs[1][1])],
                        uvDict[(uv0[0], uv0[1])],
                        uvDict[(uv2[0], uv2[1])],
                        uvDict[(uv1[0], uv1[1])],


                        # face.loops[0] + offsetTexID,
                        # face.loops[2] + offsetTexID,
                        # face.loops[1] + offsetTexID
                    )
                    file.write(data)  # uv index

                ofsetVertID += len(tmp_mesh.vertices)
                offsetTexID += len(tmp_mesh.uv_layers[0].data)
                self.vertCounter.append(len(tmp_mesh.vertices))
                depMesh.to_mesh_clear()  # 2.8 was disabled
        del uvDict

        # ####################
        # ### write frames ###
        if self.fExportAnimation and self.numFrames > 1:  # .options
            timeLineMarkers = []
            for marker in bpy.context.scene.timeline_markers:
                timeLineMarkers.append(marker)

            # sort the markers. The marker with the frame number closest to 0 will be the first marker in the list.
            # The marker with the biggest frame number will be the last marker in the list
            timeLineMarkers.sort(key=lambda marker: marker.frame)
            markerIdx = 0

            # delete markers at same frame positions
            if len(timeLineMarkers) > 1:
                markerFrame = timeLineMarkers[len(timeLineMarkers) - 1].frame
                for i in range(len(timeLineMarkers) - 2, -1, -1):
                    if timeLineMarkers[i].frame == markerFrame:
                        del timeLineMarkers[i]
                    else:
                        markerFrame = timeLineMarkers[i].frame

            # calculate shared bounding box
            if self.fUseSharedBoundingBox:  # .options
                self.bbox_min = None
                self.bbox_max = None
                for frame in range(self.fStartFrame, self.fEndFrame + 1):
                    bpy.context.scene.frame_set(frame, subframe=0.0)
                    self.calcSharedBBox_fn()
            fNameIdx = 1
            for frame in range(self.fStartFrame, self.fEndFrame + 1):
                frameIdx = frame - self.fStartFrame + 1

                # Display the progress status of the export in the console
                progressStatus = frameIdx / self.numFrames * 100
                print("Export progress: %3i%%\r".format(int(progressStatus), end=''))

                bpy.context.scene.frame_set(frame)  # , subframe=0.0

                if len(timeLineMarkers) != 0:
                    if markerIdx + 1 != len(timeLineMarkers):
                        if frame >= timeLineMarkers[markerIdx + 1].frame:
                            markerIdx += 1
                            fNameIdx = 1
                        else:
                            fNameIdx += 1
                    name = timeLineMarkers[markerIdx].name + ('%02d' % fNameIdx)  #
                else:
                    name = "frame_" + str(frameIdx)

                outFrame_fn(self, file, name)
        else:
            if self.fUseSharedBoundingBox:  # .options
                self.bbox_min = None
                self.bbox_max = None
                self.calcSharedBBox_fn()
            outFrame_fn(self, file, "FRAME1")
        # end writing frame/s

        # ### GL Commands ###
        for glCmd in self.glCmdList:
            if self.isMdx:
                data = struct.pack("<iL", glCmd[0], glCmd[1])
            else:
                data = struct.pack("<i", glCmd[0])
            file.write(data)

            for cmd in glCmd[2]:
                data = struct.pack("<ffI", cmd[0], cmd[1], cmd[2])
                file.write(data)
        # NULL GLCommand
        data = struct.pack("<I", 0)
        file.write(data)

        if self.isMdx:
            # ofsVertexInfo #mdx
            # for mdxObj in range(self.numSubObjects):
            for mdxObj, vCount in enumerate(self.vertCounter):  # range(self.numVerts):  # self.mesh.tessfaces:
                for i in range(vCount):
                    if not self.fMergeHitbox:
                        bits = (1 << mdxObj)
                    else:
                        bits = 1
                    data = struct.pack("<i", bits)  # fill as object #1 TODO
                    file.write(data)  # vert index

            # ofsSfxDefines #mdx
            # ofsSfxEntries #mdx

            # ofsBBoxFrames #mdx
            objIdx = 0
            for mdxObj in range(self.numSubObjects):
                for i in range(self.numFrames):
                    data = struct.pack("<6f",
                                       self.hitbox[i][mdxObj][0],
                                       self.hitbox[i][mdxObj][1],
                                       self.hitbox[i][mdxObj][2],
                                       self.hitbox[i][mdxObj][3],
                                       self.hitbox[i][mdxObj][4],
                                       self.hitbox[i][mdxObj][5],
                                       )
                    file.write(data)
    finally:
        file.close()
    print("Export progress: 100% - Model exported.")


def applyModifiers_fn(object):
    if len(object.modifiers) == 0:
        return object

    modifier = object.modifiers.new('Triangulate-Export', 'TRIANGULATE')
    # mesh = object.to_mesh(bpy.context.scene, True, 'PREVIEW')  # 2.7
    # mesh = object.to_mesh(preserve_all_data_layers=False)  # 2.8
    depsgraph = bpy.context.evaluated_depsgraph_get()  # 2.8
    mesh = object.evaluated_get(depsgraph).to_mesh()  # 2.8

    modifiedObj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.objects.link(modifiedObj)
    object.modifiers.remove(modifier)

    return modifiedObj


def isObj_mesh_fn(objects):
    for obj in objects:
        if obj.type == 'MESH':
            return True
    return False


def Export_MD2_fn(self, filepath):
    '''    Export model    '''
    ext = os.path.splitext(os.path.basename(filepath))[1]
    if ext != '.md2' and ext != '.mdx':
        raise RuntimeError("ERROR: File not md2 or mdx")
        return False

    if ext == '.mdx':
        self.isMdx = True
        self.ident = 1481655369
        self.version = 4
    else:
        filePath = bpy.path.ensure_ext(filepath, self.filename_ext)
        self.isMdx = False
        self.ident = 844121161
        self.version = 8

    self.vertices = -1
    self.faces = 0
    self.status = ('', '')
    self.frames = 1 + self.fEndFrame - self.fStartFrame
    self.isMesh = isObj_mesh_fn(self.objects)

    if self.isMesh:

        if self.fExportAnimation:
            frame = bpy.context.scene.frame_current

        try:
            write_fn(self, filepath)
        finally:
            if self.fExportAnimation:
                bpy.context.scene.frame_set(frame, subframe=0.0)
    else:
        raise RuntimeError("Only a meshe object can be exported")
