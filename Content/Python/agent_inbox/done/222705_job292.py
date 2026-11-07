import sys, importlib, traceback, time
import unreal
out = []
t0 = time.time()
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    import sewer_boxcol as bc
    # no level save from Python: the user saves with Save All
    if not getattr(bc, "_agent_nosave", False):
        _orig_apply = bc.apply_level
        def _apply_nosave(only=None, save=True):
            return _orig_apply(only=only, save=False)
        bc.apply_level = _apply_nosave
        bc._agent_nosave = True
    n, failed = sb.rebake_crossings()
    out.append("rebaked %d crossings in %.0f s, failed %d" % (n, time.time() - t0, len(failed)))
    out += ["FAILED " + f for f in failed]
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump292.txt", "w", encoding="utf-8").write("\n".join(out))
