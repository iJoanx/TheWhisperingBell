import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal, time
out = []
try:
    for n in ('BP_Master_PC', 'CBP_PC_Hope', 'CBP_PC_GolKosh'):
        compile_bp('/Game/ThirdPerson/Blueprints/%s.%s' % (n, n))
        cmc = unreal.get_default_object(unreal.load_class(None, '/Game/ThirdPerson/Blueprints/%s.%s_C' % (n, n))).get_editor_property('character_movement')
        out.append("%s trust=%s/%s" % (n, cmc.get_editor_property('ignore_client_movement_error_checks_and_correction'), cmc.get_editor_property('server_accept_client_authoritative_position')))
except Exception as e: out.append("compile err %s" % str(e)[:200])
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opt = unreal.AssetRegistryDependencyOptions()
DN = '/Game/NightSky/BP_DayNightCycle'
out.append("DN referencers: %s" % [str(r) for r in ar.get_referencers(DN, opt)])
out.append("DN deps: %s" % [str(d) for d in ar.get_dependencies(DN, opt) if str(d).startswith('/Game')])
bp = unreal.load_asset(DN)
try: out.append("interfaces: %s" % [str(i) for i in bp.get_editor_property('implemented_interfaces')])
except Exception as e: out.append("iface err %s" % e)
for x in infos(nodes(DN + '.BP_DayNightCycle:EventGraph')):
    if 'GetTime' in x['type_id'] or 'Event' in x['type_id']:
        out.append("event node %s %s" % (x['node']['refPath'].split('.')[-1], x['type_id']))
for g in call('list_graphs', {'blueprint': {'refPath': DN + '.BP_DayNightCycle'}}):
    pass
# timeline component settings
cdo = unreal.get_default_object(unreal.load_class(None, DN + '.BP_DayNightCycle_C'))
out.append("DN CDO replicates=%s always_relevant=%s" % (cdo.get_editor_property('replicates'), cdo.get_editor_property('always_relevant')))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump95.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
