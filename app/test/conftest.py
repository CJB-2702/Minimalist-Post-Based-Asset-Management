"""
Pytest configuration and fixtures for page load tests
"""
import pytest
from app import create_app
from app import db as _db


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def authenticated_client(client):
    """Create authenticated test client with admin/admin123456789 credentials"""
    # Login with admin/admin123456789
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'admin123456789'
    }, follow_redirects=True)
    
    return client


def login_user(client, username='admin', password='admin123456789'):
    """Helper function to login a user"""
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

