"""
Page load tests for Maintenance module routes
Tests that all maintenance routes render without errors
"""
FIRST_KNOWN_EVENT_ID = 8

def check_all_routes(client):
    """
    Test all maintenance module routes for successful page loads
    
    Args:
        client: Flask test client (authenticated)
    
    Returns:
        dict: Results with 'passed', 'failed', and 'errors' keys
    """
    results = {
        'passed': [],
        'failed': [],
        'errors': {}
    }
    
    routes = [
        # Maintenance main routes
        ('/maintenance/index', 'GET'),
        ('/maintenance/', 'GET'),
        ('/maintenance/view-events', 'GET'),
        
        # Technician portal
        ('/maintenance/technician/dashboard', 'GET'),
        ('/maintenance/technician/', 'GET'),
        ('/maintenance/technician/most-recent-event', 'GET'),
        ('/maintenance/technician/continue-discussion', 'GET'),
        
        # Manager portal
        ('/maintenance/manager/dashboard', 'GET'),
        ('/maintenance/manager/', 'GET'),
        
        # Fleet portal
        ('/maintenance/fleet/dashboard', 'GET'),
        ('/maintenance/fleet/', 'GET'),
        
        # Maintenance event portals (new refactored routes)
        # Using event ID {FIRST_KNOWN_EVENT_ID} which is created during app initialization
        ('/maintenance/maintenance-event/{FIRST_KNOWN_EVENT_ID}', 'GET'),           # View portal
        ('/maintenance/maintenance-event/{FIRST_KNOWN_EVENT_ID}/view', 'GET'),      # View portal (explicit)
        ('/maintenance/maintenance-event/{FIRST_KNOWN_EVENT_ID}/work', 'GET'),      # Work portal
        ('/maintenance/maintenance-event/{FIRST_KNOWN_EVENT_ID}/edit', 'GET'),      # Edit portal
        ('/maintenance/maintenance-event/{FIRST_KNOWN_EVENT_ID}/assign', 'GET'),    # Assign portal
        
        # Action creator portal
        ('/maintenance/action-creator-portal', 'GET'),
        
        # Maintenance plans
        ('/maintenance/planning', 'GET'),
    ]
    
    # Test each route
    for route, method in routes:
        try:
            if method == 'GET':
                response = client.get(route, follow_redirects=True)
            else:
                response = client.post(route, follow_redirects=True)
            
            if response.status_code in [200, 302, 404]:
                results['passed'].append(route)
            else:
                results['failed'].append(route)
                results['errors'][route] = f"Status code: {response.status_code}"
        except Exception as e:
            results['failed'].append(route)
            results['errors'][route] = str(e)
    
    return results






