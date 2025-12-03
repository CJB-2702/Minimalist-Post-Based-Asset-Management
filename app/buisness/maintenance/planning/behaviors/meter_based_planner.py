"""
Meter-Based Planner Behavior
Handles planning for frequency types: meter1, meter2, meter3, meter4
"""

from typing import List, Optional
from datetime import datetime
from app.data.core.asset_info.asset import Asset
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.buisness.maintenance.planning.planning_result import PlanningResult
from app.buisness.maintenance.planning.base_planner_behavior import BasePlannerBehavior
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app import db


class MeterBasedPlanner(BasePlannerBehavior):
    """Planner behavior for meter-based maintenance (meter1-4)"""
    
    def find_assets_needing_maintenance(
        self, 
        plan_context: MaintenancePlanContext
    ) -> List[PlanningResult]:
        """
        Find assets that need maintenance based on meter readings.
        
        Args:
            plan_context: MaintenancePlanContext for the plan to analyze
            
        Returns:
            List of PlanningResult objects
        """
        results = []
        matching_assets = plan_context.get_matching_assets()
        
        # Filter to active assets only
        active_assets = [asset for asset in matching_assets if asset.is_active]
        
        template_action_set = plan_context.template_action_set
        frequency_type = plan_context.maintenance_plan.frequency_type
        
        # Determine which meter field to use
        meter_field = self._get_meter_field(frequency_type)
        if not meter_field:
            # Invalid frequency type
            return results
        
        for asset in active_assets:
            try:
                # Find last completed maintenance
                last_maintenance = self.find_last_relevant_maintenance(
                    asset, 
                    template_action_set
                )
                
                # Determine if maintenance is needed
                needs_maintenance = self.should_create_maintenance(
                    asset,
                    plan_context,
                    last_maintenance
                )
                
                # Calculate due date (for meter-based, this is less meaningful)
                due_date = self.calculate_due_date(
                    asset,
                    plan_context,
                    last_maintenance
                )
                
                # Get current meter readings
                current_meter_readings = {
                    'meter1': asset.meter1,
                    'meter2': asset.meter2,
                    'meter3': asset.meter3,
                    'meter4': asset.meter4
                }
                
                # Get meter readings at last maintenance
                meter_readings_at_last = {
                    'meter1': None,
                    'meter2': None,
                    'meter3': None,
                    'meter4': None
                }
                meter_delta = {
                    'meter1': None,
                    'meter2': None,
                    'meter3': None,
                    'meter4': None
                }
                
                if last_maintenance and last_maintenance.meter_reading:
                    meter_reading = last_maintenance.meter_reading
                    meter_readings_at_last = {
                        'meter1': meter_reading.meter1,
                        'meter2': meter_reading.meter2,
                        'meter3': meter_reading.meter3,
                        'meter4': meter_reading.meter4
                    }
                    
                    # Calculate meter deltas
                    current = current_meter_readings[meter_field]
                    last = meter_readings_at_last[meter_field]
                    if current is not None and last is not None:
                        meter_delta[meter_field] = current - last
                
                # Calculate days since last maintenance
                days_since = None
                last_maintenance_date = None
                if last_maintenance and last_maintenance.end_date:
                    last_maintenance_date = last_maintenance.end_date
                    days_since = (datetime.utcnow() - last_maintenance_date).total_seconds() / 86400
                elif asset.created_at:
                    last_maintenance_date = asset.created_at
                    days_since = (datetime.utcnow() - last_maintenance_date).total_seconds() / 86400
                
                # Determine reason
                reason = self._determine_reason(
                    plan_context,
                    needs_maintenance,
                    meter_field,
                    current_meter_readings.get(meter_field),
                    meter_readings_at_last.get(meter_field),
                    meter_delta.get(meter_field)
                )
                
                # Recommended start date (default to now if due)
                recommended_start_date = datetime.utcnow() if needs_maintenance else None
                
                result = PlanningResult(
                    asset_id=asset.id,
                    asset=asset,
                    maintenance_plan_id=plan_context.id,
                    maintenance_plan=plan_context,
                    needs_maintenance=needs_maintenance,
                    reason=reason,
                    due_date=due_date,
                    last_maintenance_date=last_maintenance_date,
                    last_maintenance=last_maintenance,
                    current_meter_readings=current_meter_readings,
                    meter_readings_at_last_maintenance=meter_readings_at_last,
                    days_since_last_maintenance=days_since,
                    meter_delta=meter_delta,
                    recommended_start_date=recommended_start_date
                )
                
                results.append(result)
                
            except Exception as e:
                # Create error result
                error_result = PlanningResult(
                    asset_id=asset.id,
                    asset=asset,
                    maintenance_plan_id=plan_context.id,
                    maintenance_plan=plan_context,
                    needs_maintenance=False,
                    reason=f"Error analyzing asset: {str(e)}",
                    errors=[str(e)]
                )
                results.append(error_result)
        
        return results
    
    def calculate_due_date(
        self,
        asset: Asset,
        plan_context: MaintenancePlanContext,
        last_maintenance: Optional[MaintenanceActionSet] = None
    ) -> Optional[datetime]:
        """
        Calculate when maintenance is due for a specific asset.
        For meter-based planning, this is less meaningful but can estimate based on usage.
        
        Args:
            asset: Asset to calculate due date for
            plan_context: MaintenancePlanContext for the plan
            last_maintenance: Last completed maintenance (if available)
            
        Returns:
            Due date or None if cannot be calculated
        """
        # For meter-based, we can't really predict a due date
        # Return None to indicate it's meter-based
        return None
    
    def find_last_relevant_maintenance(
        self,
        asset: Asset,
        maintenance_template_action_set: TemplateActionSet
    ) -> Optional[MaintenanceActionSet]:
        """
        Find the last completed maintenance for an asset that matches the template.
        
        Args:
            asset: Asset to find maintenance for
            maintenance_template_action_set: TemplateActionSet to match against
            
        Returns:
            MaintenanceActionSet or None if no maintenance found
        """
        # Query for completed maintenance with matching template
        last_maintenance = (
            MaintenanceActionSet.query
            .filter_by(
                asset_id=asset.id,
                template_action_set_id=maintenance_template_action_set.id,
                status='Completed'
            )
            .order_by(MaintenanceActionSet.end_date.desc())
            .first()
        )
        
        return last_maintenance
    
    def should_create_maintenance(
        self,
        asset: Asset,
        plan_context: MaintenancePlanContext,
        last_maintenance: Optional[MaintenanceActionSet] = None
    ) -> bool:
        """
        Determine if maintenance should be created for this asset.
        
        Args:
            asset: Asset to check
            plan_context: MaintenancePlanContext for the plan
            last_maintenance: Last completed maintenance (if available)
            
        Returns:
            True if maintenance should be created
        """
        frequency_type = plan_context.maintenance_plan.frequency_type
        meter_field = self._get_meter_field(frequency_type)
        
        if not meter_field:
            return False
        
        # Get current meter reading
        current_meter = getattr(asset, meter_field, None)
        if current_meter is None:
            # No current meter reading - can't determine
            return False
        
        # Get meter reading at last maintenance
        last_meter = None
        if last_maintenance and last_maintenance.meter_reading:
            last_meter = getattr(last_maintenance.meter_reading, meter_field, None)
        
        # If no previous meter reading, compare to 0
        if last_meter is None:
            last_meter = 0
        
        # Calculate delta
        meter_delta = current_meter - last_meter
        
        # Check for meter rollover (meter decreased)
        if meter_delta < 0:
            # Meter may have been reset or replaced - treat as if no previous reading
            last_meter = 0
            meter_delta = current_meter
        
        # Get threshold delta
        delta_threshold = self._get_delta_threshold(plan_context, frequency_type)
        if delta_threshold is None:
            return False
        
        # Check if threshold exceeded
        return meter_delta >= delta_threshold
    
    def _get_meter_field(self, frequency_type: str) -> Optional[str]:
        """Get the meter field name from frequency type"""
        meter_map = {
            'meter1': 'meter1',
            'meter2': 'meter2',
            'meter3': 'meter3',
            'meter4': 'meter4'
        }
        return meter_map.get(frequency_type)
    
    def _get_delta_threshold(self, plan_context: MaintenancePlanContext, frequency_type: str) -> Optional[float]:
        """Get the delta threshold for the frequency type"""
        plan = plan_context.maintenance_plan
        delta_map = {
            'meter1': plan.delta_m1,
            'meter2': plan.delta_m2,
            'meter3': plan.delta_m3,
            'meter4': plan.delta_m4
        }
        return delta_map.get(frequency_type)
    
    def _determine_reason(
        self,
        plan_context: MaintenancePlanContext,
        needs_maintenance: bool,
        meter_field: str,
        current_meter: Optional[float],
        last_meter: Optional[float],
        meter_delta: Optional[float]
    ) -> str:
        """Determine the reason for the planning result"""
        frequency_type = plan_context.maintenance_plan.frequency_type
        delta_threshold = self._get_delta_threshold(plan_context, frequency_type)
        
        if not needs_maintenance:
            if current_meter is None:
                return f"No current {meter_field} reading available"
            if last_meter is None:
                return f"Meter threshold not yet reached. Current: {current_meter:.1f}, Threshold: {delta_threshold}"
            if meter_delta is not None:
                return f"Meter threshold not yet reached. Delta: {meter_delta:.1f}, Threshold: {delta_threshold}"
            return f"Meter threshold not yet reached"
        
        if current_meter is None:
            return f"Current {meter_field} reading not available"
        
        if meter_delta is not None and delta_threshold:
            return f"{meter_field.upper()} threshold ({delta_threshold}) exceeded. Delta: {meter_delta:.1f} (Current: {current_meter:.1f}, Last: {last_meter or 0:.1f})"
        
        return f"{meter_field.upper()} threshold exceeded"

