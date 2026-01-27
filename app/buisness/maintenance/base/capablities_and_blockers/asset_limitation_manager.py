"""
Asset Limitation Manager
Business logic for managing asset operational capability limitations.
"""

from typing import List, Optional
from datetime import datetime
from app import db
from app.data.maintenance.base.asset_limitation_records import AssetLimitationRecord
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset


class AssetLimitationManager:
    """
    Manages asset limitation records for a maintenance event.
    
    Tracks operational capability limitations separate from maintenance progress.
    Automatically updates Asset.capability_status based on active limitations.
    """
    
    # Status ranking (worst to best)
    STATUS_PRIORITY = {
        'Non Mission Capable': 1,
        'Partially Mission Capable - Functional Limitations': 2,
        'Partially Mission Capable - Temporary Compensation': 3,
        'Fully Mission Capable - Temporary Compensation': 4
    }
    
    def __init__(self, maintenance_action_set_id: int):
        """
        Initialize with maintenance action set ID.
        
        Args:
            maintenance_action_set_id: ID of the maintenance action set
        """
        self._maintenance_action_set_id = maintenance_action_set_id
        self._maintenance_action_set = MaintenanceActionSet.query.get(maintenance_action_set_id)
        if not self._maintenance_action_set:
            raise ValueError(f"MaintenanceActionSet {maintenance_action_set_id} not found")
    
    @property
    def asset_id(self) -> Optional[int]:
        """Get asset ID from maintenance action set"""
        return self._maintenance_action_set.asset_id
    
    @property
    def limitation_records(self) -> List[AssetLimitationRecord]:
        """Get all limitation records for this maintenance event"""
        return self._maintenance_action_set.limitation_records
    
    @property
    def active_limitations(self) -> List[AssetLimitationRecord]:
        """Get active limitation records (end_time is None)"""
        return [lr for lr in self.limitation_records if lr.is_active]
    
    def validate_modification_rules(self, status: str, temporary_modifications: Optional[str]) -> None:
        """
        Validate modification rules based on status.
        
        Rules:
        - Mission Capable statuses REQUIRE modifications
        - Degraded statuses FORBID modifications
        - Fully Mission Capable has NO modifications
        
        Args:
            status: Mission capability status
            temporary_modifications: Temporary modifications text
            
        Raises:
            ValueError: If modification rules are violated
        """
        compensation_statuses = [
            'Partially Mission Capable - Temporary Compensation',
            'Fully Mission Capable - Temporary Compensation'
        ]
        
        non_compensation_statuses = [
            'Non Mission Capable',
            'Partially Mission Capable - Functional Limitations'
        ]
        
        has_modifications = temporary_modifications and temporary_modifications.strip()
        
        # Rule 1: Compensation statuses REQUIRE modifications
        if status in compensation_statuses:
            if not has_modifications:
                raise ValueError(
                    f"Status '{status}' requires temporary modifications. "
                    "Compensation statuses must describe the compensation in place."
                )
        
        # Rule 2: Non-compensation statuses FORBID modifications
        if status in non_compensation_statuses:
            if has_modifications:
                raise ValueError(
                    f"Status '{status}' cannot have temporary modifications. "
                    "Only compensation statuses can have modifications."
                )
    
    def create_record(
        self,
        status: str,
        limitation_description: Optional[str] = None,
        temporary_modifications: Optional[str] = None,
        start_time: Optional[datetime] = None,
        maintenance_blocker_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> AssetLimitationRecord:
        """
        Create a new limitation record.
        
        Args:
            status: Mission capability status
            limitation_description: Description of what is limited
            temporary_modifications: Procedural/hardware compensations
            start_time: Start time (defaults to now)
            maintenance_blocker_id: Optional blocker that caused this limitation
            user_id: ID of user creating the record
            
        Returns:
            Created AssetLimitationRecord instance
            
        Raises:
            ValueError: If modification validation fails or active limitation already exists
        """
        # Check for existing active limitations
        if self.active_limitations:
            raise ValueError(
                "Cannot create a new limitation while an active limitation exists. "
                "Please close the existing limitation before creating a new one."
            )
        
        # Validate modification rules
        self.validate_modification_rules(status, temporary_modifications)
        
        # Create record
        record = AssetLimitationRecord(
            maintenance_action_set_id=self._maintenance_action_set_id,
            status=status,
            limitation_description=limitation_description,
            temporary_modifications=temporary_modifications,
            start_time=start_time or datetime.utcnow(),
            maintenance_blocker_id=maintenance_blocker_id,
            created_by_id=user_id or 1,
            updated_by_id=user_id or 1
        )
        
        db.session.add(record)
        db.session.commit()
        
        # Update asset capability status
        self.set_capability_status()
        
        return record
    
    def update_record(
        self,
        record_id: int,
        status: Optional[str] = None,
        limitation_description: Optional[str] = None,
        temporary_modifications: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> AssetLimitationRecord:
        """
        Update an existing limitation record.
        
        Args:
            record_id: ID of record to update
            status: New status (optional)
            limitation_description: New description (optional)
            temporary_modifications: New modifications (optional)
            user_id: ID of user making update
            
        Returns:
            Updated AssetLimitationRecord instance
            
        Raises:
            ValueError: If record not found or validation fails
        """
        record = AssetLimitationRecord.query.get(record_id)
        if not record:
            raise ValueError(f"AssetLimitationRecord {record_id} not found")
        
        if record.maintenance_action_set_id != self._maintenance_action_set_id:
            raise ValueError(f"Record {record_id} does not belong to this maintenance event")
        
        # Determine final status and modifications for validation
        final_status = status if status is not None else record.status
        final_modifications = temporary_modifications if temporary_modifications is not None else record.temporary_modifications
        
        # Validate modification rules
        self.validate_modification_rules(final_status, final_modifications)
        
        # Update fields
        if status is not None:
            record.status = status
        if limitation_description is not None:
            record.limitation_description = limitation_description
        if temporary_modifications is not None:
            record.temporary_modifications = temporary_modifications
        if user_id:
            record.updated_by_id = user_id
        
        db.session.commit()
        
        # Update asset capability status
        self.set_capability_status()
        
        return record
    
    def close_record(
        self,
        record_id: int,
        end_time: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        user_id: Optional[int] = None
    ) -> AssetLimitationRecord:
        """
        Close a limitation record.
        
        Args:
            record_id: ID of record to close
            end_time: End time (defaults to now)
            start_time: Optional updated start time
            user_id: ID of user closing record
            
        Returns:
            Updated AssetLimitationRecord instance
            
        Raises:
            ValueError: If record not found, already closed, or start_time after end_time
        """
        record = AssetLimitationRecord.query.get(record_id)
        if not record:
            raise ValueError(f"AssetLimitationRecord {record_id} not found")
        
        if record.maintenance_action_set_id != self._maintenance_action_set_id:
            raise ValueError(f"Record {record_id} does not belong to this maintenance event")
        
        if record.end_time:
            raise ValueError(f"Record {record_id} is already closed")
        
        # Determine final times
        final_end_time = end_time or datetime.utcnow()
        final_start_time = start_time if start_time is not None else record.start_time
        
        # Validate times
        if final_start_time > final_end_time:
            raise ValueError("Start time cannot be after end time")
        
        # Update record
        record.start_time = final_start_time
        record.end_time = final_end_time
        if user_id:
            record.updated_by_id = user_id
        
        db.session.commit()
        
        # Update asset capability status
        self.set_capability_status()
        
        return record
    
    def set_capability_status(self) -> None:
        """
        Query all open limitation records for the asset and set worst capability status.
        
        Sets Asset.capability_status to the worst (highest-ranked) open status,
        or None if no active limitations exist.
        """
        from app.logger import get_logger
        logger = get_logger("asset_management.limitation_manager")
        
        if not self.asset_id:
            logger.warning("No asset_id found, cannot update capability status")
            return
        
        # Flush any pending changes to ensure we query the latest data
        db.session.flush()
        
        # Query all active limitation records for this asset across all maintenance events
        active_records = db.session.query(AssetLimitationRecord).join(
            MaintenanceActionSet,
            AssetLimitationRecord.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.asset_id == self.asset_id,
            AssetLimitationRecord.end_time.is_(None)  # Only active records
        ).all()
        
        logger.info(f"Found {len(active_records)} active limitation records for asset {self.asset_id}")
        
        # Get asset
        asset = Asset.query.get(self.asset_id)
        if not asset:
            logger.error(f"Asset {self.asset_id} not found")
            return
        
        if not active_records:
            # No active limitations - asset is fully capable
            logger.info(f"No active limitations, setting asset {self.asset_id} capability_status to None (Fully Mission Capable)")
            asset.capability_status = None
            db.session.commit()
            return
        
        # Get all statuses from active records
        statuses = [r.status for r in active_records]
        logger.debug(f"Active limitation statuses: {statuses}")
        
        if not statuses:
            # No limiting statuses found - asset is fully capable
            logger.info(f"No statuses found, setting asset {self.asset_id} capability_status to None")
            asset.capability_status = None
            db.session.commit()
            return
        
        # Find worst status based on priority ranking
        worst_status = min(statuses, key=lambda s: self.STATUS_PRIORITY.get(s, 999))
        
        logger.info(f"Setting asset {self.asset_id} capability_status to '{worst_status}' (worst of {len(statuses)} active limitations)")
        
        # Update asset capability status
        asset.capability_status = worst_status
        db.session.commit()
        
        logger.debug(f"Asset {self.asset_id} capability_status updated successfully")
    
    def get_asset_all_limitations(self) -> List[AssetLimitationRecord]:
        """
        Get all limitation records for the asset (across all maintenance events).
        
        Returns:
            List of all AssetLimitationRecord instances for this asset
        """
        if not self.asset_id:
            return []
        
        return db.session.query(AssetLimitationRecord).join(
            MaintenanceActionSet,
            AssetLimitationRecord.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.asset_id == self.asset_id
        ).order_by(AssetLimitationRecord.start_time.desc()).all()

    @classmethod    
    def refresh_capability_status(cls, asset_id: int):
        """
        Refresh the capability_status by querying active limitations across all maintenance events.
        This is normally handled automatically by AssetLimitationManager.
        
        Args:
            asset_id: ID of the asset to refresh capability status for
        
        Returns:
            The updated capability_status (or None if no active limitations)
        """
        from app.data.maintenance.base.asset_limitation_records import AssetLimitationRecord
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.logger import get_logger
        logger = get_logger("asset_management.limitation_manager")
        
        # Get asset
        asset = Asset.query.get(asset_id)
        if not asset:
            logger.error(f"Asset {asset_id} not found")
            return None
        
        # Query all active limitation records for this asset
        active_records = db.session.query(AssetLimitationRecord).join(
            MaintenanceActionSet,
            AssetLimitationRecord.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.asset_id == asset_id,
            AssetLimitationRecord.end_time.is_(None)
        ).all()
        
        if not active_records:
            asset.capability_status = None
            logger.debug(f"Asset {asset_id} has no active limitations, capability_status set to None")
        else:
            # Use class-level STATUS_PRIORITY
            statuses = [r.status for r in active_records]
            worst_status = min(statuses, key=lambda s: cls.STATUS_PRIORITY.get(s, 999))
            asset.capability_status = worst_status
            logger.info(f"Asset {asset_id} capability_status set to '{worst_status}' from {len(active_records)} active limitations")
        
        db.session.commit()
        return asset.capability_status