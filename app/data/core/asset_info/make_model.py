from app.data.core.user_created_base import UserCreatedBase
from app import db
from app.logger import get_logger
logger = get_logger("asset_management.models.core")


class MakeModel(UserCreatedBase):
    __tablename__ = 'make_models'
    _automatic_detail_insertion_enabled = False
    
    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    revision = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=True)
    meter1_unit = db.Column(db.String(100), nullable=True)
    meter2_unit = db.Column(db.String(100), nullable=True)
    meter3_unit = db.Column(db.String(100), nullable=True)
    meter4_unit = db.Column(db.String(100), nullable=True)

    
    # Relationships (no backrefs)
    assets = db.relationship('Asset')
    asset_type = db.relationship('AssetType')
    
    def __repr__(self):
        return f'<MakeModel {self.make} {self.model}>' 

    @classmethod
    def enable_automatic_detail_insertion(cls):
        """Enable automatic detail table row creation for new models"""
        cls._automatic_detail_insertion_enabled = True
        logger.debug("Automatic detail insertion enabled")
    
    @classmethod
    def disable_automatic_detail_insertion(cls):
        """Disable automatic detail table row creation"""
        cls._automatic_detail_insertion_enabled = False

