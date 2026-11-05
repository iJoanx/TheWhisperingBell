"""Rebuild ONE crossing (fast: nothing else is touched) and save what's around it for checking.

    py sewer_one.py                    rebuilds SL_287_Crossing
    py sewer_one.py SL_051_Crossing    any other node

Also writes Content/Python/one_<label>.json: the new crossing mesh, the tunnel pieces placed
around it (within RADIUS) and the viewport camera, so the meeting of crossing and tunnels can be
checked outside Unreal. Log: one_out.txt."""
import os
import sys
import json
import time
import importlib
import traceback
import unreal
import sewer_builder as sb

LABEL = "SL_287_Crossing"
RADIUS = 1600.0
PY_DIR = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(PY_DIR, "one_out.txt")


def log(msg):
    open(out, "a").write(msg + "\n")
    unreal.log("ONE " + msg)


def _tris(mesh):
    res = []
    for t in range(sb.gs("get_num_triangle_i_ds")(mesh)):
        vs = sb._tri_positions(mesh, t)
        if vs:
            res.append([[round(v.x, 2), round(v.y, 2), round(v.z, 2)] for v in vs])
    return res


def _uvs(mesh):
    """per triangle: [uv0 x3, uv1 x3, material id] (texture coords, atlas cell, slot)"""
    res = []
    n_sets = sb.gs("get_num_uv_sets")(mesh)
    for t in range(sb.gs("get_num_triangle_i_ds")(mesh)):
        if not sb._tri_positions(mesh, t):
            continue
        row = []
        for k in range(2):
            uv = sb.gs("get_triangle_u_vs")(mesh, k, t) if n_sets > k else None
            uv = [u for u in uv if isinstance(u, unreal.Vector2D)] if isinstance(uv, tuple) else []
            row.append([[round(u.x, 4), round(u.y, 4)] for u in uv])
        mid = sb.gs("get_triangle_material_id")(mesh, t)
        row.append(int(mid[0] if isinstance(mid, tuple) else mid))
        res.append(row)
    return res


def _sm_tris(sm, cache):
    name = sm.get_path_name()
    if name not in cache:
        m = sb._new_mesh()
        sb.gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                            unreal.GeometryScriptMeshReadLOD())
        cache[name] = _tris(m)
    return name


def run(label):
    open(out, "w").write("one started: %s\n" % label)
    t0 = time.time()
    importlib.reload(sb)
    sb.HUB_FLOW_VERSION = 2
    sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewerDefinitive"
    sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
    sb.use_definitive()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    log("level %s: %d sewer nodes" % (world.get_name() if world else "?", len(nodes)))
    node = next((n for n in nodes if n.get_actor_label() == label), None)
    if node is None:                     # also find it by its number alone, or by any actor label
        num = "".join(ch for ch in label if ch.isdigit())
        cands = [n for n in nodes if num and ("_%s_" % num) in n.get_actor_label() + "_"]
        if not cands:
            cands = [a for a in sb._actors() if a.get_actor_label() == label]
        if len(cands) == 1:
            node = cands[0]
            label = node.get_actor_label()
            log("using %s" % label)
    if node is None:
        log("no node called %s (some node names: %s)" % (label, ", ".join(sorted(n.get_actor_label() for n in nodes)[:8])))
        return
    edges, per_node = sb._gather(nodes, [])
    conns = per_node.get(node.get_path_name(), [])
    mesh = sb._build_node_mesh(node, conns)
    path = "%s/SM_SewerNode_%s" % (sb.GENERATED_FOLDER, sb._safe(label))
    sm = sb._bake(mesh, path, list(sb._SLOTS), simple=False)
    comp = node.get_component_by_class(unreal.StaticMeshComponent)
    comp.modify()
    comp.set_static_mesh(sm)
    try:
        comp.set_editor_property("override_materials", [])
    except Exception:
        pass
    log("rebuilt %s in %.1f s" % (label, time.time() - t0))
    if sb.SIMPLE_COLLISION:
        import sewer_boxcol
        importlib.reload(sewer_boxcol)
        sewer_boxcol.apply_level_later(only=[node.get_path_name()])

    # what's around it, for checking: the crossing (world space) + every tunnel piece nearby
    loc = node.get_actor_location()
    xf = node.get_actor_transform()
    ctris = []
    for t in _tris(mesh):
        ctris.append([[p.x, p.y, p.z] for p in
                      (unreal.MathLibrary.transform_location(xf, unreal.Vector(*v)) for v in t)])
    cache, inst = {}, []
    for a in sb._actors():
        if a.get_actor_label() != sb.NETWORK_LABEL:
            continue
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            cm = c.get_editor_property("static_mesh")
            if cm is None or "Water" in c.get_name():
                continue
            for i in range(c.get_instance_count()):
                it = c.get_instance_transform(i, True)
                if (it.translation - loc).length() > RADIUS:
                    continue
                q = it.rotation
                inst.append({"mesh": _sm_tris(cm, cache), "comp": c.get_name(),
                             "t": [it.translation.x, it.translation.y, it.translation.z],
                             "q": [q.x, q.y, q.z, q.w],
                             "s": [it.scale3d.x, it.scale3d.y, it.scale3d.z]})
    cam = None
    try:
        r_ = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_level_viewport_camera_info()
        cl, cr = r_[-2], r_[-1]
        cam = {"loc": [cl.x, cl.y, cl.z], "pitch": cr.pitch, "yaw": cr.yaw, "roll": cr.roll}
    except Exception:
        pass
    cs = [{"h": [c["h"].x, c["h"].y, c["h"].z], "d": [c["d"].x, c["d"].y, c["d"].z], "ptype": c["ptype"],
           "lead": c["lead"], "pitch": c["pitch"], "mirror": bool(c.get("mirror"))} for c in conns]
    try:
        cuv = _uvs(mesh)
    except Exception:
        cuv = None
        log("uvs not read:\n" + traceback.format_exc())
    json.dump({"label": label, "loc": [loc.x, loc.y, loc.z], "conns": cs, "crossing": ctris, "crossing_uv": cuv,
               "slots": [str(x) for x in sb._SLOTS],
               "meshes": cache, "instances": inst, "camera": cam},
              open(os.path.join(PY_DIR, "one_%s.json" % label), "w"))
    log("saved %d crossing triangles, %d tunnel pieces nearby, camera %s" % (len(ctris), len(inst), cam))


try:
    arg = next((a for a in sys.argv[1:] if a.strip()), None)
    if arg and arg.isdigit():
        arg = "SL_%03d_Crossing" % int(arg)
    run(arg or LABEL)
except Exception:
    log(traceback.format_exc())
