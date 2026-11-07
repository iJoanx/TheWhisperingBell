import sys, importlib, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    labels = [a.get_actor_label() for a in nodes if "315" in a.get_actor_label()]
    out.append("nodes with 305: %s" % labels)
    _, per = sb._gather(nodes, [])
    nd = [a for a in nodes if a.get_actor_label() in labels and sb._is_crossing(sb._node_type(a))][0]
    conns = sb._local_conns(nd, per[nd.get_path_name()])
    for k, c in enumerate(conns):
        out.append("arm %d h(%.3f,%.3f) ang %.1f pitch %.2f lead %.1f ptype %s mirror %s" % (k, c["h"].x, c["h"].y, math.degrees(math.atan2(c["h"].y, c["h"].x)), c["pitch"], c["lead"], c["ptype"], c.get("mirror")))
    for k in range(len(conns)):
        for j in range(k + 1, len(conns)):
            out.append("  angle %d-%d: %.1f" % (k, j, sb._angle_between(conns[k], conns[j])))
    out.append("levels %s" % sb._crossing_levels(conns, sb.CROSSING_HUB))
    out.append("leaders %s" % sb._through_leaders(conns))
    warns = []
    orig = unreal.log_warning
    sb.unreal.log_warning = lambda m: (warns.append(str(m)), orig(m))
    try:
        n, failed = sb.rebake_crossings([nd.get_actor_label()])
    finally:
        sb.unreal.log_warning = orig
    out.append("rebaked %d failed %s; stats %s paint %s" % (n, failed, sb.CHANNEL_STATS, sb.PAINT_STATS))
    out += ["warn: " + w for w in warns]
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump315.txt", "w", encoding="utf-8").write("\n".join(out))
