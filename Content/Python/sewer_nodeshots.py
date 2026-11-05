"""Top-down picture of the water at every sewer node of the open level, one PNG per node, named
after the node (e.g. SL_012_Crossing.png), all in Saved/NodeShots/<LevelName>/.

    py sewer_nodeshots.py                      (every crossing)

Only the water is drawn (walls, walkways and ceilings are hidden), straight from above with an
orthographic camera, as plain base colour (no lighting), so the ripple pattern shows exactly as the
material makes it. Each picture covers SIZE_CM around the node (rooms get more)."""
import os
import struct
import time
import zlib
import traceback
import unreal

RES = 512               # pixels per side
SIZE_CM = 1600.0        # area covered around a crossing / end
ROOM_EXTRA_CM = 800.0   # junctions / shafts: wider
ABOVE_CM = 300.0        # camera height above the node
DEPTH_CM = 900.0        # how far down it looks (keeps tunnels far above / below out of the shot)
PREFIX = "SL_"

out_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nodeshots_out.txt")   # own log


def _log(msg):
    open(out_log, "a").write(msg + "\n")
    unreal.log("NODESHOTS " + msg)


def _write_png(path, w, h, pixels):
    """pixels: unreal.Color list (row by row). Written fully opaque (the capture's alpha is 0)."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        row = pixels[y * w:(y + 1) * w]
        for c in row:
            raw += bytes((c.r, c.g, c.b))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)


def run(only=None, sub=None):
    """only: node labels to shoot (default every crossing); sub: own folder name (default level)"""
    open(out_log, "w").write("nodeshots started\n")
    t0 = time.time()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    level_name = world.get_name()
    folder = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
                          "NodeShots", sub or level_name)
    os.makedirs(folder, exist_ok=True)

    # every water component in the level (passage strips + crossing water)
    water = []
    for a in actors:
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if "Water" in c.get_name():
                water.append(c)
    nodes = [a for a in actors if a.get_actor_label().startswith(PREFIX)
             and not a.get_actor_label().startswith(PREFIX + "Light")
             and a.get_class().get_name() != "PointLight"
             and a.get_actor_label().endswith("_Crossing")              # crossings only
             and (only is None or a.get_actor_label() in only)]
    _log("%d crossings, %d water components -> %s" % (len(nodes), len(water), folder))
    if not nodes or not water:
        return

    rt = unreal.RenderingLibrary.create_render_target2d(world, RES, RES,
                                                        unreal.TextureRenderTargetFormat.RTF_RGBA8)
    cap_actor = eas.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(0, 0, 0),
                                           unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
    cap_actor.set_actor_label("NodeShots_TEMP")
    cap = cap_actor.get_editor_property("capture_component2d")
    for prop, val in (("texture_target", rt),
                      ("capture_every_frame", False),
                      ("capture_on_movement", False),
                      ("projection_type", unreal.CameraProjectionMode.ORTHOGRAPHIC),
                      ("capture_source", unreal.SceneCaptureSource.SCS_BASE_COLOR),
                      ("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST),
                      ("auto_calculate_ortho_planes", False),
                      ("ortho_near_clip_plane", 0.0),
                      ("ortho_far_clip_plane", DEPTH_CM + ABOVE_CM)):
        try:
            cap.set_editor_property(prop, val)
        except Exception as e:  # noqa
            _log("note: %s not set (%s)" % (prop, e))
    for c in water:
        cap.show_only_component(c)

    done, errors = 0, 0
    try:
        for n in sorted(nodes, key=lambda a: a.get_actor_label()):
          try:
            label = n.get_actor_label()
            room = label.endswith("_Junction") or label.endswith("_Shaft")
            loc = n.get_actor_location()
            cap_actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + ABOVE_CM), False, False)
            cap_actor.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)   # looking straight down, +X up
            cap.set_editor_property("ortho_width", SIZE_CM + (ROOM_EXTRA_CM if room else 0.0))
            cap.capture_scene()
            px = list(unreal.RenderingLibrary.read_render_target(world, rt, False))
            if done == 0:
                lit = sum(1 for c in px[::97] if c.r + c.g + c.b > 6)
                _log("first picture: %d of %d sampled pixels not black" % (lit, len(px[::97])))
            if not px:
                raise RuntimeError("the capture returned no pixels")
            _write_png(os.path.join(folder, label + ".png"), RES, RES, px)
            done += 1
          except Exception:
            errors += 1
            if errors <= 3:
                _log("%s failed:\n%s" % (n.get_actor_label(), traceback.format_exc()))
    except Exception:
        _log(traceback.format_exc())
    finally:
        eas.destroy_actor(cap_actor)
    _log("saved %d pictures (%d failed) in %.0f s" % (done, errors, time.time() - t0))


import builtins
if not getattr(builtins, "_NODESHOTS_LIB", False):     # imported by another script: don't run
    run()
