"""
Core models package for the Asset Management System
"""

from .user_info.user import User
from .major_location import MajorLocation
from .asset_info.asset_type import AssetType
from .asset_info.make_model import MakeModel
from .asset_info.asset import Asset
from .event_info.event import Event, EventDetailVirtual
from .event_info.attachment import Attachment
from .event_info.comment import Comment, CommentAttachment
# EventDetailIDManager, AttachmentIDManager, AssetDetailIDManager, ModelDetailIDManager moved to app.models.core.sequences
# VirtualSequenceGenerator remains in models/core (data layer infrastructure - used by sequence ID managers)
# DataInsertionMixin moved to app.domain.core.data_insertion_mixin

__all__ = [
    'User',
    'MajorLocation', 
    'AssetType',
    'MakeModel',
    'Asset',
    'Event',
    'EventDetailVirtual',
    'Attachment',
    'Comment',
    'CommentAttachment',
] 