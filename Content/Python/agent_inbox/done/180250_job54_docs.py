import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as BT
for n in ("find_node_types","get_node_type_pins","create_node","add_event","list_events","set_pin_value","get_pin_value","add_variable","set_variable_replication","call_method","find_node_categories","add_function_graph","add_function_param","list_functions","delete_node","break_pins","get_create_event_function","list_compatible_event_functions"):
    f = getattr(BT, n, None)
    print("=====", n, "\n", (f.__doc__ or "").strip()[:1400])
import toolset_registry._registry_interface as RI
reg = RI.get_toolset_registry()
print("REG", type(reg), [n for n in dir(reg) if not n.startswith("_")])
