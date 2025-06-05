import sys
import asyncio
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.database import Database
from models.admin_user import AdminRole
from utils.permissions import PermissionManager

async def upgrade_to_super_admin():
    """Upgrade existing admin to super admin"""
    try:
        # Connect to database
        await Database.connect_db()
        db = await Database.get_database()
        
        # Find existing admin
        existing_admin = await db["users"].find_one({"username": "SHIV2808"})
        
        if not existing_admin:
            print("Admin user not found!")
            return
        
        print(f"Found admin: {existing_admin['fullname']} ({existing_admin['username']})")
        print(f"Current role: {existing_admin.get('role', 'N/A')}")
        
        # Update to super admin
        update_data = {
            "role": AdminRole.SUPER_ADMIN.value,
            "is_admin": True,
            "permissions": PermissionManager.ROLE_PERMISSIONS[AdminRole.SUPER_ADMIN],
            "assigned_events": []
        }
        
        result = await db["users"].update_one(
            {"username": "SHIV2808"},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            print("✅ Successfully upgraded to Super Admin!")
            print(f"Role: {AdminRole.SUPER_ADMIN.value}")
            print("Permissions:", len(PermissionManager.ROLE_PERMISSIONS[AdminRole.SUPER_ADMIN]), "permissions granted")
        else:
            print("❌ Failed to upgrade admin!")
            
    except Exception as e:
        print(f"❌ Error upgrading admin: {e}")
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(upgrade_to_super_admin())
