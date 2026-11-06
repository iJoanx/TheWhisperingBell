import unreal, json, asyncio, inspect
import toolset_registry._registry_interface as RI
def call(n, a, ts='editor_toolset.toolsets.blueprint.BlueprintTools'):
    r = RI.execute_tool(ts, n, a)
    if inspect.iscoroutine(r): r = asyncio.new_event_loop().run_until_complete(r)
    return r['returnValue'] if isinstance(r, dict) and 'returnValue' in r else r
BP = '/Game/Level/WhisperingBell/Blueprints/BP_WB_Sewer_Entry.BP_WB_Sewer_Entry'
for q in ["SetCastShadows", "ContainsDataLayer", "Set Visibility", "GetAllActorsOfClass", "IsLocallyControlled", "SetActorLocationAndRotation", "Set bEnabled", "Cast To PostProcessVolume", "GetRootComponent", "GetForwardVector", "Teleport", "GetDataLayerAssets", "SetActorHiddenInGame", "SetHiddenInGame", "Get Distance To", "Vector Distance", "Get World Location", "Get Controller", "SetControlRotation", "Run on Server", "HasAuthority"]:
    try:
        r = call('find_node_types', {'graph': {'refPath': BP + ':EventGraph'}, 'query': q})
        print("Q", q, json.dumps(r)[:900])
    except Exception as e:
        print("Q", q, "ERR", str(e)[:300])
