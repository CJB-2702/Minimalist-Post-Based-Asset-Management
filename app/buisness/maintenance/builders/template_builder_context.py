"""
Template Builder Context
Business logic context manager for building draft templates before submission.
"""

from typing import List, Optional, Union, Dict, Any
from app import db
from app.data.maintenance.builders.template_builder_memory import TemplateBuilderMemory
from app.data.maintenance.builders.template_builder_attachment_reference import TemplateBuilderAttachmentReference
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.maintenance.templates.template_action_set_attachments import TemplateActionSetAttachment
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment
from app.buisness.maintenance.builders.build_action import BuildAction
from app.buisness.maintenance.builders.build_part_demand import BuildPartDemand
from app.buisness.maintenance.builders.build_action_tool import BuildActionTool
from app.buisness.maintenance.builders.build_attachment import BuildAttachment
from app.buisness.maintenance.templates.template_maintenance_context import TemplateMaintenanceContext
from datetime import datetime
import json

class TemplateBuilderContext:
    """
    Business logic context manager for building draft templates.
    
    Manages in-memory build state with wrapper classes and provides
    methods to build templates incrementally before submission.
    """
    
    # Valid fields from VirtualActionSet
    _valid_metadata_fields = None
    
    def __init__(self, builder_memory: Union[TemplateBuilderMemory, int]):
        """
        Initialize TemplateBuilderContext with TemplateBuilderMemory or ID.
        
        Args:
            builder_memory: TemplateBuilderMemory instance or ID
        """
        if isinstance(builder_memory, int):
            self._builder_memory = TemplateBuilderMemory.query.get_or_404(builder_memory)
        else:
            self._builder_memory = builder_memory
        
        # Load build state from JSON
        build_state = self._builder_memory.get_build_state_dict()
        
        # Initialize metadata, actions, and attachments
        self._build_metadata: Dict[str, Any] = build_state.get('metadata', {})
        self._build_actions: List[BuildAction] = []
        self._build_attachments: List[BuildAttachment] = []
        
        # Create BuildAction instances from action data
        actions_data = build_state.get('actions', [])
        for action_data in actions_data:
            self._build_actions.append(BuildAction(action_data))
        
        # Load action-set level attachments from data
        attachments_data = build_state.get('attachments', [])
        for att_data in attachments_data:
            self._build_attachments.append(BuildAttachment(att_data))
        
        self._ensure_valid_metadata()
    
    @classmethod
    def _get_valid_metadata_fields(cls) -> set:
        """Get valid field names from TemplateActionSet model, excluding builder-invalid fields."""
        if cls._valid_metadata_fields is None:
            all_fields = TemplateActionSet.get_column_dict()
            invalid_columns = ['maintenance_plan_id']
            whitelist = { 'attachments'}
            all_fields = all_fields | whitelist
            cls._valid_metadata_fields = all_fields - set(invalid_columns)
        return cls._valid_metadata_fields
    
    def _ensure_valid_metadata(self):
        """Remove any invalid fields from metadata."""
        valid_fields = self._get_valid_metadata_fields()
        self._build_metadata = {k: v for k, v in self._build_metadata.items() if k in valid_fields}
    
    @property
    def builder_memory(self) -> TemplateBuilderMemory:
        """Get the TemplateBuilderMemory instance."""
        return self._builder_memory
    
    @property
    def builder_id(self) -> int:
        """Get the builder memory ID."""
        return self._builder_memory.id
    
    @property
    def name(self) -> str:
        """Get builder name."""
        return self._builder_memory.name
    
    @property
    def build_type(self) -> Optional[str]:
        """Get build type."""
        return self._builder_memory.build_type
    
    @property
    def build_status(self) -> str:
        """Get build status."""
        return self._builder_memory.build_status
    
    @property
    def build_actions(self) -> List[BuildAction]:
        """Get list of build actions."""
        return self._build_actions
    
    @property
    def build_attachments(self) -> List[BuildAttachment]:
        """Get list of action-set level attachments."""
        return self._build_attachments
    
    # Creation methods
    @classmethod
    def create_blank(cls, name: str, build_type: Optional[str] = None, user_id: Optional[int] = None) -> 'TemplateBuilderContext':
        """
        Create a new blank template builder.
        
        Args:
            name: Name for the template
            build_type: Optional build type classification
            user_id: User ID creating the builder
            
        Returns:
            TemplateBuilderContext: New builder context
        """
        builder_memory = TemplateBuilderMemory(
            name=name,
            build_type=build_type,
            build_status='Initialized',
            created_by_id=user_id,
            updated_by_id=user_id,
            is_revision=False  # New builds are not revisions
        )
        db.session.add(builder_memory)
        db.session.commit()
        
        # Create context and set default revision to '0' for new builds
        context = cls(builder_memory)
        if 'revision' not in context._build_metadata:
            context._build_metadata['revision'] = '0'
            context._save()
        
        return context
    
    @classmethod
    def copy_from_template(
        cls,
        template_action_set_id: int,
        name: str,
        is_revision: bool = False,
        user_id: Optional[int] = None
    ) -> 'TemplateBuilderContext':
        """
        Create a new builder by copying from an existing template.
        
        Args:
            template_action_set_id: ID of template to copy from
            name: Name for the new builder
            is_revision: If True, links as revision; if False, creates new template
            user_id: User ID creating the builder
            
        Returns:
            TemplateBuilderContext: New builder context with copied data
        """
        template = TemplateActionSet.query.get_or_404(template_action_set_id)

        if is_revision:
            builder_memory = TemplateBuilderMemory(
                name=name,
                build_type=None,  # Can be set later
                build_status='Initialized',
                created_by_id=user_id,
                updated_by_id=user_id,
                src_revision_id=template_action_set_id,
                src_revision_number=template.revision,
                is_revision=True
            )
        else:
            builder_memory = TemplateBuilderMemory(
                name=name,
                build_type=None,  # Can be set later
                build_status='Initialized',
                created_by_id=user_id,
                updated_by_id=user_id
            )
        db.session.add(builder_memory)
        db.session.flush()  # Get ID
        
        # Create context
        context = cls(builder_memory)
        
        # Copy metadata from template using TemplateActionSet.get_column_dict()
        # Invalid columns are already filtered by _get_valid_metadata_fields()
        valid_fields = context._get_valid_metadata_fields()
        for key in valid_fields:
            if hasattr(template, key):
                value = getattr(template, key)
                if value is not None:
                    context._build_metadata[key] = value
        
        # Handle revision logic
        if is_revision:
            # For revisions, set prior_revision_id and increment revision number
            context._build_metadata['prior_revision_id'] = template.id
            if template.revision:
                # Increment revision number (simple approach)
                try:
                    rev_num = int(template.revision)
                    context._build_metadata['revision'] = str(rev_num + 1)
                except ValueError:
                    context._build_metadata['revision'] = '2'
            else:
                # If source has no revision, start at 1
                context._build_metadata['revision'] = '1'
        else:
            # For new builds (not revisions), default to '0' and no prior_revision_id
            context._build_metadata['revision'] = '0'
            context._build_metadata['prior_revision_id'] = None
        
        # Ensure is_active is set
        if 'is_active' not in context._build_metadata:
            context._build_metadata['is_active'] = True
        
        # Copy actions
        for template_action in template.template_action_items:
            context.add_action_from_template_item(template_action.id)
        
        # Copy action-set level attachments (only attachment_id, no TemplateBuilderAttachmentReference created)
        for template_attachment in template.template_action_set_attachments:
            attachment_data = {}
            # Use BuildAttachment's valid fields (invalid columns already filtered)
            valid_att_fields = BuildAttachment._get_valid_fields()
            for key in valid_att_fields:
                if hasattr(template_attachment, key):
                    value = getattr(template_attachment, key)
                    if value is not None:
                        attachment_data[key] = value
            context.add_attachment(attachment_data)
        
        context._save()
        return context
    
    # Building functions
    def add_action_from_template_item(self, template_action_item_id: int) -> BuildAction:
        """
        Add an action by copying from an existing TemplateActionItem.
        
        Args:
            template_action_item_id: ID of template action item to copy
            
        Returns:
            BuildAction: The created action wrapper
        """
        # Get next sequence order
        sequence_order = self._get_next_sequence_order()
        
        # Create action using class method
        action = BuildAction.from_template_item(template_action_item_id, sequence_order=sequence_order)
        
        # If action didn't get sequence_order from template, set it
        if not action.sequence_order:
            action.sequence_order = sequence_order
        
        # Add to actions list
        self._build_actions.append(action)
        self._save()
        return action
    
    def add_action_from_proto(self, proto_action_id: int) -> BuildAction:
        """
        Add an action by copying from a ProtoActionItem.
        
        Args:
            proto_action_id: ID of proto action item to copy
            
        Returns:
            BuildAction: The created action wrapper
        """
        # Get next sequence order
        sequence_order = self._get_next_sequence_order()
        
        # Create action using class method
        action = BuildAction.from_proto(proto_action_id, sequence_order=sequence_order)
        
        # Add to actions list
        self._build_actions.append(action)
        self._save()
        return action
    
    def add_action_from_dict(self, action_dict: Dict[str, Any]) -> BuildAction:
        """
        Add an action from a dictionary (for custom actions from presentation layer).
        
        Args:
            action_dict: Dictionary containing action data
            
        Returns:
            BuildAction: The created action wrapper
        """
        # Get next sequence order if not provided
        sequence_order = action_dict.get('sequence_order') or self._get_next_sequence_order()
        
        # Create action using class method
        action = BuildAction.from_dict(action_dict, sequence_order=sequence_order)
        
        # Add to actions list
        self._build_actions.append(action)
        self._save()
        return action
    
    def add_part_demand_to_action(self, action_index: int, part_data: Dict[str, Any]) -> BuildPartDemand:
        """
        Add a part demand to an action.
        
        Args:
            action_index: Index of action in build_actions list
            part_data: Dictionary containing part demand fields
            
        Returns:
            BuildPartDemand: The created part demand wrapper
        """

        if 0 <= action_index < len(self._build_actions):
            part_demand = self._build_actions[action_index].add_part_demand(part_data)
            self._save()
            return part_demand
        raise IndexError(f"Action index {action_index} out of range")
    
    def add_tool_to_action(self, action_index: int, tool_data: Dict[str, Any]) -> BuildActionTool:
        """
        Add a tool to an action.
        
        Args:
            action_index: Index of action in build_actions list
            tool_data: Dictionary containing tool fields
            
        Returns:
            BuildActionTool: The created tool wrapper
        """
        if 0 <= action_index < len(self._build_actions):
            tool = self._build_actions[action_index].add_tool(tool_data)
            self._save()
            return tool
        raise IndexError(f"Action index {action_index} out of range")
    
    # Update functions
    def update_action(self, action_index: int, updates: Dict[str, Any]):
        """
        Update fields on an existing build action.
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions[action_index].update_from_dict(updates)
            # If sequence order is changed, normalize sequence ordering
            if 'sequence_order' in updates and updates.get('sequence_order'):
                # Sort by sequence_order while preserving list object identity
                self._build_actions.sort(key=lambda a: a.sequence_order or 0)
                self._renumber_sequence_orders()
            self._save()
            return
        raise IndexError(f"Action index {action_index} out of range")

    def update_part_demand(self, action_index: int, part_index: int, updates: Dict[str, Any]):
        """
        Update fields on a part demand for an action.
        """
        if 0 <= action_index < len(self._build_actions):
            action = self._build_actions[action_index]
            if 0 <= part_index < len(action.part_demands):
                action.part_demands[part_index].update_from_dict(updates)
                self._save()
                return
            raise IndexError(f"Part demand index {part_index} out of range")
        raise IndexError(f"Action index {action_index} out of range")

    def update_tool(self, action_index: int, tool_index: int, updates: Dict[str, Any]):
        """
        Update fields on a tool for an action.
        """
        if 0 <= action_index < len(self._build_actions):
            action = self._build_actions[action_index]
            if 0 <= tool_index < len(action.tools):
                action.tools[tool_index].update_from_dict(updates)
                self._save()
                return
            raise IndexError(f"Tool index {tool_index} out of range")
        raise IndexError(f"Action index {action_index} out of range")

    # Remove functions
    def remove_action(self, action_index: int):
        """
        Remove an action and renumber sequence orders.
        
        Args:
            action_index: Index of action to remove
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions.pop(action_index)
            self._renumber_sequence_orders()
            self._save()
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    def remove_part_demand_from_action(self, action_index: int, part_demand_index: int):
        """
        Remove a part demand from an action.
        
        Args:
            action_index: Index of action
            part_demand_index: Index of part demand to remove
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions[action_index].remove_part_demand(part_demand_index)
            self._save()
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    def remove_tool_from_action(self, action_index: int, tool_index: int):
        """
        Remove a tool from an action.
        
        Args:
            action_index: Index of action
            tool_index: Index of tool to remove
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions[action_index].remove_tool(tool_index)
            self._save()
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    # Attachment management methods
    def add_attachment(self, attachment_data: Dict[str, Any], is_new_upload: bool = False, attachment_id: Optional[int] = None) -> BuildAttachment:
        """
        Add an action-set level attachment.
        
        Args:
            attachment_data: Dictionary containing attachment reference fields
            is_new_upload: If True, creates TemplateBuilderAttachmentReference record
            attachment_id: Attachment ID (required if is_new_upload is True)
            
        Returns:
            BuildAttachment: The created attachment wrapper
        """
        attachment = BuildAttachment(attachment_data)
        self._build_attachments.append(attachment)
        
        # Create TemplateBuilderAttachmentReference for new uploads only
        if is_new_upload and attachment_id:
            builder_att_ref = TemplateBuilderAttachmentReference(
                template_builder_memory_id=self.builder_id,
                attachment_id=attachment_id,
                attachment_level='action_set',
                action_index=None,
                description=attachment_data.get('description'),
                sequence_order=attachment_data.get('sequence_order', 1),
                is_required=attachment_data.get('is_required', False),
                is_finalized=False,
                created_by_id=self._builder_memory.created_by_id,
                updated_by_id=self._builder_memory.updated_by_id
            )
            db.session.add(builder_att_ref)
        
        self._save()
        return attachment
    
    def remove_attachment(self, attachment_index: int):
        """
        Remove an action-set level attachment by index.
        
        Args:
            attachment_index: Index of attachment to remove
        """
        if 0 <= attachment_index < len(self._build_attachments):
            self._build_attachments.pop(attachment_index)
            self._save()
        else:
            raise IndexError(f"Attachment index {attachment_index} out of range")
    
    def add_attachment_to_action(
        self, 
        action_index: int, 
        attachment_data: Dict[str, Any], 
        is_new_upload: bool = False, 
        attachment_id: Optional[int] = None
    ) -> BuildAttachment:
        """
        Add an attachment to an action.
        
        Args:
            action_index: Index of action
            attachment_data: Dictionary containing attachment reference fields
            is_new_upload: If True, creates TemplateBuilderAttachmentReference record
            attachment_id: Attachment ID (required if is_new_upload is True)
            
        Returns:
            BuildAttachment: The created attachment wrapper
        """
        if 0 <= action_index < len(self._build_actions):
            attachment = self._build_actions[action_index].add_attachment(attachment_data)
            
            # Create TemplateBuilderAttachmentReference for new uploads only
            if is_new_upload and attachment_id:
                builder_att_ref = TemplateBuilderAttachmentReference(
                    template_builder_memory_id=self.builder_id,
                    attachment_id=attachment_id,
                    attachment_level='action',
                    action_index=action_index,
                    description=attachment_data.get('description'),
                    sequence_order=attachment_data.get('sequence_order', 1),
                    is_required=attachment_data.get('is_required', False),
                    is_finalized=False,
                    created_by_id=self._builder_memory.created_by_id,
                    updated_by_id=self._builder_memory.updated_by_id
                )
                db.session.add(builder_att_ref)
            
            self._save()
            return attachment
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    def remove_attachment_from_action(self, action_index: int, attachment_index: int):
        """
        Remove an attachment from an action.
        
        Args:
            action_index: Index of action
            attachment_index: Index of attachment to remove
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions[action_index].remove_attachment(attachment_index)
            self._save()
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    def unlink_proto_from_action(self, action_index: int):
        """
        Unlink proto action reference from an action (keeps all copied data).
        
        Args:
            action_index: Index of action
        """
        if 0 <= action_index < len(self._build_actions):
            self._build_actions[action_index].unlink_proto_action()
            self._save()
        else:
            raise IndexError(f"Action index {action_index} out of range")
    
    # Edit functions - metadata getters/setters
    def get_all_metadata(self) -> Dict[str, Any]:
        """Get all metadata as dictionary."""
        return dict(self._build_metadata)
    
    def get_metadata(self, key: str) -> Any:
        """Get metadata value by key."""
        return self._build_metadata.get(key)
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata value by key."""
        valid_fields = self._get_valid_metadata_fields()
        if key in valid_fields:
            if value is None:
                self._build_metadata.pop(key, None)
            else:
                self._build_metadata[key] = value
            self._save()
        else:
            raise ValueError(f"Invalid metadata field: {key}")
    
    # Convenience properties for common metadata fields
    @property
    def task_name(self) -> Optional[str]:
        """Get task_name."""
        return self._build_metadata.get('task_name')
    
    @task_name.setter
    def task_name(self, value: Optional[str]):
        """Set task_name."""
        self.set_metadata('task_name', value)
    
    @property
    def description(self) -> Optional[str]:
        """Get description."""
        return self._build_metadata.get('description')
    
    @description.setter
    def description(self, value: Optional[str]):
        """Set description."""
        self.set_metadata('description', value)
    
    # Sequence order management
    def _get_next_sequence_order(self) -> int:
        """Get next available sequence order."""
        if not self._build_actions:
            return 1
        max_order = max((action.sequence_order or 0 for action in self._build_actions), default=0)
        return max_order + 1
    
    def _renumber_sequence_orders(self):
        """Renumber all sequence orders to be consecutive starting from 1."""
        for index, action in enumerate(self._build_actions, start=1):
            action.sequence_order = index
    
    # Save and serialization
    def _save(self):
        """Save current build state to database."""
        build_state = {
            'metadata': self._build_metadata,
            'actions': [action.to_dict() for action in self._build_actions],
            'attachments': [att.to_dict() for att in self._build_attachments]
        }

        if build_state:
            self._builder_memory.set_build_state_dict(build_state)
            self._builder_memory.updated_at = datetime.utcnow()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.builder_id,
            'name': self.name,
            'build_type': self.build_type,
            'build_status': self.build_status,
            'metadata': self._build_metadata,
            'actions': [action.to_dict() for action in self._build_actions],
            'attachments': [att.to_dict() for att in self._build_attachments]
        }
    
    # Template creation
    def submit_template(self, user_id: Optional[int] = None) -> TemplateMaintenanceContext:
        """
        Convert build state to actual TemplateActionSet and related records.
        
        Args:
            user_id: User ID creating the template
            
        Returns:
            TemplateMaintenanceContext: Context for the created template
            
        Raises:
            ValueError: If validation fails or creation fails
        """
        if not user_id:
            user_id = self._builder_memory.created_by_id
        
        # Validate required fields
        if not self._build_metadata.get('task_name'):
            raise ValueError("task_name is required")
        
        # Start transaction
        try:
            # Determine prior_revision_id: use src_revision_id from TemplateBuilderMemory if this is a revision,
            # otherwise use prior_revision_id from metadata
            if self._builder_memory.is_revision and self._builder_memory.src_revision_id:
                prior_revision_id = self._builder_memory.src_revision_id
            else:
                prior_revision_id = self._build_metadata.get('prior_revision_id')
            
            # Get revision number from metadata (should be set correctly by copy_from_template or default to '0')
            revision = self._build_metadata.get('revision', '0')
            
            # Create TemplateActionSet
            template_action_set = TemplateActionSet(
                task_name=self._build_metadata['task_name'],
                description=self._build_metadata.get('description'),
                estimated_duration=self._build_metadata.get('estimated_duration'),
                safety_review_required=self._build_metadata.get('safety_review_required', False),
                staff_count=self._build_metadata.get('staff_count'),
                parts_cost=self._build_metadata.get('parts_cost'),
                labor_hours=self._build_metadata.get('labor_hours'),
                revision=revision,
                prior_revision_id=prior_revision_id,
                is_active=self._build_metadata.get('is_active', True),
                maintenance_plan_id=None,  # Not assigned during building
                asset_type_id=self._build_metadata.get('asset_type_id'),
                make_model_id=self._build_metadata.get('make_model_id'),
                created_by_id=user_id,
                updated_by_id=user_id
            )
            db.session.add(template_action_set)
            db.session.flush()  # Get ID
            
            # Create TemplateActionItems
            for build_action in self._build_actions:
                if not build_action.action_name:
                    raise ValueError(f"Action at sequence_order {build_action.sequence_order} missing action_name")
                if build_action.sequence_order is None:
                    raise ValueError(f"Action '{build_action.action_name}' missing sequence_order")
                
                template_action_item = TemplateActionItem(
                    template_action_set_id=template_action_set.id,
                    action_name=build_action.action_name,
                    description=build_action.description,
                    estimated_duration=build_action.estimated_duration,
                    expected_billable_hours=build_action._data.get('expected_billable_hours'),
                    safety_notes=build_action._data.get('safety_notes'),
                    notes=build_action._data.get('notes'),
                    sequence_order=build_action.sequence_order,
                    is_required=build_action._data.get('is_required', True),
                    instructions=build_action._data.get('instructions'),
                    instructions_type=build_action._data.get('instructions_type'),
                    minimum_staff_count=build_action._data.get('minimum_staff_count', 1),
                    required_skills=build_action._data.get('required_skills'),
                    proto_action_item_id=build_action.proto_action_item_id,
                    revision=build_action._data.get('revision'),
                    prior_revision_id=build_action._data.get('prior_revision_id'),
                    created_by_id=user_id,
                    updated_by_id=user_id
                )
                db.session.add(template_action_item)
                db.session.flush()  # Get ID
                
                # Create TemplatePartDemands
                for seq, part_demand in enumerate(build_action.part_demands, start=1):
                    from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
                    template_part_demand = TemplatePartDemand(
                        template_action_item_id=template_action_item.id,
                        part_id=part_demand.part_id,
                        quantity_required=part_demand.quantity_required,
                        expected_cost=part_demand.expected_cost,
                        notes=part_demand.notes,
                        is_optional=part_demand._data.get('is_optional', False),  # Default to required (not optional)
                        sequence_order=seq,
                        created_by_id=user_id,
                        updated_by_id=user_id
                    )
                    db.session.add(template_part_demand)
                
                # Create TemplateActionTools
                for seq, tool in enumerate(build_action.tools, start=1):
                    from app.data.maintenance.templates.template_action_tools import TemplateActionTool
                    template_tool = TemplateActionTool(
                        template_action_item_id=template_action_item.id,
                        tool_id=tool.tool_id,
                        quantity_required=tool.quantity_required,
                        notes=tool.notes,
                        is_required=tool._data.get('is_required', True),  # Default to required
                        sequence_order=seq,
                        created_by_id=user_id,
                        updated_by_id=user_id
                    )
                    db.session.add(template_tool)
                
                # Create TemplateActionAttachments
                for seq, attachment in enumerate(build_action.attachments, start=1):
                    template_attachment = TemplateActionAttachment(
                        template_action_item_id=template_action_item.id,
                        attachment_id=attachment.attachment_id,
                        all_attachment_references_id=None,  # Will be set by VirtualAttachmentReference.__init__
                        attached_to_type='TemplateActionItem',
                        display_order=seq,
                        attachment_type=attachment.attachment_type or 'Document',
                        caption=attachment.caption,
                        description=attachment.description,
                        sequence_order=attachment.sequence_order or seq,
                        is_required=attachment.is_required or False,
                        created_by_id=user_id,
                        updated_by_id=user_id
                    )
                    db.session.add(template_attachment)
            
            # Create TemplateActionSetAttachments
            for seq, attachment in enumerate(self._build_attachments, start=1):
                template_attachment = TemplateActionSetAttachment(
                    template_action_set_id=template_action_set.id,
                    attachment_id=attachment.attachment_id,
                    all_attachment_references_id=None,  # Will be set by VirtualAttachmentReference.__init__
                    attached_to_type='TemplateActionSet',
                    display_order=seq,
                    attachment_type=attachment.attachment_type or 'Document',
                    caption=attachment.caption,
                    description=attachment.description,
                    sequence_order=attachment.sequence_order or seq,
                    is_required=attachment.is_required or False,
                    created_by_id=user_id,
                    updated_by_id=user_id
                )
                db.session.add(template_attachment)
            
            # Finalize all TemplateBuilderAttachmentReference records for this builder
            builder_att_refs = TemplateBuilderAttachmentReference.query.filter_by(
                template_builder_memory_id=self.builder_id,
                is_finalized=False
            ).all()
            for builder_att_ref in builder_att_refs:
                builder_att_ref.is_finalized = True
                builder_att_ref.updated_by_id = user_id
            
            # Commit transaction
            db.session.commit()
            
            # Update builder status and save template reference
            self._builder_memory.build_status = 'Submitted'
            self._builder_memory.template_action_set_id = template_action_set.id
            self._builder_memory.updated_by_id = user_id
            self._save()
            
            # Return template context
            return TemplateMaintenanceContext(template_action_set.id)
            
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Failed to create template: {str(e)}") from e
    
    def __repr__(self):
        return f'<TemplateBuilderContext id={self.builder_id} name="{self.name}" status={self.build_status} actions={len(self._build_actions)}>'

