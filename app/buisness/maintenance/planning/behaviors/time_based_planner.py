"""
Time-Based Planner Behavior
Handles planning for frequency types: hours, days
"""

from typing import List, Optional
from datetime import datetime, timedelta
from app.data.core.asset_info.asset import Asset
from app.buisness.maintenance.planning.maintenance_plan_context import MaintenancePlanContext
from app.buisness.maintenance.planning.planning_result import PlanningResult
from app.buisness.maintenance.planning.base_planner_behavior import BasePlannerBehavior
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.templates.template_action_sets import TemplateActionSet
from app import db


class TimeBasedPlanner(BasePlannerBehavior):
    """Planner behavior for time-based maintenance (hours, days)"""
    
    def find_assets_needing_maintenance(
        self, 
        plan_context: MaintenancePlanContext
    ) -> List[PlanningResult]:
        """
        Find assets that need maintenance based on time since last maintenance.
        
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
                
                # Calculate due date
                due_date = self.calculate_due_date(
                    asset,
                    plan_context,
                    last_maintenance
                )
                
                # Calculate days since last maintenance
                days_since = None
                last_maintenance_date = None
                if last_maintenance and last_maintenance.end_date:
                    last_maintenance_date = last_maintenance.end_date
                    days_since = (datetime.utcnow() - last_maintenance_date).total_seconds() / 86400
                elif asset.created_at:
                    # Use asset creation date as baseline if no maintenance
                    last_maintenance_date = asset.created_at
                    days_since = (datetime.utcnow() - last_maintenance_date).total_seconds() / 86400
                
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
                if last_maintenance and last_maintenance.meter_reading:
                    meter_reading = last_maintenance.meter_reading
                    meter_readings_at_last = {
                        'meter1': meter_reading.meter1,
                        'meter2': meter_reading.meter2,
                        'meter3': meter_reading.meter3,
                        'meter4': meter_reading.meter4
                    }
                
                # Determine reason
                reason = self._determine_reason(
                    plan_context,
                    needs_maintenance,
                    days_since,
                    last_maintenance_date
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
        
        Args:
            asset: Asset to calculate due date for
            plan_context: MaintenancePlanContext for the plan
            last_maintenance: Last completed maintenance (if available)
            
        Returns:
            Due date or None if cannot be calculated
        """
        frequency_type = plan_context.maintenance_plan.frequency_type
        plan = plan_context.maintenance_plan
        
        # Determine baseline date
        if last_maintenance and last_maintenance.end_date:
            baseline_date = last_maintenance.end_date
        elif asset.created_at:
            baseline_date = asset.created_at
        else:
            return None
        
        # Calculate based on frequency type
        if frequency_type == 'hours':
            # For hours, use delta_days and convert to hours
            # Note: delta_days stores the value, for hours we interpret it as hours
            if plan.delta_days:
                return baseline_date + timedelta(hours=plan.delta_days)
            else:
                # Default to 24 hours if no delta specified
                return baseline_date + timedelta(hours=24)
        elif frequency_type == 'days':
            if plan.delta_days:
                return baseline_date + timedelta(days=plan.delta_days)
            else:
                # Default to 30 days if no delta specified
                return baseline_date + timedelta(days=30)
        
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
        plan = plan_context.maintenance_plan
        now = datetime.utcnow()
        
        # Determine baseline date
        if last_maintenance and last_maintenance.end_date:
            baseline_date = last_maintenance.end_date
        elif asset.created_at:
            baseline_date = asset.created_at
        else:
            # No baseline, can't determine - default to needing maintenance
            return True
        
        # Calculate time since baseline
        time_delta = now - baseline_date
        
        # Check against threshold
        if frequency_type == 'hours':
            # For hours, use delta_days and interpret as hours
            if plan.delta_days:
                hours_elapsed = time_delta.total_seconds() / 3600
                return hours_elapsed >= plan.delta_days
        elif frequency_type == 'days':
            if plan.delta_days:
                days_elapsed = time_delta.total_seconds() / 86400
                return days_elapsed >= plan.delta_days
        
        # If no threshold set, default to needing maintenance
        return True
    
    def _determine_reason(
        self,
        plan_context: MaintenancePlanContext,
        needs_maintenance: bool,
        days_since: Optional[float],
        last_maintenance_date: Optional[datetime]
    ) -> str:
        """Determine the reason for the planning result"""
        frequency_type = plan_context.maintenance_plan.frequency_type
        
        if not needs_maintenance:
            if last_maintenance_date:
                return f"Maintenance not yet due. Last maintenance: {last_maintenance_date.strftime('%Y-%m-%d')}"
            else:
                return "No previous maintenance found, but threshold not yet exceeded"
        
        if frequency_type == 'hours':
            delta = plan_context.maintenance_plan.delta_days  # For hours, delta_days stores hours value
            if days_since:
                hours_since = days_since * 24
                return f"Hours threshold ({delta}) exceeded. {hours_since:.1f} hours since last maintenance"
            return f"Hours threshold ({delta}) exceeded"
        elif frequency_type == 'days':
            delta = plan_context.maintenance_plan.delta_days
            if delta and days_since:
                return f"Days threshold ({delta}) exceeded. {days_since:.1f} days since last maintenance"
            return f"Days threshold exceeded"
        
        return "Maintenance needed based on time-based criteria"

