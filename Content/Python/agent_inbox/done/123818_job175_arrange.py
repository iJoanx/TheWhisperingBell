import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
import editor_toolset.toolsets.blueprint as BM
out = []
targets = {
    'BP_DayNightCycle': ['GetSunYear', 'SetNetTime', 'ResyncTime', 'OnRep_NetTime', 'UpdateShadowCaster'],
    'BP_Master_PC': ['ServerApplyTime'],
    'CBP_PC_Hope': ['DoTeleport'],
    'CBP_Familiar_Bolita': ['FlyVertical'],
    'ABP_Unarmed3': ['CalcFlySpeed'],
    'BP_WB_Sewer_Entry': ['ApplySewerView'],
}
ar = unreal.AssetRegistryHelpers.get_asset_registry()
def find_bp(name):
    res = ar.get_assets(unreal.ARFilter(package_paths=['/Game'], recursive_paths=True))
    for a in res:
        if str(a.asset_name) == name: return str(a.package_name) + '.' + name
    return None
allassets = None
for bpn, fns in targets.items():
    bp = find_bp(bpn)
    if not bp: out.append("no asset %s" % bpn); continue
    graphs = {g['refPath'].split(':')[-1]: g['refPath'] for g in call('list_graphs', {'blueprint': {'refPath': bp}})}
    unreal.load_asset(bp.split('.')[0]).modify()
    for fn in fns:
        if fn not in graphs: out.append("%s: no graph %s" % (bpn, fn)); continue
        objs = [unreal.find_object(None, r) for r in nodes(graphs[fn])]
        objs = [o for o in objs if o]
        for o in objs: o.modify()
        try: BM.arrange_nodes(objs); out.append("arranged %s:%s (%d nodes)" % (bpn, fn, len(objs)))
        except Exception as e: out.append("arrange err %s:%s %s" % (bpn, fn, str(e)[:400]))
# WB_SetTime: only the EventTick chain inside EventGraph
WB = '/Game/Menus/WB_SetTime.WB_SetTime'
G = WB + ':EventGraph'
xs = {x['node']['refPath']: x for x in infos(nodes(G))}
tick = [r for r, x in xs.items() if 'EventTick' in x['type_id'] or 'Tick' in x['type_id']]
out.append("tick nodes: %s" % [(r.split(':')[-1], xs[r]['type_id']) for r in tick])
if tick:
    comp, stack = set(), list(tick)
    while stack:
        r = stack.pop()
        if r in comp or r not in xs: continue
        comp.add(r)
        for p in xs[r]['input_pins'] + xs[r]['output_pins']:
            for c in (p.get('connected_pins') or []): stack.append(c['node']['refPath'])
    objs = [unreal.find_object(None, r) for r in comp]
    unreal.load_asset('/Game/Menus/WB_SetTime').modify()
    for o in objs: o.modify()
    try: BM.arrange_nodes([o for o in objs if o]); out.append("arranged WB tick chain (%d nodes)" % len(objs))
    except Exception as e: out.append("WB arrange err %s" % str(e)[:400])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump175.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
