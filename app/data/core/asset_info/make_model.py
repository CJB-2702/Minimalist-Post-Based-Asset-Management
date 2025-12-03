from app.data.core.user_created_base import UserCreatedBase
from app import db
from app.logger import get_logger
from sqlalchemy import event, update
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
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=False)
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


@event.listens_for(MakeModel, 'after_update')
def update_assets_asset_type_id(mapper, connection, target):
    """Update all Assets' asset_type_id when MakeModel's asset_type_id changes"""
    # Check if asset_type_id was changed
    # this is important enough to put in the data layer because its so critical to the integrity of the data
    # normally we would just do this in the business layer, but because this is a critical piece of data, we need to ensure it is always up to date
    history = db.inspect(target).attrs.asset_type_id.history
    if history.has_changes():
        old_value = history.deleted[0] if history.deleted else None
        new_value = history.added[0] if history.added else None
        
        # Only proceed if the value actually changed
        if old_value != new_value:
            from app.data.core.asset_info.asset import Asset
            # Update all assets that reference this make_model
            stmt = (
                update(Asset.__table__)
                .where(Asset.__table__.c.make_model_id == target.id)
                .values(asset_type_id=new_value)
            )
            connection.execute(stmt)
            logger.info(f"Updated asset_type_id for all assets with make_model_id={target.id} from {old_value} to {new_value}")

