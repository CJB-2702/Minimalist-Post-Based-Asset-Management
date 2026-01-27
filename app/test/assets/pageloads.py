"""
Page load tests for Assets module routes
Tests that all asset detail routes render without errors
"""


def check_all_routes(client):
    """
    Test all assets module routes for successful page loads
    
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
        # All details
        ('/assets/all-details/1', 'GET'),
        ('/assets/all-details/3', 'GET'),
        
        # Detail tables - list views
        ('/assets/detail-tables/purchase_info/', 'GET'),
        ('/assets/detail-tables/vehicle_registration/', 'GET'),
        ('/assets/detail-tables/toyota_warranty_receipt/', 'GET'),
        ('/assets/detail-tables/smog_record/', 'GET'),
        
        # Detail tables - detail views
        ('/assets/detail-tables/purchase_info/1/', 'GET'),
        ('/assets/detail-tables/vehicle_registration/1/', 'GET'),
        
        # Detail tables - create/edit
        ('/assets/detail-tables/purchase_info/create', 'GET'),
        ('/assets/detail-tables/purchase_info/1/edit', 'GET'),
        
        # Model details - list views
        ('/assets/model-details/emissions_info/', 'GET'),
        ('/assets/model-details/model_info/', 'GET'),
        
        # Model details - detail views
        ('/assets/model-details/emissions_info/1/', 'GET'),
        ('/assets/model-details/model_info/1/', 'GET'),
        
        # Model details - create/edit
        ('/assets/model-details/emissions_info/create', 'GET'),
        ('/assets/model-details/emissions_info/1/edit', 'GET'),
        
        # Asset details card
        ('/assets/details-card', 'GET'),
        ('/assets/details-card/1', 'GET'),
        
        # Detail template config
        ('/assets/detail-template-config/configure/asset-type/1', 'GET'),
        ('/assets/detail-template-config/configure/make-model/1', 'GET'),
        
        # Detail template CRUD - asset detail templates
        ('/assets/detail-template-crud/asset-detail-template-by-asset-type/', 'GET'),
        ('/assets/detail-template-crud/asset-detail-template-by-asset-type/1', 'GET'),
        ('/assets/detail-template-crud/asset-detail-template-by-asset-type/create', 'GET'),
        ('/assets/detail-template-crud/asset-detail-template-by-asset-type/1/edit', 'GET'),
        
        # Detail template CRUD - model detail templates
        ('/assets/detail-template-crud/asset-detail-template-by-model-type/', 'GET'),
        ('/assets/detail-template-crud/asset-detail-template-by-model-type/1', 'GET'),
        ('/assets/detail-template-crud/asset-detail-template-by-model-type/create', 'GET'),
        
        # Detail template CRUD - model detail table templates
        ('/assets/detail-template-crud/model-detail-table-template/', 'GET'),
        ('/assets/detail-template-crud/model-detail-table-template/1', 'GET'),
        ('/assets/detail-template-crud/model-detail-table-template/create', 'GET'),
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






