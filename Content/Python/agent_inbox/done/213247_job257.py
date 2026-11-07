import sys, importlib, traceback
import unreal
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    warns = []
    orig = unreal.log_warning
    sb.unreal.log_warning = lambda m: (warns.append(str(m)), orig(m))
    try:
        n, failed = sb.rebake_crossings(["SL_303_Crossing"])
    finally:
        sb.unreal.log_warning = orig
    out.append("rebaked %d failed %s" % (n, failed))
    out.append("channel stats %s snap %s" % (sb.CHANNEL_STATS, sb.SNAP_STATS))
    out += ["warn: " + w for w in warns]
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump257.txt", "w", encoding="utf-8").write("\n".join(out))
