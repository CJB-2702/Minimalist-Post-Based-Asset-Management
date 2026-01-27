# Test Suite Documentation

## Page Load Tests

The page load test suite (`test_all_pageloads.py`) performs simple HTTP status checks across all application routes to verify that pages render without server errors. These tests use Flask's test client to make GET requests to each route endpoint, following redirects automatically, and check that the response status code is acceptable (200 for success, 302 for redirects, or 404 for not found - all considered valid page loads). The tests are organized by module (core, assets, maintenance, inventory, dispatching, admin, and main), with each module having its own `pageloads.py` file containing a `check_all_routes()` function that tests all routes for that module. The main test runner executes all module tests sequentially, authenticates as the admin user, and prints a comprehensive report showing which routes passed and which failed, along with detailed error messages for any routes that returned unexpected status codes or threw exceptions during rendering. This provides a quick way to identify broken pages across the entire application without testing functionality - just ensuring pages load successfully.






