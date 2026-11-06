import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
A = '/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed2.ABP_Unarmed2'
AG = A + ':AnimGraph'
rigs = set()
for x in infos(nodes(AG)):
    if x['type_id'] == 'Misc.|ControlRig':
        r = x['node']['refPath']
        o = unreal.load_object(None, r)
        props = [p for p in dir(o) if not p.startswith('_')]
        out.append("CR node %s" % r)
        try:
            n = o.get_editor_property('node')
            for p in ('control_rig_class', 'b_reset_input_pose_to_initial', 'b_transfer_input_pose', 'b_transfer_input_curves', 'alpha', 'lod_threshold', 'b_set_ref_pose_from_skeleton', 'input_mapping', 'output_mapping'):
                try:
                    v = n.get_editor_property(p); out.append("   %s = %s" % (p, v))
                    if p == 'control_rig_class' and v: rigs.add(v.get_path_name())
                except Exception as e: out.append("   %s ?" % p)
        except Exception as e: out.append("  node err %s ; props %s" % (e, [p for p in props if 'node' in p or 'rig' in p.lower()]))
        for p_ in x['input_pins']:
            out.append("   pin %s = %s conn=%s" % (p_['name'], p_.get('default_value'), [c['node']['refPath'].split('.')[-1] for c in (p_.get('connected_pins') or [])]))
for rc in rigs:
    bp_path = rc.replace('_C', '').rsplit('.', 1)[0]
    out.append("== RIG %s" % bp_path)
    rb = unreal.load_asset(bp_path)
    try:
        models = [rb.get_model()]
        try: models = list(rb.get_all_models())
        except Exception: pass
        for m in models:
            ns = m.get_nodes()
            out.append("  graph %s (%d nodes)" % (m.get_node_path() if hasattr(m, 'get_node_path') else m.get_name(), len(ns)))
            for n in ns:
                t = n.get_node_title()
                out.append("    %s" % t)
    except Exception as e: out.append("  rig err %s" % e)
# where IKAlpha comes from
EGa = A + ':EventGraph'
d = call('read_graph_dsl', {'graph': {'refPath': EGa}})
out.append("== ABP_Unarmed2 EventGraph DSL\n" + str(d)[:3500])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump76.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
