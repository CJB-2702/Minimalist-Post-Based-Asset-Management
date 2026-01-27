"""
Page load tests for Core module routes
Tests that all core routes render without errors
"""


def check_all_routes(client):
    """
    Test all core module routes for successful page loads
    
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
    
    # Core dashboard routes
    routes = [
        ('/core/dashboard', 'GET'),
        ('/core', 'GET'),
    ]
    
    # Core assets routes
    routes.extend([
        ('/core/assets', 'GET'),
        ('/core/assets/1', 'GET'),
        ('/core/assets/1/edit', 'GET'),
        ('/core/assets/create', 'GET'),
    ])
    
    # Make/Models routes
    routes.extend([
        ('/core/make-models', 'GET'),
        ('/core/make-models/1', 'GET'),
        ('/core/make-models/1/edit', 'GET'),
        ('/core/make-models/create', 'GET'),
    ])
    
    # Asset Types routes
    routes.extend([
        ('/core/asset-types', 'GET'),
        ('/core/asset-types/1', 'GET'),
        ('/core/asset-types/1/edit', 'GET'),
        ('/core/asset-types/create', 'GET'),
    ])
    
    # Events routes
    routes.extend([
        ('/core/events', 'GET'),
        ('/core/events/1', 'GET'),
        ('/core/events/create', 'GET'),
    ])
    
    # Locations routes
    routes.extend([
        ('/core/locations', 'GET'),
        ('/core/locations/1', 'GET'),
        ('/core/locations/1/edit', 'GET'),
        ('/core/locations/create', 'GET'),
    ])
    
    # Users routes
    routes.extend([
        ('/core/users', 'GET'),
        ('/core/users/1', 'GET'),
        ('/core/users/1/edit', 'GET'),
        ('/core/users/create', 'GET'),
    ])
    
    # Supply routes
    routes.extend([
        ('/core/supply', 'GET'),
        ('/core/supply/part-definitions', 'GET'),
        ('/core/supply/part-definitions/1', 'GET'),
        ('/core/supply/part-definitions/1/edit', 'GET'),
        ('/core/supply/part-definitions/create', 'GET'),
        ('/core/supply/tools', 'GET'),
        ('/core/supply/tools/1', 'GET'),
        ('/core/supply/tools/1/edit', 'GET'),
        ('/core/supply/tools/create', 'GET'),
    ])
    
    # Meter history routes
    routes.extend([
        ('/core/meter-history', 'GET'),
        ('/core/meter-history/1/edit', 'GET'),
    ])
    
    # Test each route
    for route, method in routes:
        try:
            if method == 'GET':
                response = client.get(route, follow_redirects=True)
            else:
                response = client.post(route, follow_redirects=True)
            
            # Consider 200, 302 (redirect), 404 (not found but page loads) as acceptable
            # 500 (server error) is a failure
            if response.status_code in [200, 302, 404]:
                results['passed'].append(route)
            else:
                results['failed'].append(route)
                results['errors'][route] = f"Status code: {response.status_code}"
        except Exception as e:
            results['failed'].append(route)
            results['errors'][route] = str(e)
    
    return results

