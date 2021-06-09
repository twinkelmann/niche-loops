# <pep8 compliant>
#    Niche Loops, also known as Way too Niche and Peculiar but Actually Necessary Loop Tools
#    is an add-on that includes a few interesting loop tools
#    Copyright (C) 2021 Tim Winkelmann
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import bmesh
import mathutils
import enum


bl_info = {
    "name":        "Niche Loops",
    "author":      "Tim Winkelmann <twinkelmann@pm.me>",
    "version":     (1, 0, 0),
    "blender":     (2, 92, 0),
    "location":    "View3D > Sidebar > Edit Tab / Edit Mode Context Menu",
    "description": "This add-on includes the following operators: Build End, Build Corner, Adjust Loops, Adjust Adjacent Loops",
    "warning":     "",
    "wiki_url":    "https://github.com/winktim/niche-loops",
    "tracker_url": "https://github.com/winktim/niche-loops/issues",
    "category":    "Mesh"
}


QUAD = 4
HEXAGON = 6


class NlBuildType(enum.Enum):
    end = 1
    corner = 2


def reverse(tuples):
    """
    Return a new tuple containing the original values in reverse order
    https://www.geeksforgeeks.org/python-reversing-tuple/
    :return: tuple
    """
    return tuples[::-1]


def nl_build_core(type, obj, operator_factor, report):
    """
    Core of the Build End and Build Corner logic
    :return: nothing
    """
    data = obj.data

    # we need to switch from Edit mode to Object mode so the selection gets updated
    # https://blender.stackexchange.com/questions/1412/efficient-way-to-get-selected-vertices-via-python-without-iterating-over-the-en
    bpy.ops.object.mode_set(mode='OBJECT')

    selected_verts = [i for i in data.vertices if i.select is True]

    # back to whatever mode we were in
    bpy.ops.object.mode_set(mode='EDIT')
    num_selected_verts = len(selected_verts)

    # we need exactly 2
    if num_selected_verts != 2:
        report({'ERROR_INVALID_INPUT'}, "Exactly 2 vertices must be selected")
        return {'CANCELLED'}

    # get all ngons with 6 vertices
    ngons = [i for i in data.polygons if i.loop_total == HEXAGON]
    num_ngons = len(ngons)

    # we need at least one ngon
    if num_ngons < 1:
        report({'ERROR_INVALID_INPUT'},
               "Mesh doesn't contain any hexagon")
        return {'CANCELLED'}

    # find the ngon on which the 2 vertices are
    ngon_to_cut = None
    # store the verts for optimization
    all_verts_indices = None

    selected_verts_indices = (selected_verts[0].index, selected_verts[1].index)

    for i in range(num_ngons):
        ngon = ngons[i]
        verts = ngon.vertices
        # keep the vertices if they match our 2 selected
        found_verts = [j for j in verts if j ==
                       selected_verts_indices[0] or j == selected_verts_indices[1]]

        # if this ngon has the 2 selected vertices, then the output list will be of len 2
        if len(found_verts) == 2:
            ngon_to_cut = ngon
            all_verts_indices = verts
            break

    # the 2 selected vertices are not on the same ngon
    if ngon_to_cut is None:
        report({'ERROR_INVALID_INPUT'},
               "The 2 selected vertices are not on an hexagon, or not on the same hexagon")
        return {'CANCELLED'}

    all_edge_keys = ngon_to_cut.edge_keys
    num_all_verts = len(all_verts_indices)

    if type == NlBuildType.end:

        # check that the 2 selected vertices are part of the same edge
        if not selected_verts_indices in all_edge_keys:
            report({'ERROR_INVALID_INPUT'},
                   "The 2 selected vertices do not share the same edge")
            return {'CANCELLED'}

        return NlBuildEnd.build_end(data, all_verts_indices, selected_verts_indices, operator_factor, report)
    elif type == NlBuildType.corner:
        # check that the there is 1 vertex inbetween the 2 selected vertices
        # this is a 6 sided ngon

        first_vert_in_list = list(all_verts_indices).index(
            selected_verts_indices[0])
        expected_second_vert_in_list = (first_vert_in_list + 2) % HEXAGON

        # also store the vertex in the middle of the selection for later use
        middle_vertex_index = (first_vert_in_list + 1) % HEXAGON

        if (all_verts_indices[expected_second_vert_in_list] != selected_verts_indices[1]):
            # if the second vert is not 1 vertex away from the first, worry not. let's try from the second vert
            second_vert_in_list = list(all_verts_indices).index(
                selected_verts_indices[1])
            expected_first_vert_in_list = (second_vert_in_list + 2) % HEXAGON

            if (expected_first_vert_in_list != first_vert_in_list):
                report({'ERROR_INVALID_INPUT'},
                       "The 2 selected vertices are not seperated by 1 vertex")
                return {'CANCELLED'}
            else:
                # save the correct vertex
                middle_vertex_index = (second_vert_in_list + 1) % HEXAGON

        return NlBuildCorner.build_corner(data, all_verts_indices, selected_verts_indices, middle_vertex_index, operator_factor, report)


def nl_adjust_loops(obj, adjustment, report):
    """
    Core of the Adjust loops logic
    :return: nothing
    """
    data = obj.data

    # we need to switch from Edit mode to Object mode so the selection gets updated
    # https://blender.stackexchange.com/questions/1412/efficient-way-to-get-selected-vertices-via-python-without-iterating-over-the-en
    bpy.ops.object.mode_set(mode='OBJECT')

    selected_edges = [i for i in data.edges if i.select is True]
    num_selected_edges = len(selected_edges)

    # back to whatever mode we were in
    bpy.ops.object.mode_set(mode='EDIT')

    # we need at least 2 edges
    if num_selected_edges < 2:
        report({'ERROR_INVALID_INPUT'}, "At least 2 edges must be selected")
        return {'CANCELLED'}

    # convert edges to vertices tuple
    verts = [tuple(selected_edges[i].vertices)
             for i in range(num_selected_edges)]

    # for each polygon, find all the selected edges they contain
    num_polygons = len(data.polygons)
    face_edges = [None] * num_polygons
    # optimisation: store how many faces have been found alreadyx
    # that way we can ignore the checks once we reach 2
    num_edges_found = [0] * num_polygons

    for i in range(num_polygons):
        edge_keys = list(data.polygons[i].edge_keys)

        # ignore non quads
        if len(edge_keys) != QUAD:
            continue

        for j in range(num_selected_edges):
            # don't stop at 2, because maybe the first 2 are not opposite
            # it is cheaper to exclude the face because it has more than 2
            # than by checking if the edges are opposite
            if num_edges_found[i] >= 3:
                break

            # only check for reversed keys if we didn't find it in standard order
            # do this here separately in order to overwrite the data with the reversed keys
            # if they are the ones that worked, without having to re-reverse them later
            is_in_edge_keys = verts[j] in edge_keys
            reversed_keys = reverse(verts[j]) if not is_in_edge_keys else None
            is_in_edge_reversed_keys = reversed_keys in edge_keys if not is_in_edge_keys else False

            if is_in_edge_keys or is_in_edge_reversed_keys:
                num_edges_found[i] += 1

                if (face_edges[i] is None):
                    face_edges[i] = [j]
                else:
                    face_edges[i].append(j)

            if is_in_edge_reversed_keys:
                # store the reversed keys as the normal keys
                verts[j] = reversed_keys

    # filter the faces
    filtered = []

    for i in range(num_polygons):
        # ignore the polygons that don't have exactly 2 selected edges
        if num_edges_found[i] != 2:
            continue

        face_data = face_edges[i]
        edge_keys = data.polygons[i].edge_keys
        edge_0 = verts[face_data[0]]
        edge_1 = verts[face_data[1]]

        index_0 = edge_keys.index(edge_0)
        index_1 = edge_keys.index(edge_1)

        # ignore the polygons where the selected edges are not opposite
        if abs(index_0 - index_1) != 2:
            continue
            # edges are opposite, keep face

        # keep the face index in a tupple for later use
        # we don't need the second edge anymore. we will find the vertices later manually
        filtered.append((i, edge_0))

    num_filtered = len(filtered)

    # we need at least 1 edge
    if num_filtered <= 0:
        report({'ERROR_INVALID_INPUT'}, "At least 1 edge pair must be selected")
        return {'CANCELLED'}

    # pair edge keys
    list_of_2_points = []

    # find the corresponding vertices
    for i in range(num_filtered):
        corresponding_vertices = get_corresponding_indices(
            list(data.polygons[filtered[i][0]].vertices), filtered[i][1])

        # store the lists as strings of space separated ints to quickly remove doubles later
        # order points to sort them no matter their order
        list_1 = [min(filtered[i][1][0], corresponding_vertices[0]), max(
            filtered[i][1][0], corresponding_vertices[0])]
        list_2 = [min(filtered[i][1][1], corresponding_vertices[1]), max(
            filtered[i][1][1], corresponding_vertices[1])]

        list_of_2_points.append(list_1)
        list_of_2_points.append(list_2)

        # TODO: get points on the next faces if we want to slide to the outside later (as an option)

    # remove doubles in the vertices
    # since the vertices are sorted we can use the first one as the unique key
    unique_points = list({i[0]: i for i in list_of_2_points}.values())
    num_unique_points = len(unique_points)

    # start mesh modifications
    new_mesh = bmesh.from_edit_mesh(data)

    # ensure bmesh internal index tables are fresh
    new_mesh.verts.ensure_lookup_table()

    for i in range(num_unique_points):
        points = unique_points[i]
        center_point = new_mesh.verts[points[0]].co.lerp(
            new_mesh.verts[points[1]].co, 0.5)

        bmesh.ops.scale(new_mesh, vec=[adjustment, adjustment, adjustment],
                        space=mathutils.Matrix.Translation(-center_point), verts=[new_mesh.verts[points[0]], new_mesh.verts[points[1]]])

    # sync up bmesh and mesh
    bmesh.update_edit_mesh(data)
    new_mesh.free()
    return {'FINISHED'}


def get_corresponding_indices(face_verts, selected_verts):
    """
    Find the opposite vertices for the 2 selected vertices in the face
    :return: tuple
    """
    firt_selected_index = face_verts.index(selected_verts[0])
    second_selected_index = face_verts.index(selected_verts[1])

    first_corresponding_index = firt_selected_index + \
        1 if (firt_selected_index +
              1) % QUAD != second_selected_index else firt_selected_index - 1
    second_corresponding_index = second_selected_index + \
        1 if (second_selected_index +
              1) % QUAD != firt_selected_index else second_selected_index - 1

    return (face_verts[first_corresponding_index % QUAD], face_verts[second_corresponding_index % QUAD])


class NlBuildEnd(bpy.types.Operator):
    """Builds a quad ending to two parallel loops based on the vertex or edge selection"""

    bl_label = "Build End"
    bl_idname = "mesh.nicheloops_build_end"
    bl_options = {'REGISTER', 'UNDO'}

    slide_edge: bpy.props.FloatProperty(
        name="Slide Edge", default=0.5, min=0, max=1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    @staticmethod
    def build_end(data, all_verts_indices, selected_verts_indices, slide_edge, report):
        """
        Core of the Build Corner logic
        :return: nothing
        """

        # start mesh modifications
        new_mesh = bmesh.from_edit_mesh(data)

        # ensure bmesh internal index tables are fresh
        new_mesh.verts.ensure_lookup_table()

        # connect the ngon into triangles
        first_selected_index = list(all_verts_indices).index(
            selected_verts_indices[0])
        second_selected_index = list(all_verts_indices).index(
            selected_verts_indices[1])

        # find opposite vertex
        # if the next vertex (+1) is not the second vertex, then the opposite will be at +2
        # otherwise it will be at -2

        first_tri_index = first_selected_index + \
            2 if (first_selected_index +
                  1) % HEXAGON != second_selected_index else first_selected_index - 2
        second_tri_index = second_selected_index + \
            2 if (second_selected_index +
                  1) % HEXAGON != first_selected_index else second_selected_index - 2

        first_tri_index %= HEXAGON
        second_tri_index %= HEXAGON

        first_edge = bmesh.ops.connect_verts(new_mesh, verts=[
            new_mesh.verts[selected_verts_indices[0]], new_mesh.verts[all_verts_indices[first_tri_index]]])
        second_edge = bmesh.ops.connect_verts(new_mesh, verts=[
            new_mesh.verts[selected_verts_indices[1]], new_mesh.verts[all_verts_indices[second_tri_index]]])

        new_edges = first_edge["edges"] + second_edge["edges"]

        # subdivide the newly created edges
        output = bmesh.ops.subdivide_edges(
            new_mesh, edges=new_edges, cuts=1, use_only_quads=True)

        # move the newly created vertices to the center based on the parameter
        new_verts = output["geom_inner"][: 2]

        # if the operation was made on incompatible starting points
        # there might not be 2 points created
        # in that case stop here. result is not as expected anyways
        if len(new_verts) != 2:
            report({'WARNING'},
                   "Could not build end. Result might not be as expected")
            bmesh.update_edit_mesh(data)
            new_mesh.free()
            return {'FINISHED'}

        center_point = (new_verts[0].co + new_verts[1].co) / 2

        bmesh.ops.scale(new_mesh, vec=[slide_edge, slide_edge, slide_edge],
                        space=mathutils.Matrix.Translation(-center_point), verts=new_verts)

        # sync up bmesh and mesh
        bmesh.update_edit_mesh(data)
        new_mesh.free()
        return {'FINISHED'}

    def execute(self, context):
        obj = context.active_object
        return nl_build_core(NlBuildType.end, obj, self.slide_edge, self.report)

    def invoke(self, context, event):
        return self.execute(context)


class NlBuildCorner(bpy.types.Operator):
    """Builds a quad corner based on the vertex selection to make an edge-loop turn"""

    bl_label = "Build Corner"
    bl_idname = "mesh.nicheloops_build_corner"
    bl_options = {'REGISTER', 'UNDO'}

    slide_vertex: bpy.props.FloatProperty(
        name="Slide Vertex", default=0.5, min=0, max=1)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    @staticmethod
    def build_corner(data, all_verts_indices, selected_verts_indices, middle_vertex_index, slide_vertex, report):
        """
        Core of the Build Corner logic
        :return: nothing
        """

        # start mesh modifications
        new_mesh = bmesh.from_edit_mesh(data)

        # ensure bmesh internal index tables are fresh
        new_mesh.verts.ensure_lookup_table()

        # retrieve opposie vertex using index of vertex between selected
        opposite_vertex_index = all_verts_indices[(
            middle_vertex_index + 3) % HEXAGON]

        # connect the selected vertices into a triangle
        first_edge = bmesh.ops.connect_verts(new_mesh, verts=[
            new_mesh.verts[selected_verts_indices[0]], new_mesh.verts[selected_verts_indices[1]]])

        # subdivide the newly created edge
        output = bmesh.ops.subdivide_edges(
            new_mesh, edges=first_edge["edges"], cuts=1, use_only_quads=True)

        # retrieve vertex created from subdivide
        created_vertex = output["geom_inner"][0]

        # ensure bmesh internal index tables are fresh
        # we modified the vertices, and we will need to access them again
        new_mesh.verts.ensure_lookup_table()

        # connect created vertex with opposite vertex
        bmesh.ops.connect_verts(
            new_mesh, verts=[created_vertex, new_mesh.verts[opposite_vertex_index]])

        # move the newly created vertices to the center based on the parameter
        # center of scale is the vertex between the 2 selected vertices
        center_point = new_mesh.verts[opposite_vertex_index].co

        bmesh.ops.scale(new_mesh, vec=[slide_vertex, slide_vertex, slide_vertex],
                        space=mathutils.Matrix.Translation(-center_point), verts=[created_vertex])

        # sync up bmesh and mesh
        bmesh.update_edit_mesh(data)
        new_mesh.free()
        return {'FINISHED'}

    def execute(self, context):
        obj = context.active_object
        return nl_build_core(NlBuildType.corner, obj, self.slide_vertex, self.report)

    def invoke(self, context, event):
        return self.execute(context)


class NlAdjustLoops(bpy.types.Operator):
    """Select two or more parallel edges and adjust the value to change the distance between them"""

    bl_label = "Adjust Loops"
    bl_idname = "mesh.nicheloops_adjust_loops"
    bl_options = {'REGISTER', 'UNDO'}

    adjustment: bpy.props.FloatProperty(
        name="Adjustment", default=1, min=0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    def execute(self, context):
        obj = context.active_object

        return nl_adjust_loops(obj, self.adjustment, self.report)

    def invoke(self, context, event):
        return self.execute(context)


class NlAdjustAdjacentLoops(bpy.types.Operator):
    """Select one or more edges and adjust the value to change the positions of the edges on either side of the selected loop"""

    bl_label = "Adjust Adjacent Loops"
    bl_idname = "mesh.nicheloops_adjust_adjacent_loops"
    bl_options = {'REGISTER', 'UNDO'}

    adjustment: bpy.props.FloatProperty(
        name="Adjustment", default=1, min=0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.mode == 'EDIT'

    @staticmethod
    def adjust_adjacent_loops(obj, adjustment, report):
        """
        Core of the Adjust adjacent loops logic
        :return: nothing
        """
        data = obj.data

        # we need to switch from Edit mode to Object mode so the selection gets updated
        # https://blender.stackexchange.com/questions/1412/efficient-way-to-get-selected-vertices-via-python-without-iterating-over-the-en
        bpy.ops.object.mode_set(mode='OBJECT')

        selected_edges = [i for i in data.edges if i.select is True]
        num_selected_edges = len(selected_edges)

        # back to whatever mode we were in
        bpy.ops.object.mode_set(mode='EDIT')

        # we need at least 1 edge
        if num_selected_edges < 1:
            report({'ERROR_INVALID_INPUT'}, "At least 1 edge must be selected")
            return {'CANCELLED'}

        # convert edges to vertices tuple
        verts = [tuple(selected_edges[i].vertices)
                 for i in range(num_selected_edges)]

        # for each polygon, find if they use one of the selected edges
        num_polygons = len(data.polygons)
        linked_faces = [None] * num_selected_edges
        # optimisation: store how many faces have been found alreadyx
        # that way we can ignore the checks once we reach 2
        num_found_faces = [0] * num_selected_edges

        for i in range(num_polygons):
            edge_keys = list(data.polygons[i].edge_keys)

            # ignore non quads
            if len(edge_keys) != QUAD:
                continue

            for j in range(num_selected_edges):
                if num_found_faces[j] >= 2:
                    continue

                # only check for reversed keys if we didn't find it in standard order
                # do this here separately in order to overwrite the data with the reversed keys
                # if they are the ones that worked, without having to re-reverse them later
                is_in_edge_keys = verts[j] in edge_keys
                reversed_keys = reverse(
                    verts[j]) if not is_in_edge_keys else None
                is_in_edge_reversed_keys = reversed_keys in edge_keys if not is_in_edge_keys else False

                if is_in_edge_keys or is_in_edge_reversed_keys:
                    num_found_faces[j] += 1

                    if (linked_faces[j] is None):
                        linked_faces[j] = [i]
                    else:
                        linked_faces[j].append(i)

                if is_in_edge_reversed_keys:
                    # store the reversed keys as the normal keys
                    verts[j] = reversed_keys

        # remove edges that don't have 2 connected faces
        # go backwards through the array because we might remove items
        # TODO: maybe refactor into creating new array to gain perf ?
        for i in reversed(range(num_selected_edges)):
            if num_found_faces[i] != 2:
                del num_found_faces[i]
                del linked_faces[i]
                del verts[i]

        # recompute the number of selected edges
        num_selected_edges = len(verts)

        # create tuple of 3 points
        list_of_3_points = []

        # find the corresponding vertices on both associated faces
        for i in range(num_selected_edges):
            face_0_corresponding_vertices = get_corresponding_indices(
                list(data.polygons[linked_faces[i][0]].vertices), verts[i])
            face_1_corresponding_vertices = get_corresponding_indices(
                list(data.polygons[linked_faces[i][1]].vertices), verts[i])

            # store the lists as strings of space separated ints to quickly remove doubles later
            list_1 = [face_0_corresponding_vertices[0],
                      verts[i][0], face_1_corresponding_vertices[0]]
            list_2 = [face_0_corresponding_vertices[1],
                      verts[i][1], face_1_corresponding_vertices[1]]

            list_of_3_points.append(list_1)
            list_of_3_points.append(list_2)

            # TODO: get points on the next faces if we want to slide to the outside later (as an option)

        # remove doubles in the vertices
        # only check the middle vertex to see if we have doubles
        unique_points = list({i[1]: i for i in list_of_3_points}.values())
        num_unique_points = len(unique_points)

        # start mesh modifications
        new_mesh = bmesh.from_edit_mesh(data)

        # ensure bmesh internal index tables are fresh
        new_mesh.verts.ensure_lookup_table()

        for i in range(num_unique_points):
            points = unique_points[i]
            center_point = new_mesh.verts[points[1]].co

            bmesh.ops.scale(new_mesh, vec=[adjustment, adjustment, adjustment], space=mathutils.Matrix.Translation(
                -center_point), verts=[new_mesh.verts[points[0]], new_mesh.verts[points[2]]])

        # sync up bmesh and mesh
        bmesh.update_edit_mesh(data)
        new_mesh.free()
        return {'FINISHED'}

    def execute(self, context):
        obj = context.active_object
        return self.adjust_adjacent_loops(obj, self.adjustment, self.report)

    def invoke(self, context, event):
        return self.execute(context)


# menu containing all tools
class VIEW3D_MT_edit_mesh_nicheloops(bpy.types.Menu):
    bl_label = "Niche Loops"

    def draw(self, context):
        flow = self.layout

        flow.operator("mesh.nicheloops_build_end")
        flow.operator("mesh.nicheloops_build_corner")
        flow.operator("mesh.nicheloops_adjust_loops")
        flow.operator("mesh.nicheloops_adjust_adjacent_loops")


# panel containing all tools
class VIEW3D_PT_tools_nicheloops(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_label = "Niche Loops"
    bl_idname = "VIEW3D_PT_tools_nicheloops"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Edit'
    bl_context = "mesh_edit"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        flow = self.layout.column()

        col1 = flow.column(align=True)
        col1.operator("mesh.nicheloops_build_end")
        col1.operator("mesh.nicheloops_build_corner")

        col2 = flow.column(align=True)
        col2.operator("mesh.nicheloops_adjust_loops")
        col2.operator("mesh.nicheloops_adjust_adjacent_loops")


# draw function for integration in menus
def menu_func(self, context):
    self.layout.menu("VIEW3D_MT_edit_mesh_nicheloops")
    self.layout.separator()


# define classes for registration
classes = (
    NlBuildEnd,
    NlBuildCorner,
    NlAdjustLoops,
    NlAdjustAdjacentLoops,
    VIEW3D_MT_edit_mesh_nicheloops,
    VIEW3D_PT_tools_nicheloops,
)


def register():
    """
    Method called by Blender when enabling the add-on
    :return: nothing
    """
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)


def unregister():
    """
    Method called by Blender when disabling or removing the add-on
    :return: nothing
    """
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


# if the script is run directly, register it
if __name__ == "__main__":
    register()
