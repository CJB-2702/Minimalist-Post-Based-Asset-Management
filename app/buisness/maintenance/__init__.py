"""
Maintenance Business Layer
Contains structs, contexts, factories, and business logic for maintenance operations.

Organization:
- base/ : Actual maintenance work (MaintenanceActionSet, Action, PartDemand, etc.)
- templates/ : Maintenance blueprints (TemplateActionSet, TemplateActionItem, etc.)
- proto_templates/ : Reusable library (ProtoActionItem, etc.)
- factories/ : Factory classes for creating maintenance from templates
"""

# Base maintenance
from app.buisness.maintenance.base import (
    MaintenanceActionSetStruct,
    ActionStruct,
    PartDemandStruct,
    ActionToolStruct,
    MaintenanceContext,
    ActionContext,
    MaintenancePlanContext,
)

# Template maintenance
from app.buisness.maintenance.templates import (
    TemplateActionSetStruct,
    TemplateActionItemStruct,
    TemplatePartDemandStruct,
    TemplateActionToolStruct,
    TemplateMaintenanceContext,
    TemplateActionContext,
)

# Proto template maintenance
from app.buisness.maintenance.proto_templates import (
    ProtoActionItemStruct,
    ProtoActionContext,
)

# Factories
from app.buisness.maintenance.factories import (
    MaintenanceActionSetFactory,
    ActionFactory,
    MaintenanceFactory,
)

__all__ = [
    # Base
    'MaintenanceActionSetStruct',
    'ActionStruct',
    'PartDemandStruct',
    'ActionToolStruct',
    'MaintenanceContext',
    'ActionContext',
    'MaintenancePlanContext',
    # Templates
    'TemplateActionSetStruct',
    'TemplateActionItemStruct',
    'TemplatePartDemandStruct',
    'TemplateActionToolStruct',
    'TemplateMaintenanceContext',
    'TemplateActionContext',
    # Proto
    'ProtoActionItemStruct',
    'ProtoActionContext',
    # Factories
    'MaintenanceActionSetFactory',
    'ActionFactory',
    'MaintenanceFactory',
]
