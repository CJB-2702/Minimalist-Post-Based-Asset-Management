"""Public-facing routes for features, modules, and information pages."""

from flask import render_template
from . import public_bp


@public_bp.route('/features')
def features():
    """Display the features page."""
    return render_template('public/features.html')


@public_bp.route('/modules')
def modules():
    """Display the modules page."""
    return render_template('public/modules.html')


@public_bp.route('/get-started')
def get_started():
    """Display the get started guide."""
    return render_template('public/get_started.html')


@public_bp.route('/learn-more')
def learn_more():
    """Display the learn more / system overview page."""
    return render_template('public/learn_more.html')



