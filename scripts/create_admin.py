import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.database import Database
from models.admin_user import AdminUser, AdminRole
from routes.admin.auth import get_password_hash
from utils.permissions import PermissionManager

def get_admin_details():
    """Get admin details from user input"""
    print("=== Creating Super Admin Account ===")
    print("This will create the first super admin account for the system.")
    print("Super admins have full access and can create other admin accounts.\n")
    
    fullname = input("Enter your full name: ").strip()
    username = input("Enter your username: ").strip()
    email = input("Enter your email: ").strip()
    
    while True:
        password = input("Enter your password (min 8 characters): ").strip()
        if len(password) >= 8:
            break
        print("Password must be at least 8 characters long!")
    
    return fullname, username, email, password

async def create_super_admin():
    """Create the first super admin user"""
    try:
        # Get admin details
        fullname, username, email, password = get_admin_details()
        
        # Connect to database
        await Database.connect_db()
        db = await Database.get_database()
        
        # Check if any super admin exists
        existing_super_admin = await db["users"].find_one({
            "is_admin": True, 
            "role": AdminRole.SUPER_ADMIN.value
        })
        
        if existing_super_admin:
            print(f"\nA super admin already exists: {existing_super_admin['username']}")
            print("Only one super admin should exist. Contact the existing super admin to create additional accounts.")
            return
        
        # Check if username or email already exists
        existing_user = await db["users"].find_one({
            "$or": [
                {"username": username},
                {"email": email}
            ]
        })
        
        if existing_user:
            print(f"\nError: Username '{username}' or email '{email}' already exists!")
            return
        
        # Hash password
        hashed_password = await get_password_hash(password)
          # Create super admin user data
        admin_data = {
            "fullname": fullname,
            "username": username,
            "email": email,
            "password": hashed_password,
            "is_active": True,
            "role": AdminRole.SUPER_ADMIN.value,
            "is_admin": True,
            "created_at": datetime.utcnow(),
            "created_by": "system",
            "assigned_events": [],
            "permissions": PermissionManager.ROLE_PERMISSIONS[AdminRole.SUPER_ADMIN]
        }
        
        # Insert into database
        result = await db["users"].insert_one(admin_data)
        
        if result.inserted_id:
            print(f"\n✅ Super Admin created successfully!")
            print(f"Name: {fullname}")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Role: Super Admin")
            print(f"\nYou can now login at /admin/login and create additional admin accounts.")
        else:
            print("\n❌ Failed to create super admin!")
            
    except Exception as e:
        print(f"\n❌ Error creating super admin: {e}")
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(create_super_admin())
