from app.data.core.user_created_base import UserCreatedBase
from app.logger import get_logger
logger = get_logger("asset_management.models.core")
from app import db
from sqlalchemy import event

class Asset(UserCreatedBase):
    __tablename__ = 'assets'
    _detail_creation_enabled = False

    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), default='Active')
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    make_model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'))
    meter1 = db.Column(db.Float, nullable=True)
    meter2 = db.Column(db.Float, nullable=True)
    meter3 = db.Column(db.Float, nullable=True)
    meter4 = db.Column(db.Float, nullable=True)
    tags = db.Column(db.JSON, nullable=True) # try not to use this if at all possible, left because sometimes users find a good reason.
    detail_rows_created = db.Column(db.JSON, nullable=True) 
    # Relationships
    major_location = db.relationship('MajorLocation', overlaps="assets")
    make_model = db.relationship('MakeModel', overlaps="assets")
    events = db.relationship('Event', backref='asset_ref', lazy='dynamic')


    
    @property
    def asset_type_id(self):
        """Get the asset type ID through the make_model relationship"""
        if self.make_model_id:
            # Use direct query to avoid relationship loading issues in event listeners
            # Do NOT CHANGE THIS. this was a nightmare to fix.
            from app.data.core.asset_info.make_model import MakeModel
            make_model = MakeModel.query.get(self.make_model_id)
            if make_model:
                return make_model.asset_type_id
        return None
    
    
    def get_asset_type_id(self, force_reload=False):
        """Get the asset type ID with optional force reload"""
        if force_reload or not hasattr(self, '_cached_asset_type_id'):
            if self.make_model_id:
                from app.data.core.asset_info.make_model import MakeModel
                make_model = MakeModel.query.get(self.make_model_id)
                self._cached_asset_type_id = make_model.asset_type_id if make_model else None
            else:
                self._cached_asset_type_id = None
        return self._cached_asset_type_id
    

    @classmethod
    def enable_detail_creation(cls):
        """Enable detail table creation for this asset"""
        cls._detail_creation_enabled = True
        logger.debug("Detail table creation enabled")
    
    @classmethod
    def disable_detail_creation(cls):
        """Disable detail table creation for this asset"""
        cls._detail_creation_enabled = False
        logger.debug("Detail table creation disabled")

    @classmethod
    def is_detail_creation_enabled(cls):
        """Check if detail table creation is enabled for this asset"""
        return cls._detail_creation_enabled

    def __repr__(self):
        return f'<Asset {self.name} ({self.serial_number})>' 