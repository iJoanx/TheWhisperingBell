import sys, importlib, traceback, math
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    nodes = [a for a in sb._actors() if sb._is_node(a)]
    labels = [a.get_actor_label() for a in nodes if "315" in a.get_actor_label()]
    out.append("nodes with 315: %s" % [(l, sb._node_type([a for a in nodes if a.get_actor_label() == l][0])) for l in labels])
    _, per = sb._gather(nodes, [])
    for nd in [a for a in nodes if a.get_actor_label() in labels]:
        conns = sb._local_conns(nd, per[nd.get_path_name()])
        for k, c in enumerate(conns):
            out.append("  arm %d ang %.1f pitch %.2f lead %.1f ptype %s mirror %s" % (k, math.degrees(math.atan2(c["h"].y, c["h"].x)), c["pitch"], c["lead"], c["ptype"], c.get("mirror")))
        if sb._is_crossing(sb._node_type(nd)):
            out.append("  bend %s leaders %s mitres %s outer %s" % (bool(sb._bend_mitre(conns)), sb._through_leaders(conns), list(sb._crossing_mitres(conns).keys()), [(o[0], o[1]) for o in sb._outer_mitres(conns)]))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump306.txt", "w", encoding="utf-8").write("\n".join(out))
