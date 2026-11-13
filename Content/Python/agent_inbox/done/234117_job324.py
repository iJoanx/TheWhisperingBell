import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
out = []
def done():
    open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump324.txt", "w", encoding="utf-8").write("\n".join(out))
H = '/Game/ThirdPerson/Blueprints/CBP_PC_Hope.CBP_PC_Hope'
OLD = H + ':Get Teleport Trace'
NEW = H + ':GetTeleportTraceCapsule'
VN = 'UseCapsuleTeleportTrace'
for f in ():
    out.append("== %s %s" % (f, (getattr(BT, f).__doc__ or '')[:700]))
# 1) bool switch variable
ok = False
for args in ({'blueprint': {'refPath': H}, 'name': VN, 'type_name': 'bool'},):
    try: call('add_variable', args); ok = True; out.append("add_variable ok with " + str(list(args))); break
    except Exception as e: out.append("add_variable try %s: %s" % (list(args), str(e)[:300]))
if not ok: done(); raise SystemExit
for f, a in (('set_variable_category', {'blueprint': {'refPath': H}, 'variable_name': VN, 'category': 'Teleport'}), ('set_variable_instance_editable', {'blueprint': {'refPath': H}, 'variable_name': VN, 'instance_editable': True})):
    try: call(f, a)
    except Exception as e: out.append("%s err %s" % (f, str(e)[:300]))
try: compile_bp(H)
except Exception as e: out.append("compile1 " + str(e)[:300])
# default = true on the class defaults
try:
    bp = unreal.load_asset(H)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    cdo.set_editor_property(VN, True); out.append("default set: " + str(cdo.get_editor_property(VN)))
except Exception as e: out.append("default err " + str(e)[:300])
# 2) at the start of the old function: if UseCapsuleTeleportTrace -> call the new one, else the old chain
entry = OLD + '.K2Node_FunctionEntry_0'
tr = OLD + '.K2Node_CallFunction_3'
ep = info(entry)['position']
call('break_pins', {'output_pin': pin(entry, 'then', 'out')['pin_id'], 'input_pin': pin(tr, 'execute', 'in')['pin_id']})
t = [c.get('type_id') if isinstance(c, dict) else c for c in types(OLD, VN)]
out.append("getter types " + str(t))
gt = next((c for c in t if c.startswith('Variables|') and c.split('|')[-1] == 'Get' + VN), None)
br = node(OLD, 'Utilities|FlowControl|Branch', ep['x'] + 200, ep['y'] - 250)
gv = node(OLD, gt, ep['x'], ep['y'] - 150)
cn = node(OLD, 'CallFunction|GetTeleportTraceCapsule', ep['x'] + 450, ep['y'] - 300)
connect(pin(entry, 'then', 'out'), pin(br, 'execute', 'in'))
connect(info(gv)['output_pins'][0], pin(br, 'Condition', 'in'))
connect(pin(br, 'then', 'out'), pin(cn, 'execute', 'in'))
connect(pin(br, 'else', 'out'), pin(tr, 'execute', 'in'))
try: call('arrange_nodes', {'nodes': [{'refPath': r} for r in nodes(NEW)]})
except Exception as e: out.append("arrange err " + str(e)[:300])
try: compile_bp(H); out.append("compile OK")
except Exception as e: out.append("compile FAIL " + str(e)[:800])
d = str(call('read_graph_dsl', {'graph': {'refPath': OLD}}))
out.append("=== old fn head\n" + d[:600] + "\n...\n" + d[-700:])
done(); print("ok")
