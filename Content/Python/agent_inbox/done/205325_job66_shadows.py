import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
out = []
DN = '/Game/NightSky/BP_DayNightCycle.BP_DayNightCycle'
US = DN + ':UpdateSun'
g = call('add_function_graph', {'blueprint': {'refPath': DN}, 'graph_name': 'UpdateShadowCaster'})['refPath']
call('write_graph_dsl', {'graph': {'refPath': g}, 'code': '''(fn UpdateShadowCaster ()
  (bind up (< (.z (Transformation|GetForwardVector (Variables|Default|GetDirectionalLight))) 0.0))
  (Rendering|Components|Light|SetCastShadows (Variables|Default|GetDirectionalLight) up)
  (Rendering|Components|Light|SetCastShadows (Variables|Default|GetMoon) (not up)))'''})
out.append(str(call('read_graph_dsl', {'graph': {'refPath': g}})))
# insert after the live SetWorldRotation(DirectionalLight)
sw = US + '.K2Node_CallFunction_11'
nxt = US + '.K2Node_MacroInstance_2'
then = pin(sw, 'then', 'out'); ex = pin(nxt, 'exec', 'in')
already = [c for c in then.get('connected_pins', []) if 'UpdateShadowCaster' in str(info(c['node']['refPath'])['type_id'])]
if not already:
    call('break_pins', {'output_pin': then['pin_id'], 'input_pin': ex['pin_id']})
    p = info(sw)['position']
    c = node(US, 'CallFunction|UpdateShadowCaster', p['x'] + 300, p['y'] + 200)
    connect(pin(sw, 'then', 'out'), pin(c, 'execute', 'in'))
    connect(pin(c, 'then', 'out'), pin(nxt, 'exec', 'in'))
out.append("compile: %s" % (compile_bp(DN),))
out.append(dumpnodes(US).split('K2Node_CallFunction_11')[1][:400])
print("\n".join(out))
