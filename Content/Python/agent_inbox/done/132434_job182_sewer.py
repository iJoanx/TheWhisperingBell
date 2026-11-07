import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets(unreal.ARFilter(package_paths=['/Game'], recursive_paths=True))
def find_bp(name):
    for a in assets:
        if str(a.asset_name) == name: return str(a.package_name) + '.' + name
bp = find_bp('BP_WB_Sewer_Entry')
out.append("BP %s" % bp)
for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
    try: out.append("=== %s\n%s" % (g['refPath'].split(':')[-1], call('read_graph_dsl', {'graph': {'refPath': g['refPath']}})))
    except Exception as e: out.append("=== %s ERR %s" % (g['refPath'], e))
cdo = unreal.get_default_object(unreal.load_object(None, bp + '_C'))
for p in ('replicates', 'always_relevant', 'net_load_on_client', 'net_update_frequency'):
    try: out.append("%s=%s" % (p, cdo.get_editor_property(p)))
    except Exception as e: out.append("%s err" % p)
# who else references the sewer layers / tags
for nm in ('BP_Master_PC',):
    b = find_bp(nm)
    for g in call('list_graphs', {'blueprint': {'refPath': b}}):
        try:
            d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
            for blk in d.split("\n\n"):
                if any(k in blk for k in ('Sewer', 'DataLayer', 'RDL_', 'Teleport', 'UseEntry')):
                    out.append("--- %s %s\n%s" % (nm, g['refPath'].split(':')[-1], blk[:3000]))
        except Exception as e: out.append("err %s" % e)
# data layer assets' runtime state settings
for a in assets:
    if str(a.asset_name).startswith('RDL_'):
        try:
            o = a.get_asset()
            out.append("DL asset %s type=%s" % (a.asset_name, o.get_editor_property('data_layer_type')))
        except Exception as e: out.append("DL %s err %s" % (a.asset_name, e))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump182.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
