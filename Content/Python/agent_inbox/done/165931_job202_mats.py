import sys; sys.path.insert(0, r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_lib")
import importlib, h; importlib.reload(h)
from h import *
import unreal
out = []
GAP_X, GAP_Y = 70, 30
ar = unreal.AssetRegistryHelpers.get_asset_registry()
_assets = None
def find_bp(name):
    global _assets
    if _assets is None: _assets = ar.get_assets(unreal.ARFilter(package_paths=['/Game'], recursive_paths=True))
    for a in _assets:
        if str(a.asset_name) == name: return str(a.package_name) + '.' + name
def is_exec(p): return 'Exec' in str(p.get('type_id', ''))
LITS = ('Math|Integer|MakeLiteralInt', 'Math|Float|MakeLiteralFloat', 'Math|Float|MakeLiteralDouble', 'Utilities|MakeLiteralBool', 'Math|Boolean|MakeLiteralBool')

class Graph:
    def __init__(self, G, only=None):
        self.G = G
        self.X = {x['node']['refPath']: x for x in infos(nodes(G))}
        self.only = only
        self.obj = {r: unreal.find_object(None, r) for r in self.X}
        for o in self.obj.values():
            if o: o.modify()
    def size(self, r):
        s = self.obj[r].get_node_size(); w, hh = int(s.x), int(s.y)
        return (w if w > 0 else 200, hh if hh > 0 else 60)
    def pos(self, r): p = self.obj[r].get_node_pos(); return p.x, p.y
    def setpos(self, r, x, y): self.obj[r].set_node_pos(unreal.IntPoint(int(x), int(y)))
    def has_exec(self, r): return any(is_exec(p) for p in self.X[r]['input_pins'] + self.X[r]['output_pins'])
    def data_children(self, r):
        res = []
        for p in self.X[r]['input_pins']:
            if is_exec(p): continue
            for c in (p.get('connected_pins') or []):
                cr = c['node']['refPath']
                if cr in self.X and not self.has_exec(cr): res.append(cr)
        return res
    def exec_children(self, r):
        res = []
        for p in self.X[r]['output_pins']:
            if not is_exec(p): continue
            for c in (p.get('connected_pins') or []):
                if c['node']['refPath'] in self.X: res.append(c['node']['refPath'])
        return res

def split_getters(G):
    n_ = 0
    for x in infos(nodes(G)):
        if 'VariableGet' not in x['node']['refPath'] or not x['output_pins']: continue
        o = x['output_pins'][0]
        links = (o.get('connected_pins') or [])[1:]
        if not links: continue
        t = x['type_id']
        if t.startswith('|'):
            nm = t[1:]
            try: cands = [c.get('type_id') if isinstance(c, dict) else c for c in types(G, nm)]
            except Exception: cands = []
            t = next((c for c in cands if c.startswith('Variables|') and c.endswith('|' + nm)), None)
            if not t: out.append("  (kept shared getter %s)" % nm); continue
        for d in links:
            n = node(G, t, 0, 0)
            call('break_pins', {'output_pin': o['pin_id'], 'input_pin': d})
            connect(info(n)['output_pins'][0], {'pin_id': d}); n_ += 1
    return n_
def fold_literals(G):
    n_ = 0
    for x in infos(nodes(G)):
        if x['type_id'] not in LITS: continue
        ins = [p for p in x['input_pins'] if not is_exec(p)]
        if not ins: continue
        v = ins[0].get('value')
        dsts = x['output_pins'][0].get('connected_pins') or []
        call('delete_node', {'node': {'refPath': x['node']['refPath']}})
        for d in dsts:
            for y in infos([d['node']['refPath']]):
                for p in y['input_pins']:
                    if p['pin_id'] == d: setv(p, v)
        n_ += 1
    return n_

def layout(g, roots):
    placed = set()
    def place_tree(r, right, top):
        if r in placed: return 0
        placed.add(r)
        w, hh = g.size(r)
        ch = [c for c in g.data_children(r) if c not in placed]
        y = top; used = 0
        for c in ch:
            hgt = place_tree(c, right - w - GAP_X, y)
            if hgt: y += hgt + GAP_Y; used += hgt + GAP_Y
        used = max(hh, used - GAP_Y) if used else hh
        g.setpos(r, right - w, top + (used - hh) // 2 if used > hh else top)
        return used
    def tree_width(r, seen):
        if r in seen or r in placed: return 0
        seen.add(r)
        w, _ = g.size(r)
        return w + max([tree_width(c, seen) + GAP_X for c in g.data_children(r)] or [0])
    def place_exec(r, x, y):
        """Places exec node r at lane y, left edge at least x. Returns (right edge, bottom)."""
        if r in placed: return x, y
        kids = [c for c in g.data_children(r) if c not in placed]
        tw = max([tree_width(c, set()) for c in kids] or [0])
        nx = x + (tw + GAP_X if tw else 0)
        placed.add(r)
        w, hh = g.size(r)
        g.setpos(r, nx, y)
        bottom = y + hh
        ty = y + hh + 40
        for c in kids:
            hgt = place_tree(c, nx - GAP_X, ty)
            if hgt: ty += hgt + GAP_Y
        bottom = max(bottom, ty)
        right = nx + w
        lane_y = y
        first = True
        for c in g.exec_children(r):
            if c in placed: continue
            if first:
                rr, bb = place_exec(c, right + GAP_X + 40, y); first = False
            else:
                rr, bb = place_exec(c, right + GAP_X + 40, bottom + 60)
            bottom = max(bottom, bb)
        return right, bottom
    y = 0
    for r in roots:
        _, b = place_exec(r, 0, y)
        y = b + 150
    # anything not reached (pure-only graph etc.)
    return len(placed)

def tidy_whole(bpname, graphname=None, root_filter=None):
    bp = find_bp(bpname)
    if not bp: out.append("no asset %s" % bpname); return
    graphs = {gg['refPath'].split(':')[-1]: gg['refPath'] for gg in call('list_graphs', {'blueprint': {'refPath': bp}})}
    if graphname not in graphs: out.append("%s: no graph %s" % (bpname, graphname)); return
    G = graphs[graphname]
    unreal.load_asset(bp.split('.')[0]).modify()
    if root_filter is None:
        s = split_getters(G); f = fold_literals(G)
        g = Graph(G)
        roots = [r for r in g.X if 'FunctionEntry' in r]
    else:
        g0 = Graph(G)
        root = [r for r in g0.X if root_filter in g0.X[r]['type_id']][0]
        # collect the component of this event so the rest of the graph is untouched
        comp, stack = set(), [root]
        while stack:
            r = stack.pop()
            if r in comp or r not in g0.X: continue
            comp.add(r)
            for p in g0.X[r]['input_pins'] + g0.X[r]['output_pins']:
                for c in (p.get('connected_pins') or []): stack.append(c['node']['refPath'])
        s = f = 0
        g = g0
        # keep the event where it was: offset after layout
        ox, oy = g.pos(root)
        roots = [root]
    n = layout(g, roots)
    if root_filter is not None:
        nx, ny = g.pos(roots[0])
        for r in comp:
            x, y = g.pos(r); g.setpos(r, x - nx + ox, y - ny + oy)
    out.append("tidied %s:%s (%d nodes laid out, %d getters split, %d literals folded)" % (bpname, graphname, n, s, f))



# ---- underwater materials without the wobble (recreate the assets from scratch)
for _n in ("M_PP_Underwater_Sea", "M_PP_Underwater_Sewage"):
    _p = "/Game/Water/" + _n
    if unreal.EditorAssetLibrary.does_asset_exist(_p):
        out.append("deleted old %s: %s" % (_n, unreal.EditorAssetLibrary.delete_asset(_p)))
try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    eal = unreal.EditorAssetLibrary
    MEL = unreal.MaterialEditingLibrary
    D = "/Game/Water"
    if not eal.does_directory_exist(D): eal.make_directory(D)

    # ---------- parameter collection
    mpc_path = D + "/MPC_Water"
    mpc = unreal.load_asset(mpc_path) if eal.does_asset_exist(mpc_path) else at.create_asset("MPC_Water", D, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    params = []
    for n in ("SeaUnderwater", "SewageUnderwater", "UnderwaterDepth"):
        p = unreal.CollectionScalarParameter(); p.set_editor_property("parameter_name", n); p.set_editor_property("default_value", 0.0)
        params.append(p)
    existing = [str(p.get_editor_property("parameter_name")) for p in mpc.get_editor_property("scalar_parameters")]
    if sorted(existing) != sorted(["SeaUnderwater", "SewageUnderwater", "UnderwaterDepth"]):
        mpc.set_editor_property("scalar_parameters", params)
    out.append("MPC params: %s" % [str(p.get_editor_property("parameter_name")) for p in mpc.get_editor_property("scalar_parameters")])

    def build(name, amount_param, tint, water_color, density, wobble):
        path = D + "/" + name
        if eal.does_asset_exist(path):
            m = unreal.load_asset(path); MEL.delete_all_material_expressions(m)
        else:
            m = at.create_asset(name, D, unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property("material_domain", unreal.MaterialDomain.MD_POST_PROCESS)
        try: m.set_editor_property("blendable_location", unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
        except Exception as e: out.append("blendable_location: %s" % e)
        X = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
        C = MEL.connect_material_expressions
        def const(v, x, y):
            e = X(unreal.MaterialExpressionConstant, x, y); e.set_editor_property("r", v); return e
        def mul(a, b, x, y, bconst=None):
            e = X(unreal.MaterialExpressionMultiply, x, y); C(a, "", e, "A")
            if bconst is not None: e.set_editor_property("const_b", bconst)
            else: C(b, "", e, "B")
            return e
        def add(a, b, x, y):
            e = X(unreal.MaterialExpressionAdd, x, y); C(a, "", e, "A"); C(b, "", e, "B"); return e
        def mask(src, r, g, x, y):
            e = X(unreal.MaterialExpressionComponentMask, x, y)
            e.set_editor_property("r", r); e.set_editor_property("g", g); e.set_editor_property("b", False); e.set_editor_property("a", False)
            C(src, "", e, ""); return e
        # how much of the effect (0 = off, 1 = camera under this water)
        amount = X(unreal.MaterialExpressionCollectionParameter, -1600, -300)
        amount.set_editor_property("collection", mpc); amount.set_editor_property("parameter_name", amount_param)
        uv = X(unreal.MaterialExpressionTextureCoordinate, -400, 0)
        uvd = uv
        scene = X(unreal.MaterialExpressionSceneTexture, -250, 0)
        scene.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
        C(uvd, "", scene, "UVs")
        sc = mask(scene, True, True, -50, 0); sc.set_editor_property("b", True)
        # depth fog towards the water colour
        depth = X(unreal.MaterialExpressionSceneTexture, -700, 450)
        depth.set_editor_property("scene_texture_id", unreal.SceneTextureId.PPI_SCENE_DEPTH)
        dr = mask(depth, True, False, -500, 450)
        dd = mul(dr, None, -350, 450, density)
        one_plus = X(unreal.MaterialExpressionAdd, -200, 450); C(dd, "", one_plus, "A"); one_plus.set_editor_property("const_b", 1.0)
        inv = X(unreal.MaterialExpressionDivide, -50, 450); inv.set_editor_property("const_a", 1.0); C(one_plus, "", inv, "B")
        fog = X(unreal.MaterialExpressionOneMinus, 100, 450); C(inv, "", fog, "")
        tintc = X(unreal.MaterialExpressionConstant3Vector, 100, 150); tintc.set_editor_property("constant", unreal.LinearColor(*tint, 1.0))
        tinted = mul(sc, tintc, 250, 50)
        wc = X(unreal.MaterialExpressionConstant3Vector, 250, 300); wc.set_editor_property("constant", unreal.LinearColor(*water_color, 1.0))
        fogged = X(unreal.MaterialExpressionLinearInterpolate, 450, 150); C(tinted, "", fogged, "A"); C(wc, "", fogged, "B"); C(fog, "", fogged, "Alpha")
        final = X(unreal.MaterialExpressionLinearInterpolate, 650, 0); C(sc, "", final, "A"); C(fogged, "", final, "B"); C(amount, "", final, "Alpha")
        MEL.connect_material_property(final, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(m)
        out.append("%s built (%d expressions)" % (name, MEL.get_num_material_expressions(m)))
        return m

    sea_m = build("M_PP_Underwater_Sea", "SeaUnderwater", (0.55, 0.85, 0.9), (0.015, 0.09, 0.12), 0.0008, 0.0)
    sew_m = build("M_PP_Underwater_Sewage", "SewageUnderwater", (0.7, 0.75, 0.45), (0.05, 0.055, 0.015), 0.006, 0.0)

    # ---------- two unbound post-process volumes, one per data layer
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    dls = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)
    def inst_for(asset_path):
        a = unreal.load_asset(asset_path)
        for d in dls.get_all_data_layers():
            try:
                if d.get_asset() == a: return d
            except Exception: pass
    for label, mat, layer in (("PPV_Underwater_Sea", sea_m, "/Game/Levels/DataLayers/RDL_Sea"), ("PPV_Underwater_Sewage", sew_m, "/Game/Levels/DataLayers/RDL_Sewers")):
        ppv = next((a for a in eas.get_all_level_actors() if a.get_actor_label() == label), None)
        if ppv is None:
            ppv = eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
            ppv.set_actor_label(label)
        ppv.set_folder_path("Water")
        ppv.set_editor_property("unbound", True)
        ppv.set_editor_property("priority", 10.0)
        s = ppv.get_editor_property("settings")
        wb = unreal.WeightedBlendables(); wbl = unreal.WeightedBlendable(); wbl.set_editor_property("weight", 1.0); wbl.set_editor_property("object", mat)
        wb.set_editor_property("array", [wbl]); s.set_editor_property("weighted_blendables", wb)
        ppv.set_editor_property("settings", s)
        if ppv.get_editor_property("is_spatially_loaded"): ppv.set_editor_property("is_spatially_loaded", False)
        inst = inst_for(layer)
        r = dls.add_actors_to_data_layer([ppv], inst) if inst else None
        out.append("%s: unbound=%s blendables=%d layer=%s added=%s" % (label, ppv.get_editor_property("unbound"), len(ppv.get_editor_property("settings").get_editor_property("weighted_blendables").get_editor_property("array")), layer.split('/')[-1], r))

except Exception as e:
    import traceback; out.append("MATERIAL ERR " + traceback.format_exc()[-1500:])
open(r"C:\Users\Admin\Documents\Unreal Projects\TheWhisperingBell\Content\Python\agent_inbox\dump202.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
