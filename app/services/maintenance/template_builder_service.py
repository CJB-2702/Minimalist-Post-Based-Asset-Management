"""
Template Builder Service
Service layer for template builder presentation operations.
Handles form data conversion and data preparation for templates.
"""

from typing import Dict, Any, Optional, List
import json
from app.buisness.maintenance.builders.template_builder_context import TemplateBuilderContext
from app.data.maintenance.builders.template_builder_memory import TemplateBuilderMemory
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app.data.core.supply.part import Part
from app.data.core.supply.tool import Tool


class TemplateBuilderService:
    """
    Service for template builder presentation operations.
    Handles form data conversion and prepares data for templates.
    """
    
    @staticmethod
    def get_builder_data(builder_id: int) -> Dict[str, Any]:
        """
        Get builder data formatted for template rendering.
        
        Args:
            builder_id: ID of the template builder
            
        Returns:
            Dictionary with builder data formatted for template
        """
        context = TemplateBuilderContext(builder_id)
        
        # Format actions for template
        actions_data = []
        for idx, action in enumerate(context.build_actions):
            actions_data.append({
                'index': idx,
                'sequence_order': action.sequence_order,
                'action_name': action.action_name or 'Unnamed Action',
                'description': action.description or '',
                'estimated_duration': action.estimated_duration,
                'part_count': len(action.part_demands),
                'tool_count': len(action.tools),
                'attachment_count': len(action.attachments),
                'part_demands': [
                    {
                        'part_id': pd.part_id,
                        'quantity_required': pd.quantity_required,
                        'expected_cost': pd.expected_cost,
                        'notes': pd.notes,
                        'part': TemplateBuilderService._get_part_info(pd.part_id) if pd.part_id else None,
                    }
                    for pd in action.part_demands
                ],
                'tools': [
                    {
                        'tool_id': tool.tool_id,
                        'quantity_required': tool.quantity_required,
                        'notes': tool.notes,
                        'tool': TemplateBuilderService._get_tool_info(tool.tool_id) if tool.tool_id else None,
                    }
                    for tool in action.tools
                ],
                'attachments': [
                    {
                        'attachment_id': att.attachment_id,
                        'description': att.description,
                        'sequence_order': att.sequence_order,
                        'is_required': att.is_required,
                    }
                    for att in action.attachments
                ],
                'has_proto_reference': action.proto_action_item_id is not None,
                'proto_action_item_id': action.proto_action_item_id,
            })
        
        # Get builder memory to access revision fields
        builder_memory = TemplateBuilderMemory.query.get(builder_id)
        is_revision = builder_memory.is_revision if builder_memory else False
        
        # Get revision from metadata, default to '0' for new builds
        revision = context.get_metadata('revision')
        if revision is None and not is_revision:
            revision = '0'
        
        return {
            'builder_id': builder_id,
            'name': context.name,
            'build_type': context.build_type,
            'build_status': context.build_status,
            'is_revision': is_revision,
            'src_revision_id': builder_memory.src_revision_id if builder_memory else None,
            'src_revision_number': builder_memory.src_revision_number if builder_memory else None,
            'metadata': {
                'task_name': context.task_name or '',
                'description': context.description or '',
                'estimated_duration': context.get_metadata('estimated_duration'),
                'revision': revision,
                'safety_review_required': context.get_metadata('safety_review_required') if context.get_metadata('safety_review_required') is not None else False,
                'staff_count': context.get_metadata('staff_count'),
                'parts_cost': context.get_metadata('parts_cost'),
                'labor_hours': context.get_metadata('labor_hours'),
            },
            'actions': actions_data,
            'total_actions': len(actions_data),
        }
    
    @staticmethod
    def _get_part_info(part_id: int) -> Optional[Dict[str, Any]]:
        """
        Get part information by ID.
        
        Args:
            part_id: Part ID
            
        Returns:
            Dictionary with part information or None if not found
        """
        try:
            part = Part.query.get(part_id)
            if part:
                return {
                    'id': part.id,
                    'part_number': part.part_number,
                    'part_name': part.part_name,
                    'description': part.description,
                    'unit_cost': part.unit_cost,
                }
        except Exception:
            pass
        return None
    
    @staticmethod
    def _get_tool_info(tool_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tool information by ID.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Dictionary with tool information or None if not found
        """
        try:
            tool = Tool.query.get(tool_id)
            if tool:
                return {
                    'id': tool.id,
                    'tool_name': tool.tool_name,
                    'description': tool.description,
                    'tool_type': tool.tool_type,
                    'manufacturer': tool.manufacturer,
                    'model_number': tool.model_number,
                }
        except Exception:
            pass
        return None
    
    @staticmethod
    def get_builder_json(builder_id: int) -> str:
        """
        Get builder context as formatted JSON string.
        
        Args:
            builder_id: ID of the template builder
            
        Returns:
            Formatted JSON string representation of the builder context
        """
        context = TemplateBuilderContext(builder_id)
        context_dict = context.to_dict()
        return json.dumps(context_dict, indent=2, default=str)
    
    @staticmethod
    def get_action_detail_data(builder_id: int, action_index: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed data for a specific action.
        
        Args:
            builder_id: ID of the template builder
            action_index: Index of the action
            
        Returns:
            Dictionary with action detail data or None if not found
        """
        try:
            context = TemplateBuilderContext(builder_id)
            if 0 <= action_index < len(context.build_actions):
                action = context.build_actions[action_index]
                
                return {
                    'index': action_index,
                    'sequence_order': action.sequence_order,
                    'action_name': action.action_name or '',
                    'description': action.description or '',
                    'estimated_duration': action.estimated_duration,
                    'expected_billable_hours': action._data.get('expected_billable_hours'),
                    'safety_notes': action._data.get('safety_notes'),
                    'notes': action._data.get('notes'),
                    'is_required': action._data.get('is_required', True),
                    'instructions': action._data.get('instructions'),
                    'instructions_type': action._data.get('instructions_type'),
                    'minimum_staff_count': action._data.get('minimum_staff_count', 1),
                    'required_skills': action._data.get('required_skills'),
                    'proto_action_item_id': action.proto_action_item_id,
                    'part_demands': [
                        {
                            'index': idx,
                            'part_id': pd.part_id,
                            'quantity_required': pd.quantity_required,
                            'expected_cost': pd.expected_cost,
                            'notes': pd.notes,
                        }
                        for idx, pd in enumerate(action.part_demands)
                    ],
                    'tools': [
                        {
                            'index': idx,
                            'tool_id': tool.tool_id,
                            'quantity_required': tool.quantity_required,
                            'notes': tool.notes,
                        }
                        for idx, tool in enumerate(action.tools)
                    ],
                }
        except Exception:
            return None
    
    @staticmethod
    def convert_form_to_action_dict(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert form data to action dictionary for business layer.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Dictionary suitable for BuildAction.from_dict()
        """
        action_dict = {}
        
        # Convert string fields
        if form_data.get('action_name'):
            action_dict['action_name'] = form_data['action_name'].strip()
        if form_data.get('description'):
            action_dict['description'] = form_data['description'].strip()
        
        # Convert numeric fields
        if form_data.get('estimated_duration'):
            try:
                action_dict['estimated_duration'] = float(form_data['estimated_duration'])
            except (ValueError, TypeError):
                pass
        
        if form_data.get('expected_billable_hours'):
            try:
                action_dict['expected_billable_hours'] = float(form_data['expected_billable_hours'])
            except (ValueError, TypeError):
                pass
        
        # Convert text fields
        if form_data.get('safety_notes'):
            action_dict['safety_notes'] = form_data['safety_notes'].strip()
        if form_data.get('notes'):
            action_dict['notes'] = form_data['notes'].strip()
        if form_data.get('instructions'):
            action_dict['instructions'] = form_data['instructions'].strip()
        if form_data.get('instructions_type'):
            action_dict['instructions_type'] = form_data['instructions_type'].strip()
        if form_data.get('required_skills'):
            action_dict['required_skills'] = form_data['required_skills'].strip()
        
        # Convert boolean/integer fields
        if form_data.get('is_required') is not None:
            action_dict['is_required'] = form_data.get('is_required') in ('true', 'True', '1', True, 1)
        
        if form_data.get('minimum_staff_count'):
            try:
                action_dict['minimum_staff_count'] = int(form_data['minimum_staff_count'])
            except (ValueError, TypeError):
                pass
        
        return action_dict
    
    @staticmethod
    def convert_form_to_part_dict(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert form data to part demand dictionary.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Dictionary suitable for BuildPartDemand
        """
        part_dict = {}
        
        if form_data.get('part_id'):
            try:
                part_dict['part_id'] = int(form_data['part_id'])
            except (ValueError, TypeError):
                pass
        
        if form_data.get('quantity_required'):
            try:
                part_dict['quantity_required'] = float(form_data['quantity_required'])
            except (ValueError, TypeError):
                part_dict['quantity_required'] = 1.0
        
        if form_data.get('expected_cost'):
            try:
                part_dict['expected_cost'] = float(form_data['expected_cost'])
            except (ValueError, TypeError):
                pass
        
        if form_data.get('notes'):
            part_dict['notes'] = form_data['notes'].strip()
        
        return part_dict
    
    @staticmethod
    def convert_form_to_tool_dict(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert form data to tool dictionary.
        
        Args:
            form_data: Form data from request
            
        Returns:
            Dictionary suitable for BuildActionTool
        """
        tool_dict = {}
        
        if form_data.get('tool_id'):
            try:
                tool_dict['tool_id'] = int(form_data['tool_id'])
            except (ValueError, TypeError):
                pass
        
        if form_data.get('quantity_required'):
            try:
                tool_dict['quantity_required'] = int(form_data['quantity_required'])
            except (ValueError, TypeError):
                tool_dict['quantity_required'] = 1
        
        if form_data.get('notes'):
            tool_dict['notes'] = form_data['notes'].strip()
        
        return tool_dict
    
    @staticmethod
    def get_available_templates(
        search_id: Optional[int] = None,
        search_name: Optional[str] = None,
        asset_type_id: Optional[int] = None,
        make_model_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of available templates for copying with action summaries.
        
        Args:
            search_id: Filter by template ID
            search_name: Filter by task name (partial match)
            asset_type_id: Filter by asset type ID
            make_model_id: Filter by make/model ID
            
        Returns:
            List of template dictionaries with id, task_name, revision, and actions
        """
        from app.buisness.maintenance.templates.template_action_context import TemplateActionContext
        from app.buisness.maintenance.templates.template_maintenance_context import TemplateMaintenanceContext
        
        # Build query
        query = TemplateActionSet.query.filter_by(is_active=True)
        
        # Apply filters
        if search_id:
            query = query.filter_by(id=search_id)
        if search_name:
            query = query.filter(TemplateActionSet.task_name.ilike(f'%{search_name}%'))
        if asset_type_id:
            query = query.filter_by(asset_type_id=asset_type_id)
        if make_model_id:
            query = query.filter_by(make_model_id=make_model_id)
        
        templates = query.order_by(TemplateActionSet.task_name).all()
        result = []
        
        for template in templates:
            template_context = TemplateMaintenanceContext(template.id)
            actions = TemplateActionContext.get_by_template_action_set(template.id)
            
            result.append({
                'id': template.id,
                'task_name': template.task_name,
                'description': template.description,
                'revision': template.revision,
                'asset_type_id': template.asset_type_id,
                'make_model_id': template.make_model_id,
                'total_actions': len(actions),
                'actions': [
                    {
                        'sequence_order': action._struct.sequence_order,
                        'action_name': action._struct.action_name,
                        'description': action._struct.description,
                        'estimated_duration': action._struct.template_action_item.estimated_duration if action._struct.template_action_item else None,
                        'part_count': action.total_part_demands,
                        'tool_count': action.total_action_tools,
                    }
                    for action in actions
                ],
            })
        
        return result

