"""Trial run of a full sewer layout (from your Blender layout) in its own level.
    import importlib, sewer_layout_trial; importlib.reload(sewer_layout_trial); sewer_layout_trial.run()
Data: import/sewer_layout.json  (nodes: id/type/x/y in cm, edges: a/b/passage type)
"""
import json, os, time
import unreal

PY_DIR = os.path.dirname(os.path.abspath(__file__))
LEVEL = "/Game/Sewers/Maps/SewerTrial"
PREFIX = "SL_"
Z = 0.0


def load(name="sewer_layout.json"):
    return json.load(open(os.path.join(PY_DIR, "import", name)))


def open_level(level=LEVEL):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.save_current_level()
    if unreal.EditorAssetLibrary.does_asset_exist(level):
        les.load_level(level)
    else:
        les.new_level(level)
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        sun = eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 5000), unreal.Rotator(0, -50, 30))
        sun.set_actor_label("Trial_Sun")
        sky = eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 5000))
        sky.set_actor_label("Trial_Sky")


def spawn(data):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label().startswith(PREFIX):
            eas.destroy_actor(a)
    cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/Sewers/BP_SewerNode")
    actors = {}
    for n in data["nodes"]:
        a = eas.spawn_actor_from_class(cls, unreal.Vector(n["x"], n["y"], Z + n.get("z", 0.0)))
        a.set_actor_label("%s%03d_%s" % (PREFIX, n["id"], n["type"]))
        a.set_folder_path("SewerTrial/" + n["type"])
        a.set_editor_property("NodeType", n["type"])
        actors[n["id"]] = a
    links = {}
    for e in data["edges"]:
        prop = "Passage12To" if e["p"] == "P12" else "Passage20To"
        links.setdefault((e["a"], prop), []).append(actors[e["b"]])
    for (aid, prop), targets in links.items():
        actors[aid].set_editor_property(prop, targets)
    return actors


def run(cell_size=5000.0, build=True, name="sewer_layout.json", level=LEVEL):
    """   sewer_layout_trial.run(name="sewertest_layout.json", level="/Game/Sewers/Maps/SewerTest2")"""
    import sewer_builder
    data = load(name)
    open_level(level)
    t0 = time.time()
    actors = spawn(data)
    unreal.log("TRIAL spawned %d nodes, %d passages in %.1fs" % (len(actors), len(data["edges"]), time.time() - t0))
    if build:
        sewer_builder.CULL_CELL_SIZE = cell_size
        t1 = time.time()
        sewer_builder.build()
        unreal.log("TRIAL build took %.1f s" % (time.time() - t1))
        open(os.path.join(PY_DIR, "trial_out.txt"), "w").write("build %.1f s, nodes %d, passages %d" %
                                                               (time.time() - t1, len(actors), len(data["edges"])))


# --------------------------------------------------------------------------- from Blender
# In Blender (Python console):  exec(open(r"<Zippy>/Content/Python/import/blender_marks.py").read())
#   -> writes import/blender_layout.json (points incl. height, edges, vertex groups Junction/Shaft/12/20)
# In UE:  py import importlib,sewer_layout_trial;importlib.reload(sewer_layout_trial);sewer_layout_trial.from_blender()

def convert(src="blender_layout.json", dst="sewertest_layout.json", merge=50.0):
    """Blender layout -> node/passage list: Junction/Shaft from vertex groups, P20 when both ends
    are in group "20", Crossing where passages cross or a passage end touches another passage,
    other points with one passage = End, more = Crossing. Heights come along (Blender Z)."""
    import collections, math
    d = load(src)
    W = [(x * 100.0, -y * 100.0, z * 100.0) for (x, y, z) in d["verts"]]
    rep = list(range(len(W)))
    for i in range(len(W)):
        for j in range(i):
            if rep[j] == j and math.hypot(W[i][0] - W[j][0], W[i][1] - W[j][1]) < merge:
                rep[i] = j
                break
    grp = {}
    for i, g in enumerate(d["groups"]):
        grp.setdefault(rep[i], {}).update(g)

    def etype(a, b):
        ga, gb = grp[a], grp[b]
        if "20" in ga and "20" in gb:
            if "12" in ga and "12" in gb:
                return "P20" if ga["20"] + gb["20"] >= ga["12"] + gb["12"] else "P12"
            return "P20"
        return "P12"
    E = {}
    for a, b in d["edges"]:
        a, b = rep[a], rep[b]
        if a != b:
            E[tuple(sorted((a, b)))] = etype(a, b)
    nodes = {i: list(W[i]) for i in set(rep)}
    El = [(a, b, p) for (a, b), p in E.items()]
    nid = [max(nodes) + 1]

    def node_at(p):
        for k, n in nodes.items():
            if math.hypot(n[0] - p[0], n[1] - p[1]) < merge:
                return k
        nodes[nid[0]] = list(p)
        grp[nid[0]] = {}
        nid[0] += 1
        return nid[0] - 1
    splits = collections.defaultdict(list)
    for i in range(len(El)):
        a, b, _ = El[i]
        A, B = nodes[a], nodes[b]
        rx, ry = B[0] - A[0], B[1] - A[1]
        for j in range(i + 1, len(El)):
            c, e, _ = El[j]
            if len({a, b, c, e}) < 4:
                continue
            C, D = nodes[c], nodes[e]
            sx, sy = D[0] - C[0], D[1] - C[1]
            den = rx * sy - ry * sx
            if abs(den) < 1e-9:
                continue
            qx, qy = C[0] - A[0], C[1] - A[1]
            t, u = (qx * sy - qy * sx) / den, (qx * ry - qy * rx) / den
            if 1e-6 < t < 1 - 1e-6 and 1e-6 < u < 1 - 1e-6:
                k = node_at((A[0] + rx * t, A[1] + ry * t, A[2] + (B[2] - A[2]) * t))
                splits[i].append((t, k))
                splits[j].append((u, k))
    for n, p in list(nodes.items()):
        for k, (a, b, _) in enumerate(El):
            if n in (a, b):
                continue
            A, B = nodes[a], nodes[b]
            abx, aby = B[0] - A[0], B[1] - A[1]
            L2 = abx * abx + aby * aby
            t = ((p[0] - A[0]) * abx + (p[1] - A[1]) * aby) / L2 if L2 else 0
            if 0.01 < t < 0.99 and math.hypot(A[0] + abx * t - p[0], A[1] + aby * t - p[1]) < merge:
                splits[k].append((t, n))
    seen, out = set(), []
    for k, (a, b, p) in enumerate(El):
        ch = [a] + [n for t, n in sorted(splits[k])] + [b]
        ch = [x for i, x in enumerate(ch) if i == 0 or x != ch[i - 1]]
        for x, y in zip(ch, ch[1:]):
            key = tuple(sorted((x, y)))
            if key not in seen:
                seen.add(key)
                out.append((x, y, p))
    deg = collections.Counter()
    for x, y, _ in out:
        deg.update((x, y))
    nl, remap = [], {}
    for k in sorted(nodes):
        if not deg[k]:
            continue
        g = grp.get(k, {})
        t = "Junction" if "Junction" in g else "Shaft" if "Shaft" in g else ("End" if deg[k] == 1 else "Crossing")
        remap[k] = len(nl)
        x, y, z = nodes[k]
        nl.append({"id": len(nl), "type": t, "x": round(x, 1), "y": round(y, 1), "z": round(z, 1)})
    data = {"nodes": nl, "edges": [{"a": remap[a], "b": remap[b], "p": p} for a, b, p in out]}
    json.dump(data, open(os.path.join(PY_DIR, "import", dst), "w"))
    unreal.log("Sewer layout: %d nodes, %d passages -> %s" % (len(nl), len(out), dst))
    return data


def from_blender(level="/Game/Sewers/Maps/SewerTest2", build=True):
    convert()
    run(name="sewertest_layout.json", level=level, build=build)


LIGHT_PREFIX = "SL_Light_"


def add_lights(height_crossing=300.0, height_room=500.0, height_end=250.0, intensity=8.0, radius=1500.0):
    """Every light in the level becomes movable, and each sewer node gets a movable point light
    near its top (replaces lights made by an earlier call)."""
    import sewer_builder as sb
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    for a in actors:
        if a.get_actor_label().startswith(LIGHT_PREFIX):
            eas.destroy_actor(a)
    n_mov = 0
    for a in eas.get_all_level_actors():
        for c in a.get_components_by_class(unreal.LightComponent):
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            n_mov += 1
    n_new = 0
    for n in [a for a in eas.get_all_level_actors() if sb._is_node(a)]:
        nt = sb._node_type(n)
        h = height_end if sb._is_end(nt) else (height_crossing if sb._is_crossing(nt) else height_room)
        lt = eas.spawn_actor_from_class(unreal.PointLight, n.get_actor_location() + unreal.Vector(0, 0, h))
        lt.set_actor_label(LIGHT_PREFIX + n.get_actor_label())
        lt.set_folder_path("SewerTrial/Lights")
        c = lt.get_component_by_class(unreal.PointLightComponent)
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        c.set_intensity(intensity)
        c.set_attenuation_radius(radius)
        c.set_light_color(unreal.LinearColor(1.0, 0.82, 0.6, 1.0))
        n_new += 1
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    msg = "lights: %d made movable, %d node lights added" % (n_mov, n_new)
    open(os.path.join(PY_DIR, "scan_out.txt"), "w").write(msg)
    return msg
