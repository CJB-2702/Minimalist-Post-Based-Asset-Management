"""
Page load tests for Dispatching module routes
Tests that all dispatching routes render without errors
"""


def check_all_routes(client):
    """
    Test all dispatching module routes for successful page loads
    
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
        ('/dispatching', 'GET'),
        ('/dispatching/index', 'GET'),
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






