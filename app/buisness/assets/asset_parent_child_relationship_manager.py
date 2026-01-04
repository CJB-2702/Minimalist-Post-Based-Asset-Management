"""
Asset Parent-Child Relationship Manager
Manages parent-child asset linkages with validation and history tracking.
"""

from typing import List, Optional, Union
from datetime import datetime
from app.data.core.asset_info.asset import Asset
from app.data.assets.asset_parent_history import AssetParentHistory
from app import db


class AssetParentChildRelationshipManager:
    """
    Manager for parent-child asset relationships.
    
    Handles linking and unlinking assets to/from parent assets with full
    historical tracking via AssetParentHistory records.
    
    Provides validation to prevent circular references and self-parenting.
    """
    
    def __init__(self, asset: Union[Asset, int]):
        """
        Initialize AssetParentChildRelationshipManager with an Asset instance or asset ID.
        
        Args:
            asset: Asset instance or asset ID
        """
        if isinstance(asset, int):
            self._asset = Asset.query.get_or_404(asset)
            self._asset_id = asset
        else:
            self._asset = asset
            self._asset_id = asset.id
    
    @property
    def asset(self) -> Asset:
        """Get the Asset instance"""
        return self._asset
    
    @property
    def asset_id(self) -> int:
        """Get the asset ID"""
        return self._asset_id
    
    def link_to_parent(
        self,
        parent_asset_id: int,
        linked_by_id: Optional[int] = None,
        link_start_time: Optional[datetime] = None,
        commit: bool = True
    ) -> AssetParentHistory:
        """
        Link this asset to a parent asset and create parent history record.
        
        Validates no circular reference and no self-parenting before creating the link.
        If an active link already exists, it will be closed before creating the new one.
        
        Args:
            parent_asset_id: ID of the parent asset to link to
            linked_by_id: ID of the user creating the link
            link_start_time: Optional timestamp (defaults to now)
            commit: If True, commit the transaction immediately. If False,
                    add to session but don't commit (allows rollback on error)
        
        Raises:
            ValueError: If circular reference would be created or self-parenting attempted
            
        Returns:
            AssetParentHistory instance for the new link
        """
        # Validate no self-parenting
        if parent_asset_id == self._asset_id:
            raise ValueError("Asset cannot be its own parent")
        
        # Validate parent asset exists
        parent_asset = Asset.query.get(parent_asset_id)
        if not parent_asset:
            raise ValueError(f"Parent asset with ID {parent_asset_id} not found")
        
        # Validate no circular reference (parent cannot be a descendant of this asset)
        self.validate_no_circular_reference(parent_asset_id)
        
        if link_start_time is None:
            link_start_time = datetime.utcnow()
        
        # Close any existing active link
        active_link = AssetParentHistory.query.filter_by(
            asset_id=self._asset_id,
            link_end_time=None
        ).first()
        
        if active_link:
            active_link.link_end_time = link_start_time
            if linked_by_id:
                active_link.updated_by_id = linked_by_id
        
        # Create new parent history record
        parent_history = AssetParentHistory(
            asset_id=self._asset_id,
            parent_asset_id=parent_asset_id,
            link_start_time=link_start_time,
            link_end_time=None,  # Active link
            created_by_id=linked_by_id,
            updated_by_id=linked_by_id
        )
        
        db.session.add(parent_history)
        db.session.flush()
        
        # Update asset's current parent
        self._asset.current_parent_asset_id = parent_asset_id
        if linked_by_id:
            self._asset.updated_by_id = linked_by_id
        
        if commit:
            db.session.commit()
        
        return parent_history
    
    def unlink_from_parent(
        self,
        unlinked_by_id: Optional[int] = None,
        link_end_time: Optional[datetime] = None,
        commit: bool = True
    ) -> Optional[AssetParentHistory]:
        """
        Unlink this asset from its current parent and close the active history record.
        
        Args:
            unlinked_by_id: ID of the user unlinking the asset
            link_end_time: Optional timestamp (defaults to now)
            commit: If True, commit the transaction immediately. If False,
                    add to session but don't commit (allows rollback on error)
        
        Raises:
            ValueError: If asset does not currently have a parent
        
        Returns:
            AssetParentHistory instance that was closed
        """
        # Find active link
        active_link = AssetParentHistory.query.filter_by(
            asset_id=self._asset_id,
            link_end_time=None
        ).first()
        
        if not active_link:
            raise ValueError(f"Asset {self._asset_id} does not have an active parent link to unlink")
        
        if link_end_time is None:
            link_end_time = datetime.utcnow()
        
        # Close the active link
        active_link.link_end_time = link_end_time
        if unlinked_by_id:
            active_link.updated_by_id = unlinked_by_id
        
        # Update asset's current parent to None
        self._asset.current_parent_asset_id = None
        if unlinked_by_id:
            self._asset.updated_by_id = unlinked_by_id
        
        if commit:
            db.session.commit()
        
        return active_link
    
    def get_current_parent(self) -> Optional[Asset]:
        """
        Get the current parent asset.
        
        Returns:
            Asset instance of the current parent, or None if no parent
        """
        if self._asset.current_parent_asset_id:
            return Asset.query.get(self._asset.current_parent_asset_id)
        return None
    
    def get_parent_history(self) -> List[AssetParentHistory]:
        """
        Get all parent linkage history records for this asset.
        
        Returns:
            List of AssetParentHistory instances, ordered by link_start_time descending (newest first)
        """
        return AssetParentHistory.query.filter_by(
            asset_id=self._asset_id
        ).order_by(AssetParentHistory.link_start_time.desc()).all()
    
    def validate_no_circular_reference(self, parent_asset_id: int) -> bool:
        """
        Validate that linking to the specified parent would not create a circular reference.
        
        A circular reference would occur if the parent asset is a descendant of this asset.
        
        Args:
            parent_asset_id: ID of the potential parent asset
        
        Raises:
            ValueError: If circular reference would be created
        
        Returns:
            True if valid (no circular reference)
        """
        # Get parent asset
        parent_asset = Asset.query.get(parent_asset_id)
        if not parent_asset:
            raise ValueError(f"Parent asset with ID {parent_asset_id} not found")
        
        # Recursively check if parent is a descendant of this asset
        visited = set()  # Prevent infinite loops in case of data corruption
        
        def is_descendant(asset_id: int, target_parent_id: int) -> bool:
            """Check if asset_id is a descendant of target_parent_id"""
            if asset_id in visited:
                return False  # Already checked, prevent infinite loop
            
            visited.add(asset_id)
            
            if asset_id == target_parent_id:
                return True
            
            # Get current parent of this asset
            asset = Asset.query.get(asset_id)
            if not asset or not asset.current_parent_asset_id:
                return False
            
            # Recursively check parent
            return is_descendant(asset.current_parent_asset_id, target_parent_id)
        
        # Check if parent_asset_id is a descendant of self._asset_id
        if is_descendant(parent_asset_id, self._asset_id):
            raise ValueError(
                f"Cannot link asset {self._asset_id} to parent {parent_asset_id}: "
                f"would create circular reference (parent is a descendant of this asset)"
            )
        
        return True
    
    def get_parent_chain(self) -> List[Asset]:
        """
        Get the complete chain of parent assets (parent, grandparent, etc.).
        
        Returns:
            List of Asset instances representing the parent chain, ordered from
            immediate parent to root ancestor (oldest parent first)
        """
        chain = []
        visited = set()  # Prevent infinite loops in case of data corruption
        current_asset = self._asset
        
        while current_asset and current_asset.current_parent_asset_id:
            parent_id = current_asset.current_parent_asset_id
            
            # Prevent infinite loops
            if parent_id in visited:
                break
            visited.add(parent_id)
            
            parent_asset = Asset.query.get(parent_id)
            if parent_asset:
                chain.append(parent_asset)
                current_asset = parent_asset
            else:
                break
        
        return chain
    
    def __repr__(self):
        return f'<AssetParentChildRelationshipManager asset_id={self._asset_id}>'


