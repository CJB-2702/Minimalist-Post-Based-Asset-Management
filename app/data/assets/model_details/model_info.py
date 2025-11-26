#!/usr/bin/env python3
"""
Model Information Detail Table
Store general model specifications and information
"""

from app.data.assets.model_detail_virtual import ModelDetailVirtual
from app import db

class ModelInfo(ModelDetailVirtual):
    """
    Store general model specifications and information
    """
    __tablename__ = 'model_info'
    
    # Model specification fields
    model_year = db.Column(db.Integer, nullable=True)
    body_style = db.Column(db.String(50), nullable=True)  # sedan, SUV, truck, etc.
    engine_type = db.Column(db.String(100), nullable=True)
    engine_displacement = db.Column(db.String(50), nullable=True)  # e.g., "2.5L"
    transmission_type = db.Column(db.String(50), nullable=True)  # automatic, manual, CVT
    drivetrain = db.Column(db.String(50), nullable=True)  # FWD, RWD, AWD, 4WD
    seating_capacity = db.Column(db.Integer, nullable=True)
    cargo_capacity = db.Column(db.Float, nullable=True)  # cubic feet
    towing_capacity = db.Column(db.Integer, nullable=True)  # pounds
    manufacturer_website = db.Column(db.String(500), nullable=True)
    technical_specifications = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        """String representation of the model info"""
        return f'<ModelInfo Model:{self.make_model_id} Year:{self.model_year} Style:{self.body_style}>'
    
    @property
    def vehicle_category(self):
        """Determine vehicle category based on body style"""
        if self.body_style:
            style = self.body_style.lower()
            if 'sedan' in style or 'coupe' in style or 'hatchback' in style:
                return "Passenger Car"
            elif 'suv' in style or 'crossover' in style:
                return "SUV/Crossover"
            elif 'truck' in style or 'pickup' in style:
                return "Truck"
            elif 'van' in style or 'minivan' in style:
                return "Van/Minivan"
            elif 'wagon' in style:
                return "Wagon"
            else:
                return "Other"
        return None
    
    @property
    def drivetrain_description(self):
        """Get human-readable drivetrain description"""
        if self.drivetrain:
            drivetrain = self.drivetrain.upper()
            if drivetrain == 'FWD':
                return "Front-Wheel Drive"
            elif drivetrain == 'RWD':
                return "Rear-Wheel Drive"
            elif drivetrain == 'AWD':
                return "All-Wheel Drive"
            elif drivetrain == '4WD':
                return "Four-Wheel Drive"
            else:
                return drivetrain
        return None 