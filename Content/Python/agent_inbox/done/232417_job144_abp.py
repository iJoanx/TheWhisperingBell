import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
cls = unreal.load_class(None, '/Game/ThirdPerson/Blueprints/CBP_Familiar_Bolita.CBP_Familiar_Bolita_C')
cdo = unreal.get_default_object(cls)
mesh = cdo.get_editor_property('mesh')
ac = mesh.get_editor_property('anim_class')
out.append("anim class: %s" % (ac.get_path_name() if ac else None))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
hits = [a for a in ar.get_assets(unreal.ARFilter(package_paths=["/Game"], recursive_paths=True)) if str(a.asset_name) in ('ABP_Bolita',)]
paths = set([ac.get_path_name().replace('_C', '').rsplit('.', 1)[0]] if ac else []) | set(str(a.package_name) for a in hits)
for pkg in paths:
    p = pkg + '.' + pkg.split('/')[-1]
    out.append("######## " + p)
    for g in call('list_graphs', {'blueprint': {'refPath': p}}):
        gr = g['refPath']
        d = str(call('read_graph_dsl', {'graph': {'refPath': gr}}))
        out.append("--- %s\n%s" % (gr.split(':')[-1], d[:3500]))
        if 'AnimGraph' in gr:
            for x in infos(nodes(gr)):
                if any(k in x['type_id'] for k in ('BlendSpace', 'Blendspace', 'BS_', 'Sequence', 'Fly')):
                    out.append("   ANIMNODE %s %s inputs=%s" % (x['node']['refPath'].split('.')[-1], x['type_id'], [(q['name'], [c['node']['refPath'].split('.')[-1] for c in (q.get('connected_pins') or [])], q.get('default_value')) for q in x['input_pins']]))
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump144.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
