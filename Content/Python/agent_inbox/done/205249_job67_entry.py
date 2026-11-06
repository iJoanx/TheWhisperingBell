import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
E = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry'
EG = E + ':EventGraph'
bp = unreal.load_asset(E)
# ---- components: SewerBox (under Capsule) and ReturnPoint (under root)
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
L = unreal.SubobjectDataBlueprintFunctionLibrary
handles = {}
for hd in sub.k2_gather_subobject_data_for_blueprint(bp):
    d = L.get_data(hd)
    handles[str(L.get_variable_name(d))] = hd
out.append("components: %s" % list(handles))
def add(parent, cls, name):
    if name in handles: return L.get_object(L.get_data(handles[name]))
    p = unreal.AddNewSubobjectParams(parent_handle=handles[parent], new_class=cls, blueprint_context=bp)
    hd, fail = sub.add_new_subobject(p)
    if not L.is_handle_valid(hd): raise RuntimeError("add %s failed: %s" % (name, fail))
    sub.rename_subobject(hd, unreal.Text(name))
    handles[name] = hd
    return L.get_object(L.get_data(hd))
sb = add('Capsule', unreal.BoxComponent, 'SewerBox')
sb.set_editor_property('relative_location', unreal.Vector(0, 0, 150))
sb.set_editor_property('box_extent', unreal.Vector(60, 60, 40))
sb.set_collision_profile_name('Custom')
sb.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
sb.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_IGNORE)
sb.set_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA, unreal.CollisionResponseType.ECR_BLOCK)
sb.set_editor_property('hidden_in_game', True)
rp_parent = 'DefaultSceneRoot' if 'DefaultSceneRoot' in handles else list(handles)[1]
rp = add(rp_parent, unreal.SceneComponent, 'ReturnPoint')
rp.set_editor_property('relative_location', unreal.Vector(0, 0, 100))
compile_bp(E)
# ---- functions via DSL
g = call('add_function_graph', {'blueprint': {'refPath': E}, 'graph_name': 'ApplySewerView'})['refPath']
if 'InSewer' not in str(info(nodes(g)[0])):
    call('add_function_param', {'graph': {'refPath': g}, 'param_name': 'InSewer', 'param_type': 'bool', 'input_param': True})
if len(nodes(g)) <= 1: call('write_graph_dsl', {'graph': {'refPath': g}, 'code': '''(fn ApplySewerView (InSewer)
  (bind sew (Actor|GetAllActorsOfClasswithTag "/Script/Engine.Actor" "RDL_Sewers"))
  (for a sew
    (Rendering|SetActorHiddenInGame a (not InSewer)))
  (bind sky (Actor|GetAllActorsOfClasswithTag "/Script/Engine.Actor" "RDL_Sky"))
  (for b sky
    (Rendering|SetActorHiddenInGame b InSewer)))'''})
out.append("ApplySewerView:\n" + str(call('read_graph_dsl', {'graph': {'refPath': g}})))
g2 = call('add_function_graph', {'blueprint': {'refPath': E}, 'graph_name': 'UseEntry'})['refPath']
if 'Player' not in str(info(nodes(g2)[0])):
    call('add_object_function_param', {'graph': {'refPath': g2}, 'param_name': 'Player', 'object_class': {'refPath': '/Script/Engine.Actor'}, 'input_param': True})
for n_ in nodes(g2):
    if 'FunctionEntry' not in n_: call('delete_node', {'node': {'refPath': n_}})
call('write_graph_dsl', {'graph': {'refPath': g2}, 'code': '''(fn UseEntry (Player)
  (bind ploc (Transformation|GetActorLocation Player))
  (bind down (< (Math|Vector|Distance(Vector) ploc (Transformation|GetWorldLocation (Variables|Default|GetBox))) (Math|Vector|Distance(Vector) ploc (Transformation|GetWorldLocation (Variables|Default|GetSewerBox)))))
  (Transformation|SetActorLocation Player (select down (Transformation|GetWorldLocation (Variables|Default|GetCapsule)) (Transformation|GetWorldLocation (Variables|Default|GetReturnPoint))) false true)
  (bind pawn (Utilities|Casting|CastToPawn :Object Player)
    (:then
      (if (Pawn|IsLocallyControlled pawn)
        (CallFunction|ApplySewerView :InSewer down)))
    (:CastFailed)))'''})
out.append("UseEntry:\n" + str(call('read_graph_dsl', {'graph': {'refPath': g2}})))
# ---- event graph: OnInteract -> UseEntry, BeginPlay -> ApplySewerView(false); remove old streaming chain
ii = infos(nodes(EG))
by = {x['node']['refPath']: x for x in ii}
oi = [x for x in ii if x['type_id'] == 'AddEvent|EventOnInteract'][0]
bpn = [x for x in ii if x['type_id'] == 'AddEvent|EventBeginPlay'][0]
keep = {'AddEvent|EventOnInteract', 'AddEvent|EventBeginPlay', 'AddEvent|Collision|EventActorBeginOverlap', 'AddEvent|EventTick'}
removed = []
for x in ii:
    if x['type_id'] not in keep:
        call('delete_node', {'node': x['node']}); removed.append(x['type_id'])
out.append("removed: %s" % removed)
x0, y0 = oi['position']['x'], oi['position']['y']
cu = node(EG, 'CallFunction|UseEntry', x0 + 350, y0)
connect(pin(oi['node']['refPath'], 'then', 'out'), pin(cu, 'execute', 'in'))
connect(pin(oi['node']['refPath'], 'Player', 'out'), pin(cu, 'Player', 'in'))
bx, by_ = bpn['position']['x'], bpn['position']['y']
ca = node(EG, 'CallFunction|ApplySewerView', bx + 350, by_)
connect(pin(bpn['node']['refPath'], 'then', 'out'), pin(ca, 'execute', 'in'))
setv(pin(ca, 'InSewer', 'in'), 'false')
r = compile_bp(E)
out.append("compile: %s" % (r,))
out.append("EventGraph:\n" + str(call('read_graph_dsl', {'graph': {'refPath': EG}})))
# instance check
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_class().get_name() == 'BP_WB_Sewer_Entry_C':
        cs = {c.get_name(): c.get_world_location() for c in a.get_components_by_class(unreal.SceneComponent)}
        out.append("%s SewerBox=%s ReturnPoint=%s Capsule=%s" % (a.get_actor_label(), cs.get('SewerBox'), cs.get('ReturnPoint'), cs.get('Capsule')))
print("\n".join(str(x) for x in out))
