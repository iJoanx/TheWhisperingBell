import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
bp = '/Game/Menus/WB_SetTime.WB_SetTime'
for g in call('list_graphs', {'blueprint': {'refPath': bp}}):
    try:
        d = str(call('read_graph_dsl', {'graph': {'refPath': g['refPath']}}))
        out.append("=== GRAPH %s\n%s" % (g['refPath'].split(':')[-1], d))
    except Exception as e: out.append("=== GRAPH %s ERR %s" % (g['refPath'], e))
W = unreal.load_asset('/Game/Menus/WB_SetTime')
pref = W.get_path_name() + ':WidgetTree'
tree = unreal.find_object(None, pref)
out.append("TREE %s %s" % (tree, tree.get_class().get_name() if tree else None))
ws = {w.get_name(): w for w in unreal.ObjectIterator(unreal.Widget) if w.get_path_name().startswith(pref + '.')}
for pn in ('VerticalBox_21', 'HorizontalBox_2', 'HorizontalBox'):
    p = ws[pn]
    out.append("%s children: %s" % (pn, [p.get_child_at(i).get_name() for i in range(p.get_children_count())]))
yt = ws['YearTextBox']
try:
    st = yt.get_editor_property('widget_style')
    ts = st.get_editor_property('text_style')
    f = ts.get_editor_property('font')
    out.append("YearTextBox font %s size %s" % (f.get_editor_property('font_object'), f.get_editor_property('size')))
except Exception as e: out.append("yt style err %s" % e)
for p in ('widget_variable_name_to_guid_map',):
    try: out.append("%s: %s" % (p, W.get_editor_property(p)))
    except Exception as e: out.append("%s err %s" % (p, e))
out.append("PanelWidget methods: %s" % [m for m in dir(unreal.PanelWidget) if 'child' in m])
out.append("VBox methods: %s" % [m for m in dir(unreal.VerticalBox) if 'child' in m])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump158.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
