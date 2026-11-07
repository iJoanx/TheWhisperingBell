import sys, importlib, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    _, per = sb._gather(nodes, [])
    nd = [a for a in nodes if a.get_actor_label() == "SL_315_Crossing"][0]
    orig = sb._unjitter_hub_walls
    import inspect
    for mode in ("current", "none"):
        if mode == "none":
            sb._unjitter_hub_walls = lambda mesh, conns, radius: 0
        sb._UV_TABLES.clear(); sb._OUTER.clear(); del sb._SLOTS[:]
        m = sb._build_node_mesh(nd, per[nd.get_path_name()])
        out.append("%s: walls %s vault %s channel %s tris %d" % (mode, sb.FIT_STATS, sb.VAULT_STATS, sb.CHANNEL_STATS, sb.gs("get_num_triangle_i_ds")(m)))
    sb._unjitter_hub_walls = orig
    # how far does the snap move things?
    sb._UV_TABLES.clear(); sb._OUTER.clear(); del sb._SLOTS[:]
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump313.txt", "w", encoding="utf-8").write("\n".join(out))
