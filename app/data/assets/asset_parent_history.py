from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
from sqlalchemy import Index

class AssetParentHistory(UserCreatedBase):
    """
    Asset Parent History - Tracks parent-child asset relationships over time.
    
    This model stores historical parent-child linkages for assets,
    allowing tracking of asset hierarchy changes over time. Each record
    represents a period during which a child asset was linked to a parent asset.
    """
    __tablename__ = 'asset_parent_history'
    
    # Asset references - REQUIRED
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    parent_asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    
    # Link timing
    link_start_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    link_end_time = db.Column(db.DateTime, nullable=True)  # NULL = currently active link
    
    # Relationships
    asset = db.relationship('Asset', foreign_keys=[asset_id], backref='parent_history_records', lazy='select')
    parent_asset = db.relationship('Asset', foreign_keys=[parent_asset_id], backref='child_history_records', lazy='select')
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_asset_parent_history_asset_id_link_end_time', 'asset_id', 'link_end_time'),
        Index('idx_asset_parent_history_parent_asset_id_link_end_time', 'parent_asset_id', 'link_end_time'),
        Index('idx_asset_parent_history_asset_id_link_start_time', 'asset_id', 'link_start_time'),
    )
    
    def __repr__(self):
        status = 'active' if self.link_end_time is None else 'closed'
        return f'<AssetParentHistory {self.id}: Asset {self.asset_id} -> Parent {self.parent_asset_id} ({status})>'


