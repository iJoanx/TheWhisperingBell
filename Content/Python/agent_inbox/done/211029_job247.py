import sys, importlib, traceback
out = []
try:
    sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python")
    import sewer_builder as sb
    importlib.reload(sb)
    n, failed = sb.rebake_crossings(["SL_303_Crossing"])
    out.append("rebaked %d failed %s" % (n, failed))
except Exception:
    out.append(traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump247.txt", "w", encoding="utf-8").write("\n".join(out))
