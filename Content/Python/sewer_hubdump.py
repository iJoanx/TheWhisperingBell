"""Water test data: the exact inputs of every crossing's water in the open sewer level, saved to
hubdump_<Level>.json (no meshes are built or changed, takes seconds).

    py sewer_hubdump.py
"""
import os
import json
import importlib
import traceback
import unreal
import sewer_builder as sb

PY_DIR = os.path.dirname(os.path.abspath(__file__))
out_log = os.path.join(PY_DIR, "hubdump_out.txt")


def _v(p):
    return [p.x, p.y, p.z]


def _plain(x):
    if hasattr(x, "x") and hasattr(x, "y") and hasattr(x, "z"):
        return _v(x)
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x


def run():
    open(out_log, "w").write("hubdump started\n")
    importlib.reload(sb)
    sb.HUB_FLOW_VERSION = 2
    sb.use_definitive()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    edges, per_node = sb._gather(nodes, [])
    sb._FLOW_CACHE.clear()
    sb._flow_field(edges)
    caught = {}
    cur = {}

    def capture(node, verts, tris, arms):
        caught[cur["label"]] = {"verts": [_v(p) for p in verts], "tris": [list(t) for t in tris],
                                "arms": [_plain(a) for a in arms]}
        return None
    sb._hub_water_v2 = capture
    for n in nodes:
        if not sb._is_crossing(sb._node_type(n)):
            continue
        conns = per_node.get(n.get_path_name(), [])
        if not conns:
            continue
        cur["label"] = n.get_actor_label()
        try:
            sb._hub_water_asset(n, conns)
            Sn, Tn = sb._FLOW_FIELD["nodes"].get(n.get_path_name(), (0.0, 0.0))
            caught[cur["label"]]["node"] = [Sn, Tn]
        except Exception:
            open(out_log, "a").write("%s:\n%s" % (cur["label"], traceback.format_exc()))
    path = os.path.join(PY_DIR, "hubdump_%s.json" % world.get_name())
    json.dump(caught, open(path, "w"))
    open(out_log, "a").write("%d crossings -> %s\n" % (len(caught), path))


try:
    run()
except Exception:
    open(out_log, "a").write(traceback.format_exc())
