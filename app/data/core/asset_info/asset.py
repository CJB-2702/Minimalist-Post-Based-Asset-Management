from app.data.core.user_created_base import UserCreatedBase
from app.logger import get_logger
logger = get_logger("asset_management.models.core")
from app import db

class Asset(UserCreatedBase):
    __tablename__ = 'assets'
    _detail_creation_enabled = False

    name = db.Column(db.String(100), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), default='Active')
    capability_status = db.Column(db.String(20), nullable=True)
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    make_model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'),nullable=False)
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'),nullable=False)
    meter1 = db.Column(db.Float, nullable=True)
    meter2 = db.Column(db.Float, nullable=True)
    meter3 = db.Column(db.Float, nullable=True)
    meter4 = db.Column(db.Float, nullable=True)
    tags = db.Column(db.JSON, nullable=True) # try not to use this if at all possible, left because sometimes users find a good reason.
    detail_rows_created = db.Column(db.JSON, nullable=True) 
    current_parent_asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    # Relationships
    major_location = db.relationship('MajorLocation', overlaps="assets")
    make_model = db.relationship('MakeModel', overlaps="assets")
    asset_type = db.relationship('AssetType', backref='assets')
    events = db.relationship('Event', backref='asset_ref', lazy='dynamic')
    is_active = db.Column(db.Boolean, default=True)
    

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