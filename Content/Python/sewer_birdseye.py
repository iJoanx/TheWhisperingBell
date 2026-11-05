"""Bird's-eye picture of every crossing, junction and shaft of the open level: walls, walkways,
channel and water, seen straight from above with the ceilings cut away. One PNG per node, named
after it (SL_012_Crossing.png, SL_127_Shaft.png), in Saved/NodeShots/<LevelName>_birdseye/.

    py sewer_birdseye.py                 every crossing, junction and shaft
    py sewer_birdseye.py 287 51 127      just these (numbers or full names)
    py sewer_birdseye.py crossings       only crossings   (also: junctions, shafts, rooms)

Junctions and shafts get a wider picture (ROOM_EXTRA_CM) so the whole room and its doorways fit.
For each node a temporary cut-away copy is made of it and of everything around it (the
tunnel pieces and neighbouring nodes in the picture), sliced off CUT_CM above the crossing's
walkway, and photographed with the water; the copies are deleted afterwards. Nothing in the level
changes. Plain base colour (no lighting), like the Unlit view. Log: birdseye_out.txt."""
import os
import sys
import time
import importlib
import traceback
import unreal
import sewer_builder as sb

RES = 768               # pixels per side
SIZE_CM = 1600.0        # area covered around each crossing
ROOM_EXTRA_CM = 1000.0  # junctions / shafts: this much wider
KINDS = ("_Crossing", "_Junction", "_Shaft")
CUT_CM = 200.0          # ceilings, vaults and upper walls removed above this (cm above the walkway)
ABOVE_CM = 700.0        # camera height above the crossing
MATERIAL = "/Game/Level/Sewers/M_Master_Sewers_Inst"
PREFIX = "SL_"

PY_DIR = os.path.dirname(os.path.abspath(__file__))
out_log = os.path.join(PY_DIR, "birdseye_out.txt")
_STATE = {"handle": None}


def _log(msg):
    open(out_log, "a").write(msg + "\n")
    unreal.log("BIRDSEYE " + msg)


def _write_png(path, w, h, pixels):
    import struct
    import zlib
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for c in pixels[y * w:(y + 1) * w]:
            raw += bytes((c.r, c.g, c.b))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def _wanted(args):
    """(labels or numbers wanted or None for all, kinds wanted)"""
    names, nums, kinds = set(), set(), set()
    groups = {"crossings": ("_Crossing",), "junctions": ("_Junction",), "shafts": ("_Shaft",),
              "rooms": ("_Junction", "_Shaft")}
    for a in args:
        a = a.strip().strip(",")
        if a.lower() in groups:
            kinds.update(groups[a.lower()])
        elif a.isdigit():
            nums.add(int(a))
        elif a:
            names.add(a)
    return (names, nums) if (names or nums) else None, tuple(kinds) or KINDS


def _size(label):
    return SIZE_CM + (0.0 if label.endswith("_Crossing") else ROOM_EXTRA_CM)


def _pick(label, only, kinds):
    if not label.startswith(PREFIX) or not label.endswith(kinds):
        return False
    if only is None:
        return True
    names, nums = only
    num = label[len(PREFIX):].split("_")[0]
    return label in names or (num.isdigit() and int(num) in nums)


def run(args):
    open(out_log, "w").write("birdseye started\n")
    t0 = time.time()
    importlib.reload(sb)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    only, kinds = _wanted(args)
    folder = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
                          "NodeShots", world.get_name() + "_birdseye")
    os.makedirs(folder, exist_ok=True)
    mat = unreal.EditorAssetLibrary.load_asset(MATERIAL)

    # what can be in a picture: every node's own mesh, and every tunnel / end-cap piece
    water, pieces, node_meshes, crossings = [], [], [], []
    for a in actors:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if "Water" in c.get_name():
                water.append(c)
                continue
            sm = c.get_editor_property("static_mesh")
            if sm is None:
                continue
            if isinstance(c, unreal.InstancedStaticMeshComponent):
                if a.get_actor_label() != sb.NETWORK_LABEL:
                    continue
                for i in range(c.get_instance_count()):
                    pieces.append((sm, c.get_instance_transform(i, True)))
            elif sb._is_node(a):
                node_meshes.append((sm, c.get_world_transform()))
        label = a.get_actor_label()
        if sb._is_node(a) and _pick(label, only, kinds):
            crossings.append(a)
    crossings.sort(key=lambda a: a.get_actor_label())
    _log("%d nodes, %d tunnel pieces, %d node meshes, %d water components -> %s"
         % (len(crossings), len(pieces), len(node_meshes), len(water), folder))
    if not crossings:
        return

    cache = {}

    def dyn(sm):
        key = sm.get_path_name()
        if key not in cache:
            m = sb._new_mesh()
            sb.gs("copy_mesh_from_static_mesh")(sm, m, unreal.GeometryScriptCopyMeshFromAssetOptions(),
                                                unreal.GeometryScriptMeshReadLOD())
            cache[key] = m
        return cache[key]

    temps = []
    with unreal.ScopedSlowTask(len(crossings), "Bird's-eye pictures: cutting away the ceilings...") as task:
        task.make_dialog(True)
        for n in crossings:
            task.enter_progress_frame(1, n.get_actor_label())
            if task.should_cancel():
                break
            try:
                loc = n.get_actor_location()
                reach = _size(n.get_actor_label()) * 0.75 + 450.0   # anything whose pivot is this close may show
                m = sb._new_mesh()
                for sm, xf in pieces + node_meshes:
                    p = xf.translation
                    if abs(p.x - loc.x) > reach or abs(p.y - loc.y) > reach or abs(p.z - loc.z) > 1500.0:
                        continue
                    rel = unreal.Transform(location=p - loc, rotation=xf.rotation.rotator(), scale=xf.scale3d)
                    part = sb._new_mesh()          # each piece cut on its own (pieces overlap a little)
                    sb.gs("append_mesh")(part, dyn(sm), rel)
                    sb._subtract_halfspace(part, unreal.Vector(0, 0, CUT_CM), unreal.Vector(0, 0, 1))
                    sb.gs("append_mesh")(m, part, unreal.Transform())
                t = eas.spawn_actor_from_class(unreal.DynamicMeshActor, loc, unreal.Rotator(0, 0, 0))
                t.set_actor_label("BirdsEye_TEMP_" + n.get_actor_label())
                comp = t.get_component_by_class(unreal.DynamicMeshComponent)
                try:
                    comp.set_dynamic_mesh(m)
                except Exception:
                    target = comp.get_dynamic_mesh()
                    target.reset()
                    sb.gs("append_mesh")(target, m, unreal.Transform())
                for i in range(8):
                    try:
                        comp.set_material(i, mat)
                    except Exception:
                        break
                temps.append((n.get_actor_label(), loc, t, comp))
            except Exception:
                _log("%s: copy failed:\n%s" % (n.get_actor_label(), traceback.format_exc()))
    _log("cut-away copies made in %.0f s; taking the pictures in a moment" % (time.time() - t0))

    # the copies only show up in pictures after the editor has drawn a frame: shoot a bit later
    _STATE["wait"] = 3

    def shoot(dt):
        _STATE["wait"] -= 1
        if _STATE["wait"] > 0:
            return
        unreal.unregister_slate_post_tick_callback(_STATE["handle"])
        _STATE["handle"] = None
        t1 = time.time()
        done = errors = 0
        rt = unreal.RenderingLibrary.create_render_target2d(world, RES, RES,
                                                            unreal.TextureRenderTargetFormat.RTF_RGBA8)
        cam = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0),
                                         unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
        cam.set_actor_label("BirdsEye_TEMP_Camera")
        cap = cam.get_editor_property("capture_component2d")
        for prop, val in (("texture_target", rt), ("capture_every_frame", False), ("capture_on_movement", False),
                          ("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC),
                          ("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR),
                          ("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)):
            try:
                cap.set_editor_property(prop, val)
            except Exception as e:  # noqa
                _log("note: %s not set (%s)" % (prop, e))
        try:
            for label, loc, t, comp in temps:
                try:
                    try:
                        cap.clear_show_only_components()
                    except Exception:
                        cap.set_editor_property("show_only_components", [])
                    cap.show_only_component(comp)
                    for w in water:
                        cap.show_only_component(w)
                    cap.set_editor_property("ortho_width", _size(label))
                    cam.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + ABOVE_CM), False, False)
                    cam.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)
                    cap.capture_scene()
                    px = list(unreal.RenderingLibrary.read_render_target(world, rt, False))
                    if not px:
                        raise RuntimeError("the capture returned no pixels")
                    if done == 0:
                        lit = sum(1 for c in px[::97] if c.r + c.g + c.b > 6)
                        _log("first picture: %d of %d sampled pixels not black" % (lit, len(px[::97])))
                    _write_png(os.path.join(folder, label + ".png"), RES, RES, px)
                    done += 1
                except Exception:
                    errors += 1
                    if errors <= 3:
                        _log("%s failed:\n%s" % (label, traceback.format_exc()))
        finally:
            eas.destroy_actor(cam)
            for _, _, t, _ in temps:
                eas.destroy_actor(t)
        _log("saved %d pictures (%d failed) in %.0f s, copies removed" % (done, errors, time.time() - t1))

    if _STATE["handle"] is not None:
        unreal.unregister_slate_post_tick_callback(_STATE["handle"])
    _STATE["handle"] = unreal.register_slate_post_tick_callback(shoot)


try:
    run(sys.argv[1:])
except Exception:
    _log(traceback.format_exc())
