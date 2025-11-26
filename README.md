# Asset Management System

A comprehensive asset management system built with Flask, SQLAlchemy, and HTMX. This application manages assets, maintenance, dispatch, supply chain, and planning operations with minimal JavaScript and CSS.

## Features

- **Asset Management**: Track physical assets with types, models, and locations
- **Maintenance System**: Schedule and track maintenance events with templates
- **Dispatch System**: Manage work orders and assignments
- **Inventory Management**: Track parts, stock levels, and movements
- **Planning System**: Automated maintenance scheduling
- **User Management**: Role-based access control with system user initialization

## Technology Stack

- **Backend**: Flask with SQLAlchemy ORM
- **Frontend**: HTMX for dynamic interactions, minimal Alpine.js
- **Database**: SQLite (development)
- **Authentication**: Flask-Login
- **Styling**: Minimal CSS, focus on functionality

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd asset_management
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Build the database**
   ```bash
   # Build all phases (default)
   python app.py --build-only
   
   # Or build specific phases
   python app.py --phase1 --build-only  # Core foundation only
   python app.py --phase2 --build-only  # Core + asset details
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Project Structure

```
asset_management/
├── app/
│   ├── models/           # Database models organized by domain
│   │   ├── core/         # Core entities (User, Location, etc.)
│   │   ├── assets/       # Asset management models
│   │   ├── maintenance/  # Maintenance system models
│   │   ├── inventory/    # Inventory management models
│   │   ├── dispatch/     # Dispatch system models
│   │   ├── planning/     # Planning system models
│   │   └── communication/ # Communication models
│   ├── routes/           # Flask routes organized by domain
│   ├── templates/        # Jinja2 templates
│   ├── static/           # Static files (CSS, JS, uploads)
│   ├── services/         # Business logic services
│   └── utils/            # Utility functions
├── migrations/           # Database migrations
├── tests/               # Test files
├── requirements.txt     # Python dependencies
├── config.py           # Configuration settings
└── run.py              # Application entry point
```

## Development Phases

The system is developed in phases:

- **Phase 1**: Core Foundation (✅ Complete) - Core models, system initialization
- **Phase 2**: Asset Detail Tables (🔄 In Progress) - Extended asset information
- **Phase 3**: Maintenance & Operations (📋 Planned) - Maintenance system
- **Phase 4**: Advanced Features (📋 Planned) - Advanced functionality

## Key Models
- **User**: User management with role-based access
- **UserCreatedBase**: Abstract base class for audit trails
- **SystemUser**: Special user for initial data creation
- **MajorLocation**: Geographic locations
- **StatusSet**: Reusable status configurations
- **Event**: Activity tracking

### Asset Models
- **Asset**: Main asset entity
- **AssetType**: Asset categorization
- **MakeModel**: Manufacturer and model information

### Maintenance Models
- **MaintenanceEvent**: Scheduled and reactive maintenance
- **TemplateActions**: Reusable maintenance procedures
- **Action**: Individual maintenance tasks
- **MaintenanceStatus**: Status tracking

### Inventory Models
- **Part**: Inventory items
- **Inventory**: Stock management
- **PartDemand**: Parts needed for maintenance
- **PurchaseOrder**: Procurement management

### Dispatch Models
- **Dispatch**: Work orders and assignments
- **DispatchStatus**: Status tracking
- **DispatchChangeHistory**: Audit trail

## User Management

The system implements a hierarchical user management system:

1. **System User**: Special user (ID 1) that handles all initial data creation
2. **Admin User**: First human user with full system access
3. **Regular Users**: Role-based access (Manager, Technician, Viewer)

### User Roles
- **Admin**: Full system access, user management
- **Manager**: Asset management, maintenance planning
- **Technician**: Maintenance execution, inventory access
- **Viewer**: Read-only access

## Database Design

The system follows these design principles:

- **Atomic Models**: Each table has its own dedicated model file
- **Audit Trail**: All user-created entities track creation and modification
- **Foreign Key Relationships**: Proper referential integrity
- **System Initialization**: All seed data created by system user

## HTMX Implementation

The application uses HTMX for dynamic interactions:

- **Form Handling**: Standard HTML forms with HTMX attributes
- **Dynamic Content**: Real-time updates without page refresh
- **Loading States**: Built-in loading indicators
- **Error Handling**: Server-side validation and error display

## Development

### Adding New Models

1. Create the model file in the appropriate domain folder
2. Inherit from `UserCreatedBase` for user-created entities
3. Add relationships and foreign keys
4. Import the model in `app/models/__init__.py`

### Adding New Routes

1. Create route files in the appropriate domain folder
2. Register blueprints in `app/__init__.py`
3. Create corresponding templates
4. Add navigation links in `base.html`

### Database Migrations

```bash
flask db init
flask db migrate -m "Description of changes"
flask db upgrade
```

## Testing

Run tests with:
```bash
python -m pytest tests/
```

## Contributing

1. Follow the existing code structure and patterns
2. Use atomic models and proper separation of concerns
3. Minimize JavaScript usage - prefer HTMX solutions
4. Write tests for new functionality
5. Update documentation as needed

## License

This project is licensed under the MIT License. 