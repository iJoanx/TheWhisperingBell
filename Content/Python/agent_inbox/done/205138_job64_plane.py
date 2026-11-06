import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, os, re
ar = unreal.AssetRegistryHelpers.get_asset_registry()
hits = [a for a in ar.get_assets(unreal.ARFilter(package_paths=["/Game"], recursive_paths=True)) if str(a.asset_name) == "BP_PlaneOperator"]
for a in hits:
    p = str(a.package_name) + "." + str(a.asset_name)
    print("asset", p)
    try: print("compile:", compile_bp(p))
    except Exception as e: print("compile err", str(e)[:2000])
    deps = ar.get_dependencies(a.package_name, unreal.AssetRegistryDependencyOptions())
    print("deps:", [str(d) for d in deps][:40])
    for g in call('list_graphs', {'blueprint': {'refPath': p}}):
        print("graph", g['refPath'])
# recent log lines mentioning it
log = os.path.join(unreal.Paths.project_log_dir(), "TheWhisperingBell.log")
try:
    L = open(log, encoding="utf-8", errors="ignore").read().splitlines()
    m = [l for l in L if "PlaneOperator" in l]
    print("log lines:", len(m)); print("\n".join(m[-25:]))
except Exception as e: print("log err", e)
