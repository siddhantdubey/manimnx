import networkx as nx
import numpy as np

from manimlib.imports import *

# outsource exact details of node and edge creation to user
# provide convenience functions for moving nodes and edges
# get item and stuff similar to nx but return the vmobject instead of the key


def get_dot_node(n, G):
    """Create a dot node with a given color.

    Uses RED by default.

    Parameters
    ----------
    n :
        Node key for graph G.

    Returns
    -------
    Dot
        The Dot VMobject.

    """
    n = G.node[n]
    node = Dot(color=n.get('color', RED))
    x, y = n['pos']
    node.move_to(x*RIGHT + y*UP)
    return node


def get_line_edge(ed, G):
    """Create a line edge using the color of node n1.

    Uses WHITE by default.

    Parameters
    ----------
    ed:
        Edge key for the networkx graph G.

    Returns
    -------
    Line
        The Line VMobject.

    """
    n1 = G.node[ed[0]]
    n2 = G.node[ed[1]]
    x1, y1 = n1['pos']
    x2, y2 = n2['pos']
    start = x1*RIGHT + y1*UP
    end = x2*RIGHT + y2*UP
    return Line(start, end, color=n1.get('color', WHITE))


class ManimGraph(VGroup):
    """A manim VGroup which wraps a networkx Graph.

    Parameters
    ----------
    graph : networkx.Graph
        The graph to wrap.
    get_node : function (node, Graph) -> VMobject
        Create the VMobject for the given node key in the given Graph.
    get_edge : function (edge, Graph) -> VMobject
        Create the VMobject for the given edge key in the given Graph.

    Additional kwargs are passed to VGroup.

    Attributes
    ----------
    nodes : dict
        Dict mapping mob_id -> node mobject
    edges : dict
        Dict mapping mob_id -> edge mobject
    id_to_node: dict
        Dict mapping mob_id -> node key
    id_to_edge: dict
        Dict mapping mob_id -> edge key


    """

    def __init__(self, graph,
                 get_node=get_dot_node,
                 get_edge=get_line_edge, **kwargs):
        super().__init__(**kwargs)
        self.graph = graph
        self.get_edge = get_edge
        self.get_node = get_node

        self.nodes = {}
        self.edges = {}

        self.id_to_node = {}
        self.id_to_edge = {}

        n = list(self.graph.nodes())[0]
        scale = np.array([6.5, 3.5])
        if 'pos' not in self.graph.node[n].keys():
            unscaled_pos = nx.spring_layout(self.graph)
            positions = {k: v*scale for k, v in unscaled_pos.items()}
            for node, pos in positions.items():
                self.graph.node[node]['pos'] = pos

        self.count = 0
        self._add_nodes()
        self._add_edges()

    def _add_nodes(self):
        """Create nodes using get_node and add to submobjects and nodes dict."""
        for node in self.graph.nodes:
            n = self.get_node(node, self.graph)
            self.graph.nodes[node]['mob_id'] = self.count
            self.nodes[self.count] = n
            self.id_to_node[self.count] = node
            self.add(n)
            self.count += 1

    def _add_edges(self):
        """Create edges using get_edge and add to submobjects and edges dict."""
        for edge in self.graph.edges:
            self.graph.edges[edge]['mob_id'] = self.count
            e = self.get_edge(edge, self.graph)
            self.edges[self.count] = e
            self.id_to_edge[self.count] = edge
            self.add_to_back(e)
            self.count += 1


# %%


class TransformAndRemoveSource(Transform):
    def clean_up_from_scene(self, scene):
        super().clean_up_from_scene(scene)
        scene.remove(self.mobject)

# TODO: move this to manimnx package
# %% TODO: take in custom transform for edges and nodes


def transform_graph(mng, G):
    """Transforms the graph in ManimGraph mng to the graph G.

    This is better than just using Transform because it keeps edges and
    nodes which don't change stationary, unlike Transform which mixes up
    everything.

    For any new mob_ids in G, or any nodes or edges without a mob_id, they
    are assumed to be new objects which are to be created. If they contain
    an expansion attribute, they will be created and transformed from those
    mob_ids in the expansion. Otherwise, they will be faded in.

    Missing mob_ids in G are dealt with in two ways:
    If they are found in the contraction attribute of the node or edge, the
    mobjects are first transformed to the contracted node then faded away. If
    not found in any contraction, they are faded away. (Note that this means
    that any older contractions present in G do not affect the animation in any
    way.)

    Cannot contract to new nodes/edges and expand from new nodes/edges.
    # TODO: consider changing this behavior


    Parameters
    ----------
    mng : ManimGraph
        The ManimGraph object to transform.
    G : Graph
        The graph containing attributes of the target graph.

    Returns
    -------
    list of Animations
        List of animations to show the transform.

    """
    anims = []
    id_to_mobj = {**mng.nodes, **mng.edges}

    old_ids = list(mng.nodes.keys()) + list(mng.edges.keys())
    new_ids = []

    # just copying the loops for edges and nodes, not worth functioning that
    # i think
    # ------- ADDITIONS AND DIRECT TRANSFORMS ---------
    # NODES
    for node, node_data in G.nodes.items():
        new_node = mng.get_node(node, G)
        if 'mob_id' not in node_data.keys():
            G.nodes[node]['mob_id'] = mng.count
            mng.count += 1

        mob_id = node_data['mob_id']
        new_ids.append(mob_id)

        if mob_id in old_ids:
            # if mng.graph.nodes[mng.id_to_node[mob_id]] != node_data:
            anims.append(Transform(mng.nodes[mob_id], new_node))
        else:
            if 'expansion' in node_data.keys():
                objs = [id_to_mobj[o['mob_id']]
                        for o in node_data['expansion'].values()]
                anims.append(TransformFromCopy(VGroup(*objs), new_node))
            else:
                anims.append(FadeIn(new_node))

            mng.nodes[mob_id] = new_node
            mng.add(new_node)
            mng.id_to_node[mob_id] = node

    # EDGES
    for edge, edge_data in G.edges.items():
        new_edge = mng.get_edge(edge, G)
        if 'mob_id' not in edge_data.keys():
            G.edges[edge]['mob_id'] = mng.count
            mng.count += 1

        mob_id = edge_data['mob_id']
        new_ids.append(mob_id)

        if mob_id in old_ids:
            # only transform if new is different from old
            # TODO: how to check this properly, and is it really needed?

            # if mng.graph.edges[mng.id_to_edge[mob_id]] != edge_data:
            anims.append(Transform(mng.edges[mob_id], new_edge))
        else:
            if 'expansion' in edge_data.keys():
                objs = [id_to_mobj[o['mob_id']]
                        for o in edge_data['expansion'].values()]
                anims.append(TransformFromCopy(VGroup(*objs), new_edge))
            else:
                anims.append(FadeIn(new_edge))

            mng.edges[mob_id] = new_edge
            mng.add_to_back(new_edge)
            mng.id_to_edge[mob_id] = edge

    # --------- REMOVALS AND CONTRACTIONS ----------
    # NODES
    for node, node_data in mng.graph.nodes.items():
        mob_id = node_data['mob_id']
        if mob_id in new_ids:
            continue

        contracts_to = []
        for node2, node_datfg in G.nodes.items():
            for c2 in node_datfg.get('contraction', {}).values():
                if mob_id == c2['mob_id']:
                    contracts_to.append(id_to_mobj[node_datfg['mob_id']])
                    break

        mobj = id_to_mobj[mob_id]
        if len(contracts_to) == 0:
            anims.append(FadeOut(mobj))
        else:
            # anims.append(Succession(Transform(mobj, VGroup(*contracts_to)),
            #                         FadeOut(mobj)))
            anims.append(TransformAndRemoveSource(mobj, VGroup(*contracts_to)))

        # dont actually remove so that the edges in the back remain in the
        # back while transforming. this might bite later though
        # mng.remove(mobj)
        del mng.nodes[mob_id]
        del mng.id_to_node[mob_id]

    # EDGES
    for edge, edge_data in mng.graph.edges.items():
        mob_id = edge_data['mob_id']
        if mob_id in new_ids:
            continue

        contracts_to = []
        for edge2, edge_datfg in G.edges.items():
            for c2 in edge_datfg.get('contraction', {}).values():
                if mob_id == c2['mob_id']:
                    contracts_to.append(id_to_mobj[edge_datfg['mob_id']])
                    break

        mobj = id_to_mobj[mob_id]
        if len(contracts_to) == 0:
            anims.append(FadeOut(mobj))
        else:
            anims.append(TransformAndRemoveSource(mobj, VGroup(*contracts_to)))

        # mng.remove(mobj)
        del mng.edges[mob_id]
        del mng.id_to_edge[mob_id]

    mng.graph = G
    return anims
