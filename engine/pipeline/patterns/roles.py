from enum import Enum

class SemanticRole(str, Enum):
    COMPONENT_STATE = "component_state"
    COMPONENT_METHOD = "component_method"
    SERVICE = "service"
    CONTROLLER = "controller"
    TEMPLATE_BINDING = "template_binding"
    EVENT_HANDLER = "event_handler"
