import sys
import os
import asyncio
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from config.database import Database
from models.admin_user import AdminUser

async def list_admins():
    """List all users and their status"""
    try:
        await Database.connect_db()
        db = await Database.get_database()
        
        # Find all users
        users = await db["users"].find({}).to_list(length=None)
        
        print("\nCurrent Users:")
        print("=" * 80)
        print(f"{'Full Name':<30} {'Username':<20} {'Email':<30} {'Role':<10}")
        print("-" * 80)
        
        for user in users:
            print(f"{user['fullname']:<30} {user['username']:<20} {user['email']:<30} {user['role']:<10}")
            
    except Exception as e:
        print(f"Error listing users: {e}")
    finally:
        await Database.close_db()

async def update_admin_role():
    """Update user role to admin"""
    try:
        await Database.connect_db()
        db = await Database.get_database()
        
        username = input("\nEnter username to grant admin access: ")
        
        # Find user
        user = await db["users"].find_one({"username": username})
        if not user:
            print(f"User {username} not found!")
            return
            
        if user.get("role") == "admin":
            print(f"\nUser {username} already has admin role!")
            print(f"Current user details:")
            print(f"Full Name: {user.get('fullname')}")
            print(f"Email: {user.get('email')}")
            print(f"Role: {user.get('role')}")
            return
            
        # Update role to admin
        result = await db["users"].update_one(
            {"username": username},
            {"$set": {"role": "admin"}}
        )
        
        if result.modified_count:
            print(f"\nSuccessfully granted admin access to {username}")
            print(f"Updated user details:")
            print(f"Full Name: {user.get('fullname')}")
            print(f"Email: {user.get('email')}")
            print(f"Role: admin")
        else:
            print(f"\nFailed to update role for {username}")
            print("Please check database permissions.")
    except Exception as e:
        print(f"Error updating admin role: {e}")
    finally:
        await Database.close_db()

async def view_user_details():
    """View details of a specific user"""
    try:
        await Database.connect_db()
        db = await Database.get_database()
        
        username = input("\nEnter username to view details: ")
        
        # Find user
        user = await db["users"].find_one({"username": username})
        if not user:
            print(f"\nUser {username} not found!")
            return
            
        print(f"\nUser Details:")
        print("-" * 40)
        print(f"Full Name: {user.get('fullname')}")
        print(f"Username: {user.get('username')}")
        print(f"Email: {user.get('email')}")
        print(f"Role: {user.get('role')}")
        print(f"Active: {user.get('is_active', True)}")
            
    except Exception as e:
        print(f"Error viewing user details: {e}")
    finally:
        await Database.close_db()

async def main():
    while True:
        print("\nAdmin Management Menu:")
        print("1. List all users and their roles")
        print("2. View user details")
        print("3. Grant admin access to user")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            await list_admins()
        elif choice == "2":
            await view_user_details()
        elif choice == "3":
            await update_admin_role()
        elif choice == "4":
            break
        else:
            print("Invalid choice! Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
