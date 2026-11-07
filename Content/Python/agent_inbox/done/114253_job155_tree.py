import unreal
OUT = r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump155.txt"
W = unreal.load_asset('/Game/Menus/WB_SetTime')
pref = W.get_path_name() + ':WidgetTree.'
ws = [w for w in unreal.ObjectIterator(unreal.Widget) if w.get_path_name().startswith(pref)]
out = ["widgets in tree: %d" % len(ws)]
def slotinfo(w):
    s = w.get_editor_property('slot')
    if s is None: return "root/no slot"
    par = s.get_editor_property('parent')
    r = "%s in %s(%s)" % (s.get_class().get_name(), par.get_name() if par else None, par.get_class().get_name() if par else None)
    if isinstance(s, unreal.CanvasPanelSlot):
        ld = s.get_editor_property('layout_data')
        o = ld.get_editor_property('offsets'); a = ld.get_editor_property('anchors'); al = ld.get_editor_property('alignment')
        r += " off(L%.0f T%.0f R%.0f B%.0f) anch(%.2f,%.2f-%.2f,%.2f) align(%.2f,%.2f) auto=%s z=%s" % (o.left, o.top, o.right, o.bottom, a.minimum.x, a.minimum.y, a.maximum.x, a.maximum.y, al.x, al.y, s.get_auto_size(), s.get_z_order())
    else:
        for p in ('padding', 'horizontal_alignment', 'vertical_alignment', 'size'):
            try: r += " %s=%s" % (p, s.get_editor_property(p))
            except Exception: pass
    return r
for w in ws:
    line = "%-30s %-18s %s" % (w.get_name(), w.get_class().get_name(), slotinfo(w))
    if isinstance(w, unreal.TextBlock):
        f = w.get_editor_property('font')
        fam = f.get_editor_property('font_object'); 
        line += " | text=%r font=%s size=%s typeface=%s color=%s just=%s" % (str(w.get_editor_property('text'))[:40], fam.get_name() if fam else None, f.get_editor_property('size'), f.get_editor_property('typeface_font_name'), w.get_editor_property('color_and_opacity').get_editor_property('specified_color'), w.get_editor_property('justification'))
    out.append(line)
open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("ok", len(ws))
