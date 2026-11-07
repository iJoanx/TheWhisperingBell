import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
BP = '/Game/Menus/WB_SetTime.WB_SetTime'
W = unreal.load_asset('/Game/Menus/WB_SetTime')
pref = W.get_path_name() + ':WidgetTree'
tree = unreal.find_object(None, pref)
ws = {w.get_name(): w for w in unreal.ObjectIterator(unreal.Widget) if w.get_path_name().startswith(pref + '.')}
vb = ws['VerticalBox_21']
if 'YearNameText' in ws:
    out.append("YearNameText already exists, skipping widget creation")
else:
    W.modify(); tree.modify(); vb.modify()
    src = ws['MonthSupertypeText']
    tb = unreal.new_object(unreal.TextBlock, outer=tree, name='YearNameText')
    f = src.get_editor_property('font')
    tb.set_editor_property('font', f)
    tb.set_editor_property('color_and_opacity', src.get_editor_property('color_and_opacity'))
    tb.set_editor_property('justification', unreal.TextJustify.CENTER)
    tb.set_editor_property('text', unreal.Text('Year of Three Ships Sailing'))
    after = ['MonthText', 'MonthSupertypeText', 'HorizontalBox', 'HolidaysHBox']
    saved = []
    for n in after:
        c = ws[n]; s = c.get_editor_property('slot')
        saved.append((c, s.get_editor_property('padding'), s.get_editor_property('horizontal_alignment'), s.get_editor_property('vertical_alignment'), s.get_editor_property('size')))
        c.modify()
        vb.remove_child(c)
    ns = vb.add_child_to_vertical_box(tb)
    ns.set_editor_property('horizontal_alignment', unreal.HorizontalAlignment.H_ALIGN_CENTER)
    ns.set_editor_property('vertical_alignment', unreal.VerticalAlignment.V_ALIGN_CENTER)
    ns.set_editor_property('padding', unreal.Margin(0, 0, 0, 12))
    for c, pad, ha, va, sz in saved:
        s = vb.add_child_to_vertical_box(c)
        s.set_editor_property('padding', pad); s.set_editor_property('horizontal_alignment', ha)
        s.set_editor_property('vertical_alignment', va); s.set_editor_property('size', sz)
    out.append("VB order now: %s" % [vb.get_child_at(i).get_name() for i in range(vb.get_children_count())])
for vn, tn, ct in (('YearNames', 'string', 'ARRAY'), ('ShownYear', 'int', None)):
    existing = [p for p in dir(unreal.load_object(None, BP + '_C').get_default_object()) if p == vn.lower() or p == vn]
    a = {'blueprint': {'refPath': BP}, 'name': vn, 'type_name': tn}
    if ct: a['container_type'] = ct
    try: out.append("add %s: %s" % (vn, call('add_variable', a)))
    except Exception as e: out.append("add %s err %s" % (vn, str(e)[:400]))
try: out.append("compile: %s" % str(compile_bp(BP))[:1500])
except Exception as e: out.append("compile err %s" % str(e)[:800])
G = BP + ':EventGraph'
for flt in ('YearNameText', 'ShownYear', 'YearNames', 'WidgetFromName', 'GetWidget'):
    try: out.append("%s -> %s" % (flt, [x.get('type_id') for x in types(G, flt)][:10]))
    except Exception as e: out.append("%s ERR %s" % (flt, str(e)[:200]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump161.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
