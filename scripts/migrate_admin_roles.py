#!/usr/bin/env python3
"""
Migration script to update existing admin users to use the new role-based system.
This script converts old 'admin' role to 'super_admin' and updates the schema.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_operations import DatabaseOperations
from models.admin_user import AdminRole

async def migrate_admin_roles():
    """Migrate existing admin users to new role system"""
    try:
        print("🔄 Starting admin role migration...")
          # Get all admin users
        admin_users = await DatabaseOperations.find_many("users", {"is_admin": True})
        
        if not admin_users:
            print("ℹ️  No admin users found to migrate.")
            return
        
        print(f"📋 Found {len(admin_users)} admin users to migrate:")
        
        migration_count = 0
        for admin in admin_users:
            username = admin.get('username', 'Unknown')
            current_role = admin.get('role', 'N/A')
            
            print(f"   - {username}: {current_role}")
            
            # Prepare update data
            update_data = {}
            
            # Convert old role to new role system
            if current_role == 'admin' or not current_role or current_role not in [r.value for r in AdminRole]:
                # Convert old 'admin' role to 'super_admin'
                update_data['role'] = AdminRole.SUPER_ADMIN.value
                print(f"     → Converting to: {AdminRole.SUPER_ADMIN.value}")
            
            # Add missing fields if they don't exist
            if 'permissions' not in admin:
                update_data['permissions'] = []
            
            if 'assigned_events' not in admin:
                update_data['assigned_events'] = []
            
            if 'created_by' not in admin:
                update_data['created_by'] = 'system_migration'
            
            if 'updated_at' not in admin:
                update_data['updated_at'] = datetime.utcnow()
            
            # Only update if there are changes
            if update_data:
                result = await DatabaseOperations.update_one(
                    "users", 
                    {"_id": admin["_id"]}, 
                    {"$set": update_data}
                )
                
                if result:
                    migration_count += 1
                    print(f"     ✅ Updated successfully")
                else:
                    print(f"     ⚠️  Update failed")
            else:
                print(f"     ℹ️  Already up to date")
        
        print(f"\n✅ Migration completed! Updated {migration_count} admin users.")
        
        # Verify the migration
        print("\n🔍 Verifying migration...")
        updated_admins = await DatabaseOperations.find_many("users", {"is_admin": True})
        
        for admin in updated_admins:
            username = admin.get('username', 'Unknown')
            role = admin.get('role', 'N/A')
            has_permissions = 'permissions' in admin
            has_assigned_events = 'assigned_events' in admin
            
            print(f"   - {username}: {role} | Permissions: {has_permissions} | Events: {has_assigned_events}")
        
        print("\n🎉 Admin role migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_admin_roles())
