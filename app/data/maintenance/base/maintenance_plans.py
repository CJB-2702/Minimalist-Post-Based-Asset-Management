from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.orm import relationship

class MaintenancePlan(UserCreatedBase):
    __tablename__ = 'maintenance_plans'
    
    #header fields
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=False)
    model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'), nullable=True)
    status = db.Column(db.String(20), default='Active', nullable=False)

    #task to be assigned
    template_action_set_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=False)

    #frequency fields
    frequency_type = db.Column(db.String(20), nullable=False)
    delta_hours = db.Column(db.Float, nullable=True)
    delta_m1 = db.Column(db.Float, nullable=True)
    delta_m2 = db.Column(db.Float, nullable=True)
    delta_m3 = db.Column(db.Float, nullable=True)
    delta_m4 = db.Column(db.Float, nullable=True)
    
    # Improved relationships with proper loading strategies
    asset_type = relationship('AssetType', backref='maintenance_plans')
    model = relationship('MakeModel', backref='maintenance_plans')
    template_action_set = relationship(
        'TemplateActionSet', 
        foreign_keys=[template_action_set_id],
        back_populates='maintenance_plans'
    )
    maintenance_action_sets = relationship('MaintenanceActionSet', back_populates='maintenance_plan')

    def __repr__(self):
        return f'<MaintenancePlan {self.name}>'
    
 