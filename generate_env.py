#!/usr/bin/env python3
"""
Environment Configuration Generator for Asset Management System

This script generates a secure .env file with:
- Cryptographically secure SECRET_KEY for Flask sessions
- Secure random passwords for System and Admin users
- Database configuration
- Other environment variables

Usage:
    python generate_env.py              # Interactive mode
    python generate_env.py --force      # Overwrite existing .env
    python generate_env.py --dev        # Development mode (less secure, predictable)
"""

import secrets
import string
import sys
import os
from pathlib import Path
import argparse


class EnvGenerator:
    """Generate secure environment configuration"""
    
    def __init__(self, dev_mode=False):
        self.dev_mode = dev_mode
        self.env_file = Path(__file__).parent / '.env'
        self.env_template = Path(__file__).parent / '.env.example'
        
    def generate_secret_key(self, length=64):
        """Generate a cryptographically secure secret key"""
        if self.dev_mode:
            return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
        return secrets.token_hex(length)
    
    def generate_password(self, length=20, include_special=True):
        """
        Generate a secure random password
        
        Args:
            length: Password length (default: 20)
            include_special: Include special characters (default: True)
        
        Returns:
            Secure random password string
        """
        if self.dev_mode:
            return "admin987654321!"  # Simple password for development
        
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        # Safe special characters for .env files (avoid #, =, :, quotes)
        special = "!@$%^&*()_+-[]{}|;.,<>?"
        
        # Ensure at least one of each type
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
        ]
        
        if include_special:
            password.append(secrets.choice(special))
        
        # Fill the rest
        all_chars = lowercase + uppercase + digits
        if include_special:
            all_chars += special
        
        for _ in range(length - len(password)):
            password.append(secrets.choice(all_chars))
        
        # Shuffle to avoid predictable pattern
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def generate_database_url(self):
        """Generate database URL"""
        # For now, using SQLite (default)
        # Can be customized for PostgreSQL, MySQL, etc.
        return "sqlite:///instance/asset_management.db"
    
    def create_env_content(self):
        """Create the full .env file content"""
        
        secret_key = self.generate_secret_key()
        system_password = self.generate_password()
        admin_password = self.generate_password()
        database_url = self.generate_database_url()
        
        content = f"""# Asset Management System Environment Configuration
# Generated: {self._get_timestamp()}
# 
# SECURITY WARNING: Keep this file secret! Never commit to version control!
# The .gitignore file should already exclude .env files.

# ============================================================================
# Flask Configuration
# ============================================================================

# Secret key for session signing and CSRF protection
# CRITICAL: Change this in production! Never use the default!
SECRET_KEY={secret_key}

# Flask environment: 'development' or 'production'
FLASK_ENV=production

# Flask debug mode: 'True' or 'False'
# WARNING: NEVER set to True in production!
FLASK_DEBUG=False

# Enable/disable Flask reloader (useful for development)
USE_RELOADER=False

# ============================================================================
# Database Configuration
# ============================================================================

# Database connection URL
# SQLite (default): sqlite:///instance/asset_management.db
# PostgreSQL: postgresql://user:password@localhost/dbname
# MySQL: mysql://user:password@localhost/dbname
DATABASE_URL={database_url}

# ============================================================================
# Default User Credentials
# ============================================================================
# These are used during initial database setup to create default users.
# After setup, you can change passwords through the web interface.
# Note: Values are quoted to safely handle special characters

# System User (id=0) - Internal system user for automated operations
SYSTEM_USER_PASSWORD="{system_password}"

# Admin User (id=1) - Primary administrator account
ADMIN_USER_PASSWORD="{admin_password}"

# ============================================================================
# Application Settings
# ============================================================================

# Server host (0.0.0.0 = all interfaces, 127.0.0.1 = localhost only)
# For production behind reverse proxy, use 127.0.0.1
FLASK_HOST=127.0.0.1

# Server port
FLASK_PORT=5000

# ============================================================================
# Security Settings (Advanced)
# ============================================================================

# HTTPS/TLS Configuration
# Set to True in production when using HTTPS, False for development/HTTP only
ENABLE_HTTPS={'False' if self.dev_mode else 'True'}

# Automatically redirect HTTP to HTTPS (requires ENABLE_HTTPS=True)
FORCE_HTTPS_REDIRECT={'False' if self.dev_mode else 'True'}

# Session cookie settings
SESSION_COOKIE_SECURE={'False' if self.dev_mode else 'True'}  # Set to False ONLY for development/HTTP
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Session lifetime in seconds (default: 3600 = 1 hour)
PERMANENT_SESSION_LIFETIME=3600

# Remember me cookie settings
REMEMBER_COOKIE_SECURE={'False' if self.dev_mode else 'True'}  # Set to False ONLY for development/HTTP
REMEMBER_COOKIE_HTTPONLY=True
REMEMBER_COOKIE_DURATION=86400  # 24 hours in seconds

# ============================================================================
# Email Configuration (Optional - for notifications)
# ============================================================================

# SMTP server settings (uncomment and configure if using email)
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USE_TLS=True
# MAIL_USERNAME=your-email@example.com
# MAIL_PASSWORD=your-email-password
# MAIL_DEFAULT_SENDER=your-email@example.com

# ============================================================================
# Logging Configuration
# ============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file path (relative to project root)
LOG_FILE=logs/asset_management.log

# ============================================================================
# Feature Flags (Optional)
# ============================================================================

# Enable/disable specific features
# ENABLE_MAINTENANCE_MODULE=True
# ENABLE_INVENTORY_MODULE=True
# ENABLE_DISPATCHING_MODULE=True

"""
        
        return content, {
            'secret_key': secret_key,
            'system_password': system_password,
            'admin_password': admin_password,
            'database_url': database_url
        }
    
    def _get_timestamp(self):
        """Get current timestamp for documentation"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def file_exists(self):
        """Check if .env file already exists"""
        return self.env_file.exists()
    
    def create_backup(self):
        """Create backup of existing .env file"""
        if not self.file_exists():
            return None
        
        backup_path = self.env_file.parent / f'.env.backup.{self._get_timestamp().replace(":", "-").replace(" ", "_")}'
        import shutil
        shutil.copy2(self.env_file, backup_path)
        return backup_path
    
    def write_env_file(self, content):
        """Write content to .env file"""
        with open(self.env_file, 'w') as f:
            f.write(content)
        
        # Set file permissions to 600 (owner read/write only)
        os.chmod(self.env_file, 0o600)
    
    def display_credentials(self, credentials):
        """Display generated credentials to user"""
        print("\n" + "=" * 80)
        print("🔐 GENERATED CREDENTIALS - SAVE THESE SECURELY!")
        print("=" * 80)
        print("\n📝 These credentials have been written to .env file")
        print("⚠️  This is the ONLY time passwords will be displayed!")
        print("\n" + "-" * 80)
        
        if not self.dev_mode:
            print("\n🔑 Flask Secret Key:")
            print(f"   {credentials['secret_key'][:20]}...{credentials['secret_key'][-20:]}")
            print(f"   (Length: {len(credentials['secret_key'])} characters)")
        else:
            print("\n🔑 Flask Secret Key: dev-secret-key-DO-NOT-USE-IN-PRODUCTION")
        
        print("\n👤 Default User Credentials:")
        print(f"\n   System User:")
        print(f"   - Username: system")
        print(f"   - Password: {credentials['system_password']}")
        
        print(f"\n   Admin User:")
        print(f"   - Username: admin")
        print(f"   - Password: {credentials['admin_password']}")
        
        print("\n💾 Database Configuration:")
        print(f"   {credentials['database_url']}")
        
        print("\n" + "-" * 80)
        print("\n📋 Next Steps:")
        print("   1. Save these credentials in a secure password manager")
        print("   2. Run: python app.py  (to initialize database)")
        print("   3. Login with admin credentials")
        print("   4. Change admin password through web interface")
        print("   5. Keep .env file secure (never commit to git)")
        
        if self.dev_mode:
            print("\n⚠️  DEV MODE: Using simple passwords for development!")
            print("   DO NOT use this configuration in production!")
        
        print("\n" + "=" * 80 + "\n")
    
    def generate(self, force=False):
        """
        Generate .env file
        
        Args:
            force: Overwrite existing .env file without prompting
        """
        # Check if .env already exists
        if self.file_exists() and not force:
            print(f"\n⚠️  File {self.env_file} already exists!")
            response = input("Do you want to overwrite it? (yes/no): ").lower().strip()
            
            if response not in ['yes', 'y']:
                print("❌ Aborted. Existing .env file was not modified.")
                return False
            
            # Create backup
            backup_path = self.create_backup()
            if backup_path:
                print(f"✅ Backup created: {backup_path}")
        
        # Generate content
        print("\n🔧 Generating secure environment configuration...")
        content, credentials = self.create_env_content()
        
        # Write to file
        self.write_env_file(content)
        print(f"✅ Created: {self.env_file}")
        
        # Display credentials
        self.display_credentials(credentials)
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate secure .env configuration for Asset Management System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_env.py              # Interactive mode
  python generate_env.py --force      # Overwrite without prompting
  python generate_env.py --dev        # Development mode (simple passwords)
  
Security Notes:
  - Generated .env file will have 600 permissions (owner read/write only)
  - Secret key is 128 characters (64 bytes hex)
  - Passwords are 20 characters with uppercase, lowercase, digits, and symbols
  - Password values are quoted to safely handle special characters
  - All values use cryptographically secure random generation
        """
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing .env file without prompting'
    )
    
    parser.add_argument(
        '--dev', '-d',
        action='store_true',
        help='Development mode: use simple, predictable values (NOT FOR PRODUCTION!)'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print("\n" + "=" * 80)
    print("🔐 Asset Management System - Environment Generator")
    print("=" * 80)
    
    if args.dev:
        print("\n⚠️  WARNING: Development mode enabled!")
        print("    This will generate INSECURE credentials for development only.")
        print("    DO NOT use --dev flag for production deployments!\n")
    
    # Create generator
    generator = EnvGenerator(dev_mode=args.dev)
    
    # Generate
    success = generator.generate(force=args.force)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
