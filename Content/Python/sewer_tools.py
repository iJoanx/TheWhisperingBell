"""Editor helpers for laying out sewer nodes (Zippy).

Menu: Sewer (in the level editor's main menu bar, added by init_unreal.py at startup), or console:
    py import sewer_tools; sewer_tools.insert()          # 2 linked nodes selected -> node halfway between
    py sewer_tools.insert(3)                             # ... 3 evenly spaced nodes
    py sewer_tools.straighten()                          # selected node(s) snap onto the line of their 2 neighbours
All steps can be undone with Ctrl+Z.
"""
import unreal

NODE_CLASS = "/Game/Sewers/BP_SewerNode"
PROPS = ("Passage12To", "Passage20To")
DEFAULT_TYPE = "Crossing"


def _eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _is_node(a):
    try:
        a.get_editor_property("NodeType")
        return True
    except Exception:
        return False


def _selected_nodes():
    return [a for a in _eas().get_selected_level_actors() if _is_node(a)]


def _all_nodes():
    return [a for a in _eas().get_all_level_actors() if _is_node(a)]


def _links(a, prop):
    return list(a.get_editor_property(prop) or [])


def _find_link(a, b):
    """(owner, prop) of the passage between a and b, or None."""
    for owner, other in ((a, b), (b, a)):
        for prop in PROPS:
            if other in _links(owner, prop):
                return owner, prop
    return None


def _neighbours(n):
    """[(neighbour, prop)] for every passage touching n, whichever node stores it."""
    out = [(o, p) for p in PROPS for o in _links(n, p) if o]
    for a in _all_nodes():
        if a == n:
            continue
        for p in PROPS:
            if n in _links(a, p):
                out.append((a, p))
    return out


def _unique_label(base):
    used = {a.get_actor_label() for a in _eas().get_all_level_actors()}
    k = 1
    while "%s_%d" % (base, k) in used:
        k += 1
    return "%s_%d" % (base, k)


def _msg(text, title="Sewer"):
    unreal.log(text)
    unreal.EditorDialog.show_message(title, text, unreal.AppMsgType.OK)


def insert(count=1, node_type=DEFAULT_TYPE):
    """Select two nodes joined by a passage: puts `count` new nodes evenly on the straight line
    between them and splits the passage through them (same passage type)."""
    sel = _selected_nodes()
    if len(sel) != 2:
        _msg("Select exactly two sewer nodes that are joined by a passage.")
        return []
    a, b = sel
    link = _find_link(a, b)
    if not link:
        _msg("%s and %s are not joined by a passage." % (a.get_actor_label(), b.get_actor_label()))
        return []
    owner, prop = link
    first, last = (a, b) if owner == a else (b, a)       # keep the link direction
    pa, pb = first.get_actor_location(), last.get_actor_location()
    cls = unreal.EditorAssetLibrary.load_blueprint_class(NODE_CLASS)
    made = []
    with unreal.ScopedEditorTransaction("Insert sewer node"):
        for n in (first, last):
            n.modify()
        lst = _links(first, prop)
        lst.remove(last)
        prev = first
        for i in range(count):
            t = (i + 1.0) / (count + 1.0)
            loc = pa + (pb - pa) * t
            m = _eas().spawn_actor_from_class(cls, loc, first.get_actor_rotation())
            m.set_actor_label(_unique_label("SewerNode_" + node_type))
            try:
                m.set_folder_path(first.get_folder_path())
            except Exception:
                pass
            m.set_editor_property("NodeType", node_type)
            made.append(m)
            if prev == first:
                lst.append(m)
                first.set_editor_property(prop, lst)
            else:
                prev.set_editor_property(prop, _links(prev, prop) + [m])
            prev = m
        prev.set_editor_property(prop, _links(prev, prop) + [last])
    _eas().set_selected_level_actors(made)
    unreal.log("Sewer: inserted %d node(s) between %s and %s" % (count, first.get_actor_label(), last.get_actor_label()))
    return made


def straighten():
    """Each selected node with exactly two passages moves onto the straight line between its
    two neighbours (keeps its distance along the line; height follows the line)."""
    moved, skipped = 0, []
    with unreal.ScopedEditorTransaction("Straighten sewer nodes"):
        for n in _selected_nodes():
            nb = _neighbours(n)
            if len(nb) != 2:
                skipped.append(n.get_actor_label())
                continue
            pa, pb = nb[0][0].get_actor_location(), nb[1][0].get_actor_location()
            d = pb - pa
            L2 = d.dot(d)
            if L2 < 1.0:
                continue
            p = n.get_actor_location()
            t = max(0.05, min(0.95, (p - pa).dot(d) / L2))
            n.modify()
            n.set_actor_location(pa + d * t, False, False)
            moved += 1
    if skipped:
        _msg("Moved %d node(s). Skipped (need exactly 2 passages): %s" % (moved, ", ".join(skipped)))
    return moved


def build():
    import importlib, sewer_builder
    importlib.reload(sewer_builder)
    sewer_builder.build()


# --------------------------------------------------------------------------- menu
def register_menu():
    menus = unreal.ToolMenus.get()
    main = menus.find_menu("LevelEditor.MainMenu")
    if not main:
        return
    sub = main.add_sub_menu("Sewer", "", "SewerMenu", "Sewer", "Sewer node tools")
    items = [
        ("SewerInsert", "Insert node between selected", "Two joined nodes selected: adds a node halfway and splits the passage",
         "import sewer_tools; sewer_tools.insert()"),
        ("SewerInsert3", "Insert 3 nodes between selected", "Two joined nodes selected: adds 3 evenly spaced nodes",
         "import sewer_tools; sewer_tools.insert(3)"),
        ("SewerStraighten", "Straighten selected nodes", "Moves each selected node onto the line between its two neighbours",
         "import sewer_tools; sewer_tools.straighten()"),
        ("SewerBuild", "Build sewer", "Bakes all nodes and places the passages",
         "import sewer_tools; sewer_tools.build()"),
    ]
    for name, label, tip, cmd in items:
        e = unreal.ToolMenuEntry(name=name, type=unreal.MultiBlockType.MENU_ENTRY)
        e.set_label(label)
        e.set_tool_tip(tip)
        e.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", cmd)
        sub.add_menu_entry("Sewer", e)
    menus.refresh_all_widgets()
