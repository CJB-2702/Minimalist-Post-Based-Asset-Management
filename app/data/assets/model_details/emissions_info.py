#!/usr/bin/env python3
"""
Emissions Information Detail Table
Store emissions specifications for vehicle models
"""

from app.data.assets.model_detail_virtual import ModelDetailVirtual
from app import db

class EmissionsInfo(ModelDetailVirtual):
    """
    Store emissions specifications for vehicle models
    """
    __tablename__ = 'emissions_info'
    
    # Emissions fields
    emissions_standard = db.Column(db.String(50), nullable=True)  # EPA, CARB, etc.
    emissions_rating = db.Column(db.String(50), nullable=True)  # ULEV, SULEV, etc.
    fuel_type = db.Column(db.String(50), nullable=True)  # gasoline, diesel, electric, hybrid
    mpg_city = db.Column(db.Float, nullable=True)
    mpg_highway = db.Column(db.Float, nullable=True)
    mpg_combined = db.Column(db.Float, nullable=True)
    co2_emissions = db.Column(db.Float, nullable=True)  # grams per mile
    emissions_test_date = db.Column(db.Date, nullable=True)
    emissions_certification = db.Column(db.String(100), nullable=True)

    def __init__(self, *args, **kwargs):
        """Initialize the emissions info record"""
        super().__init__(*args, **kwargs)
    
    def __repr__(self):
        """String representation of the emissions info"""
        return f'<EmissionsInfo Model:{self.make_model_id} Standard:{self.emissions_standard}>'
    
    @property
    def fuel_efficiency_rating(self):
        """Calculate fuel efficiency rating based on combined MPG"""
        if self.mpg_combined:
            if self.mpg_combined >= 40:
                return "Excellent"
            elif self.mpg_combined >= 30:
                return "Good"
            elif self.mpg_combined >= 20:
                return "Average"
            else:
                return "Poor"
        return None
    
    @property
    def emissions_rating_category(self):
        """Get emissions rating category"""
        if self.emissions_rating:
            rating = self.emissions_rating.upper()
            if 'ZEV' in rating or 'ZERO' in rating:
                return "Zero Emissions"
            elif 'SULEV' in rating:
                return "Super Ultra Low Emissions"
            elif 'ULEV' in rating:
                return "Ultra Low Emissions"
            elif 'LEV' in rating:
                return "Low Emissions"
            else:
                return "Standard"
        return None 