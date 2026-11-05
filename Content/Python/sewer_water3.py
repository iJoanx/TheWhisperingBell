"""Fast water test for 3-way crossings: rebakes ONLY the crossing water of the open sewer level
(nothing else is rebuilt) and photographs those crossings from above.

    py sewer_water3.py            new: one smooth flow, ripples only scaled evenly (no streaks)
    py sewer_water3.py streams    separate streams meeting in seams
    py sewer_water3.py old        the previous smooth fill (streaky), to compare

Pictures: Saved/NodeShots/<Level>_3way_<new|streams|old>. Log: water3_out.txt.
Set ONLY to a list of labels to do just those (faster)."""
import os
import sys
import time
import builtins
import importlib
import traceback
import unreal

ONLY = None            # e.g. ["SL_051_Crossing", "SL_048_Crossing"]; None = every 3-way crossing
ARMS = (3, 4)          # which crossings: number of passages (4-ways: only 1-to-3 / 3-to-1 ones change)

PY_DIR = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(PY_DIR, "water3_out.txt")


def log(msg):
    open(out, "a").write(msg + "\n")
    unreal.log("WATER3 " + msg)


def run():
    open(out, "w").write("water3 started\n")
    args = sys.argv[1:]
    mode = "old" if "old" in args else "streams" if "streams" in args else "new"
    import sewer_builder as sb
    importlib.reload(sb)
    sb.HUB_FLOW_VERSION = 2
    sb.HUB_V2_THREE = {"old": None, "streams": "streams", "new": "conformal"}[mode]
    sb.GENERATED_FOLDER = "/Game/Sewers/Generated/SewerDefinitive"
    sb.WATER_MATERIAL = "/Game/Sewers/Materials/MI_SewerWaterV2_Opaque"
    sb.use_definitive()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    t0 = time.time()
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    edges, per_node = sb._gather(nodes, [])
    sb._FLOW_CACHE.clear()
    sb._flow_field(edges)
    done = []
    with unreal.ScopedSlowTask(len(nodes), "Crossing water...") as task:
        task.make_dialog(True)
        for n in nodes:
            task.enter_progress_frame(1)
            if task.should_cancel():
                break
            if not sb._is_crossing(sb._node_type(n)):
                continue
            conns = per_node.get(n.get_path_name(), [])
            label = n.get_actor_label()
            if ONLY is not None:
                if label not in ONLY:
                    continue
            elif len(conns) not in ARMS:
                continue
            try:
                sb._hub_water_asset(n, conns)
                done.append(label)
            except Exception:
                log("%s failed:\n%s" % (label, traceback.format_exc()))
    kinds = {}
    for k in sb._HUB_V2_ITERS:
        k = k[0] if isinstance(k, tuple) and k and k[0] == "conformal" else k
        if isinstance(k, str):
            kinds[k] = kinds.get(k, 0) + 1
    log("%s water rebaked for %d crossings in %.0f s %s" % (mode.upper(), len(done), time.time() - t0, kinds))
    builtins._NODESHOTS_LIB = True
    try:
        import sewer_nodeshots
        importlib.reload(sewer_nodeshots)
    finally:
        builtins._NODESHOTS_LIB = False
    sewer_nodeshots.run(only=set(done), sub="%s_3way_%s" % (world.get_name(), mode))
    log("pictures done (see nodeshots_out.txt)")


try:
    run()
except Exception:
    log(traceback.format_exc())
