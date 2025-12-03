"""
User Context (Core)
Provides a clean interface for managing user operations.
Only uses models from app.data.core.* to maintain layer separation.

Handles:
- User creation with automatic portal_user_data creation
- User update operations
- User deletion operations
"""

from typing import Optional, Dict, Any
from app import db
from app.data.core.user_info.user import User
from app.data.core.user_info.portal_user_data import PortalUserData
from app.logger import get_logger

logger = get_logger("asset_management.buisness.core.user_context")


class UserContext:
    """
    Core context manager for user operations.
    
    Provides a clean interface for:
    - Creating users with automatic portal_user_data creation
    - Updating user information
    - Deleting users (with validation)
    - Accessing user and portal data
    - Updating portal settings and cache
    - Resetting portal data to defaults
    - Resetting portal settings
    - Resetting portal cache
    """
    
    def __init__(self, user: User):
        """
        Initialize UserContext with a User instance.
        
        Args:
            user: User instance
        """
        self._user = user
        self._user_id = user.id
        self._portal_data = None  # Cache for portal_data
    
    @property
    def user(self) -> User:
        """Get the User instance"""
        return self._user
    
    @property
    def user_id(self) -> int:
        """Get the user ID"""
        return self._user_id
    
    @property
    def portal_data(self) -> Optional[PortalUserData]:
        """Get the PortalUserData instance for this user"""
        if not self._portal_data:
            self._portal_data = PortalUserData.query.filter_by(user_id=self._user_id).first()
        return self._portal_data
    
    @classmethod
    def create(
        cls,
        username: str,
        email: str,
        password: str,
        is_admin: bool = False,
        is_active: bool = True,
        created_by_id: Optional[int] = None,
        commit: bool = True,
        **kwargs
    ) -> 'UserContext':
        """
        Create a new user and associated portal_user_data record.
        
        This method ensures that every user has a corresponding portal_user_data
        record created automatically.
        
        Args:
            username: Username (must be unique)
            email: Email address (must be unique)
            password: Plain text password (will be hashed)
            is_admin: Whether user is an admin (default: False)
            is_active: Whether user is active (default: True)
            created_by_id: ID of the user creating this user
            commit: Whether to commit the transaction (default: True)
            **kwargs: Additional user fields (if any)
            
        Returns:
            UserContext instance for the newly created user
            
        Raises:
            ValueError: If username or email already exists, or password is invalid
        """
        # Validate password
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check if username already exists
        if User.query.filter_by(username=username).first():
            raise ValueError(f"Username '{username}' already exists")
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            raise ValueError(f"Email '{email}' already exists")
        
        # Create user
        user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            is_active=is_active,
            **kwargs
        )
        user.set_password(password)
        
        # Set audit fields if provided
        if created_by_id:
            # User doesn't use UserCreatedBase, but we can track creation if needed
            pass
        
        db.session.add(user)
        
        # Flush to get the user ID
        if commit:
            db.session.flush()
        else:
            db.session.flush()
        
        # Create associated portal_user_data record
        portal_data = PortalUserData(
            user_id=user.id,
            general_settings={},
            core_settings={},
            maintenance_settings={},
            general_cache={},
            core_cache={},
            maintenance_cache={}
        )
        
        # Set audit fields for portal_data
        if created_by_id:
            portal_data.created_by_id = created_by_id
            portal_data.updated_by_id = created_by_id
        
        db.session.add(portal_data)
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Created user: {username} (ID: {user.id}) with portal_user_data")
        
        return cls(user)
    
    def update(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True,
        **kwargs
    ) -> 'UserContext':
        """
        Update user information.
        
        Args:
            updated_by_id: ID of the user making the change
            commit: Whether to commit the transaction (default: True)
            **kwargs: Fields to update (username, email, is_admin, is_active, password, etc.)
            
        Returns:
            UserContext instance (self)
            
        Raises:
            ValueError: If username or email already exists (excluding current user)
        """
        # Prevent updating system user
        if self._user.is_system:
            raise ValueError("System user cannot be updated")
        
        # Handle password update
        if 'password' in kwargs:
            password = kwargs.pop('password')
            if password and len(password) >= 8:
                self._user.set_password(password)
            elif password:
                raise ValueError("Password must be at least 8 characters long")
        
        # Handle username update
        if 'username' in kwargs:
            new_username = kwargs['username']
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != self._user_id:
                raise ValueError(f"Username '{new_username}' already exists")
        
        # Handle email update
        if 'email' in kwargs:
            new_email = kwargs['email']
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != self._user_id:
                raise ValueError(f"Email '{new_email}' already exists")
        
        # Update fields
        for key, value in kwargs.items():
            if value is not None:
                setattr(self._user, key, value)
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Updated user: {self._user.username} (ID: {self._user_id})")
        self._portal_data = None
        self.portal_data
        return self
    
    def delete(
        self,
        deleted_by_id: Optional[int] = None,
        commit: bool = True
    ) -> None:
        """
        Delete user and associated portal_user_data.
        
        Args:
            deleted_by_id: ID of the user performing the deletion
            commit: Whether to commit the transaction (default: True)
            
        Raises:
            ValueError: If system user or if user has created entities
        """
        # Prevent deleting system user
        if self._user.is_system:
            raise ValueError("System user cannot be deleted")
        
        # Check if user has created any entities (optional validation)
        # This is a safety check - you may want to adjust based on requirements
        from app.data.core.asset_info.asset import Asset
        if Asset.query.filter_by(created_by_id=self._user_id).count() > 0:
            raise ValueError("Cannot delete user with created assets")
        
        # Delete portal_data first (foreign key constraint)
        portal_data = self.portal_data
        if portal_data:
            db.session.delete(portal_data)
        
        # Delete user
        db.session.delete(self._user)
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Deleted user: {self._user.username} (ID: {self._user_id})")
    
    def update_portal_data(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True,
        **kwargs
    ) -> 'UserContext':
        """
        Update portal_user_data settings and cache fields.
        
        Args:
            updated_by_id: ID of the user making the change
            commit: Whether to commit the transaction (default: True)
            **kwargs: Portal data fields to update:
                - general_settings: dict
                - core_settings: dict
                - maintenance_settings: dict
                - general_cache: dict
                - core_cache: dict
                - maintenance_cache: dict
                
        Returns:
            UserContext instance (self)
            
        Raises:
            ValueError: If portal_user_data doesn't exist
        """
        portal_data = self.portal_data
        
        if not portal_data:
            raise ValueError(f"Portal user data not found for user ID {self._user_id}")
        
        # Update fields
        valid_fields = [
            'general_settings', 'core_settings', 'maintenance_settings',
            'general_cache', 'core_cache', 'maintenance_cache'
        ]
        
        for key, value in kwargs.items():
            if key in valid_fields:
                setattr(portal_data, key, value or {})
            else:
                logger.warning(f"Invalid portal_data field: {key}")
        
        # Update audit fields
        if updated_by_id:
            portal_data.updated_by_id = updated_by_id
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Updated portal_data for user: {self._user.username} (ID: {self._user_id})")
        
        # Refresh cached portal_data
        self._portal_data = None
        
        return self
    

    def reset_portal_data(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True
    ) -> 'UserContext':
        """
        Reset all portal_user_data settings and cache fields to empty dicts.
        Calls reset_portal_settings() and reset_portal_cache().
        
        Args:
            updated_by_id: ID of the user performing the reset
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            UserContext instance (self)
            
        Raises:
            ValueError: If portal_user_data doesn't exist
        """
        # Reset settings and cache separately, but only commit at the end
        self.reset_portal_settings(updated_by_id=updated_by_id, commit=False)
        self.reset_portal_cache(updated_by_id=updated_by_id, commit=commit)
        
        return self
    
    def reset_portal_settings(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True
    ) -> 'UserContext':
        """
        Reset all portal_user_data settings fields to empty dicts (cache is preserved).
        
        Args:
            updated_by_id: ID of the user performing the reset
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            UserContext instance (self)
            
        Raises:
            ValueError: If portal_user_data doesn't exist
        """
        portal_data = self.portal_data
        
        if not portal_data:
            raise ValueError(f"Portal user data not found for user ID {self._user_id}")
        
        # Clear all settings fields (keep cache)
        portal_data.general_settings = {}
        portal_data.core_settings = {}
        portal_data.maintenance_settings = {}
        
        # Update audit fields
        if updated_by_id:
            portal_data.updated_by_id = updated_by_id
        
        # Commit if requested
        if commit:
            db.session.commit()
            logger.info(f"Reset portal settings for user: {self._user.username} (ID: {self._user_id})")
        
        # Refresh cached portal_data
        self._portal_data = None
        
        return self
    
    def reset_portal_cache(
        self,
        updated_by_id: Optional[int] = None,
        commit: bool = True
    ) -> 'UserContext':
        """
        Reset all portal_user_data cache fields to empty dicts (settings are preserved).
        Alias for clear_cache() for consistency with reset_portal_settings().
        
        Args:
            updated_by_id: ID of the user performing the reset
            commit: Whether to commit the transaction (default: True)
            
        Returns:
            UserContext instance (self)
            
        Raises:
            ValueError: If portal_user_data doesn't exist
        """
        return self.clear_cache(updated_by_id=updated_by_id, commit=commit)
    

    
    def __repr__(self):
        return f'<UserContext user_id={self._user_id} username={self._user.username}>'

