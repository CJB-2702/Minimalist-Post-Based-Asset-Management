# EBAMS - Event Based Asset Maintenance System

A comprehensive fleet and asset management system designed to streamline operations and maximize uptime. EBAMS provides a complete solution for managing assets, maintenance workflows, inventory, dispatching, and operational planning.

This is a temporary demo. Data is deleted every day on server reset. 
Login with Username and password (admin,admin)



## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Public Asset Managment"
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

The application will automatically:
- Initialize the database with all required tables
- Create critical system data
- Insert debug/demo data for testing
- Start the development server at `http://localhost:5000`

### First Login

After starting the application, navigate to `http://localhost:5000/login` and use the default credentials:

- **Username**: `admin`
- **Password**: `password`

> ⚠️ **Important**: Change the default admin password after first login in production environments.

## 📋 Application Overview

EBAMS is built on an event-driven architecture that tracks all changes and activities across your asset fleet. The system is organized into several integrated modules:

### Core Modules

- **Asset Management** - Track assets with detailed specifications, history, and relationships
- **Maintenance System** - Schedule and execute maintenance with customizable workflows
- **Inventory Management** - Manage parts, stock levels, locations, and procurement
- **Dispatching** - Assign and track work orders across your fleet
- **Reporting & Analytics** - Gain insights into asset performance and operational efficiency

## 🏗️ Application Structure

```
Public Asset Managment/
├── app/
│   ├── data/                    # Database models (SQLAlchemy)
│   │   ├── core/               # Core entities (User, Location, Asset, Event)
│   │   ├── assets/             # Asset detail models
│   │   ├── maintenance/        # Maintenance system models
│   │   ├── inventory/          # Inventory and procurement models
│   │   └── dispatching/        # Dispatch and work order models
│   │
│   ├── buisness/               # Business logic layer
│   │   ├── core/               # Core business contexts
│   │   ├── assets/             # Asset management logic
│   │   ├── maintenance/        # Maintenance workflow logic
│   │   ├── inventory/          # Inventory management logic
│   │   └── dispatching/        # Dispatching logic
│   │
│   ├── services/               # Application services
│   │   ├── core/               # Core services
│   │   ├── assets/             # Asset services
│   │   ├── inventory/          # Inventory services
│   │   └── maintenance/        # Maintenance services
│   │
│   ├── presentation/           # Web interface layer
│   │   ├── routes/             # Flask route handlers
│   │   ├── templates/          # Jinja2 HTML templates
│   │   └── static/             # CSS, JavaScript, and static assets
│   │
│   ├── debug/                  # Debug and test data utilities
│   ├── utils/                  # Utility functions and helpers
│   ├── __init__.py            # Flask app factory
│   ├── auth.py                # Authentication routes
│   └── build.py               # Database builder
│
├── instance/                   # Instance-specific files (database, uploads)
├── logs/                      # Application logs
├── app.py                     # Application entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker container definition
└── docker-compose.yml         # Docker Compose configuration
```

### Architecture Layers

1. **Data Layer** (`app/data/`)
   - SQLAlchemy models defining database schema
   - Virtual models for computed properties
   - Organized by business domain

2. **Business Layer** (`app/buisness/`)
   - Business logic and validation
   - Context managers for complex operations
   - Factories for object creation

3. **Service Layer** (`app/services/`)
   - Application services and orchestration
   - Cross-domain operations
   - API-like interfaces

4. **Presentation Layer** (`app/presentation/`)
   - Flask routes and blueprints
   - HTML templates with HTMX
   - RESTful endpoints

## 🔧 Technology Stack

- **Backend Framework**: Flask 2.x
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Database**: SQLite (development), supports PostgreSQL/MySQL
- **Authentication**: Flask-Login with password hashing
- **Frontend**: 
  - HTMX for dynamic interactions
  - Bootstrap 5 for responsive UI
  - Alpine.js for lightweight reactivity
  - Minimal custom JavaScript
- **Logging**: Python logging with JSON structured logs

## 🎯 Key Features

### Asset Management
- Create and track assets with customizable types
- Link assets to makes/models with automatic detail population
- Track asset parent-child relationships
- Complete audit trail of all changes

### Maintenance System
- Event-based maintenance tracking
- Template-based maintenance workflows
- Action items with checklist functionality
- Part and tool demand tracking
- Technician, manager, and fleet portals

### Inventory Management
- Multi-location inventory tracking
- Purchase order management
- Arrival processing and receiving
- Part linking to maintenance events
- Stock level monitoring

### Dispatching
- Work order creation and assignment
- Status tracking with history
- Asset-dispatch relationships
- Outcome recording

## 📊 Database Build System

EBAMS uses a phased database build system for flexibility:

```bash
# Build all phases (recommended)
python app.py

# Build specific phases
python app.py --phase1    # Core foundation only
python app.py --phase2    # Core + asset details
python app.py --phase3    # Core + asset details + auto-creation
python app.py --phase4    # Full system with UI

# Build without demo data
python app.py --no-debug-data

# Create tables only (no data)
python app.py --build-only
```

### Build Phases

- **Phase 1**: Core foundation tables (User, Location, Asset, Event)
- **Phase 2**: Asset detail tables and templates
- **Phase 3**: Automatic detail creation on asset/model creation
- **Phase 4**: Full system including maintenance, inventory, and dispatching
- **Phase 5**: Maintenance system tables
- **Phase 6**: Inventory and purchasing tables

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The application will be available at `http://localhost:5000`

### Container Startup Process

Every time the container starts, it automatically:
1. Runs `z_clear_data.py` to clean up:
   - Python cache files (`.pyc`, `__pycache__`)
   - Log files (`.log`)
   - **All database files** (`.db`, `.sqlite`, `.sqlite3`) - **ALL DATA WILL BE LOST**
   - **All attachment files** in `instance/large_attachments/` - **ALL ATTACHMENTS WILL BE LOST**
2. Starts the Flask application with a fresh database

⚠️ **WARNING**: This setup DELETES ALL DATABASE DATA AND ATTACHMENTS on every container start!
This is ideal for development/testing environments that need a fresh start daily.
For production, modify `docker-entrypoint.sh` to skip the cleanup step.

### Manual Docker Build

```bash
# Build image
docker build -t ebams:latest .

# Run container
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance ebams:latest
```

## 🔐 User Management

### User Roles

- **System User** (ID: 1) - Internal system account for data initialization
- **Admin** - Full system access, user management, configuration
- **Manager** - Asset management, maintenance planning, reporting
- **Technician** - Maintenance execution, inventory access
- **Viewer** - Read-only access to data

### Creating Users

Users can be created through:
1. Web UI: Core Management → User Info → Users
2. Python console: Using `User` model and `UserContext`
3. Debug data: Automatically created with `--enable-debug-data`

## 📝 Development

### Adding New Features

1. **Models** - Define in `app/data/<domain>/`
2. **Business Logic** - Implement in `app/buisness/<domain>/`
3. **Services** - Create in `app/services/<domain>/`
4. **Routes** - Add to `app/presentation/routes/<domain>/`
5. **Templates** - Create in `app/presentation/templates/<domain>/`

### Code Organization Principles

- **Atomic Models**: Each table has its own model file
- **Domain-Driven Design**: Code organized by business domain
- **Separation of Concerns**: Clear boundaries between layers
- **Audit Trail**: All user actions tracked with created_by/modified_by
- **HTMX-First**: Minimize JavaScript, use HTMX for dynamic behavior

### Running Tests

```bash
# Run all tests
python -m pytest app/debug/

# Run specific test file
python app/debug/test_build_system.py
```

## 📁 Key Directories

- `app/data/core/` - Core system models (User, Asset, Event, Location)
- `app/presentation/templates/` - All HTML templates
- `app/debug/data/` - JSON files with demo/debug data
- `instance/` - SQLite database and uploaded files
- `logs/` - Application and error logs

## 🔍 Logging

EBAMS uses structured JSON logging:

- **Application logs**: `logs/asset_management.log`
- **Error logs**: `logs/errors.log`
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

View logs in real-time through the web interface: System → Log Viewer

## ⚙️ Configuration

Key configuration options in the Flask app:

- `SECRET_KEY` - Session encryption key (auto-generated)
- `SQLALCHEMY_DATABASE_URI` - Database connection string
- `DEBUG` - Debug mode (enabled by default)
- `HOST` - Server host (default: 127.0.0.1)
- `PORT` - Server port (default: 5000)

## 🤝 Contributing

1. Follow the existing code structure and naming conventions
2. Use type hints for function parameters and returns
3. Add docstrings to classes and functions
4. Test changes with debug data enabled
5. Update documentation for new features

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues, questions, or contributions:

1. Check the System → Help page in the application
2. Review the logs in System → Log Viewer
3. Examine debug data in `app/debug/data/`
4. Refer to model docstrings for data structure details

## 🗺️ Roadmap

- [ ] Advanced reporting and analytics dashboard
- [ ] Mobile-responsive technician portal
- [ ] Barcode/QR code scanning for assets and parts
- [ ] Email notifications for maintenance events
- [ ] REST API for external integrations
- [ ] Multi-language support
- [ ] Advanced scheduling and planning algorithms

---

Built with ❤️ for efficient fleet and asset management operations.
