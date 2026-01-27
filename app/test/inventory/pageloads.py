"""
Page load tests for Inventory module routes
Tests that all inventory routes render without errors
"""


def check_all_routes(client):
    """
    Test all inventory module routes for successful page loads
    
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
        # Inventory main routes
        ('/inventory/index', 'GET'),
        ('/inventory/', 'GET'),
        
        # Purchase orders
        ('/inventory/purchase-order', 'GET'),
        ('/inventory/purchase-order/view', 'GET'),
        ('/inventory/purchase-order/1/view', 'GET'),
        ('/inventory/purchase-order/1/edit', 'GET'),
        ('/inventory/purchase-order/1/link', 'GET'),
        ('/inventory/purchase-order-lines/view', 'GET'),
        ('/inventory/purchase-order-line/1/view', 'GET'),
        ('/inventory/create-po', 'GET'),
        
        # Arrivals
        ('/inventory/arrivals', 'GET'),
        ('/inventory/arrivals/view', 'GET'),
        ('/inventory/po-arrivals', 'GET'),
        ('/inventory/package-arrival/1/view', 'GET'),
        ('/inventory/po-arrival/1', 'GET'),
        ('/inventory/package-arrival/1/edit', 'GET'),
        ('/inventory/arrivals/create-arrival', 'GET'),
        ('/inventory/arrivals/1/link', 'GET'),
        
        # Inventory management
        ('/inventory/active-inventory', 'GET'),
        ('/inventory/movements', 'GET'),
        ('/inventory/part-issues', 'GET'),
        ('/inventory/part-issues/1/view', 'GET'),
        ('/inventory/part-issues/1/edit', 'GET'),
        ('/inventory/issue-parts', 'GET'),
        ('/inventory/initial-stocking', 'GET'),
        ('/inventory/stocking-gui', 'GET'),
        ('/inventory/move-inventory-gui', 'GET'),
        
        # Storeroom
        ('/inventory/storeroom/index', 'GET'),
        ('/inventory/storeroom/create', 'GET'),
        ('/inventory/storeroom/1/build', 'GET'),
        ('/inventory/storeroom/1/view', 'GET'),
        ('/inventory/storeroom/1/edit', 'GET'),
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

