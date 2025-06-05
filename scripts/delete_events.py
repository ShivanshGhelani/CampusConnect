import asyncio
import sys
import os
import shutil
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import Database
from utils.db_operations import DatabaseOperations

async def delete_all_events():
    try:
        print("🔄 Connecting to database...")
        await Database.connect_db()
        
        print("\n📋 Fetching all events...")
        events = await DatabaseOperations.find_many("events", {})
        
        if not events:
            print("ℹ️ No events found in the database.")
            return
            
        print(f"\n🗑️ Found {len(events)} events to delete.")
        
        # Get confirmation from user
        confirmation = input("\n⚠️ WARNING: This will delete all events, their certificate folders, and event collections.\nType 'DELETE' to confirm: ")
        if confirmation != "DELETE":
            print("\n❌ Operation cancelled.")
            return
            
        # Delete certificate folders
        certificates_dir = Path("templates/certificates")
        success_count = 0
        error_count = 0
        
        print("\n🗑️ Deleting events:")
        for event in events:
            try:
                event_id = event.get('event_id')
                event_name = event.get('event_name')
                print(f"\nProcessing: {event_name} ({event_id})")
                
                # Delete certificate folder if exists
                event_cert_dir = certificates_dir / event_id
                if event_cert_dir.exists():
                    print(f"- Deleting certificate folder: {event_cert_dir}")
                    shutil.rmtree(event_cert_dir)
                if Database.client is not None:
                    # Delete event-specific collection
                    print(f"- Dropping collection: {event_id}")
                    
                    # Get the main database
                    db = Database.client["CampusConnect"]
                    
                    # Get list of all collections
                    coll_list = await db.list_collection_names()
                    
                    # Check if the event collection exists
                    safe_collection_name = ''.join(c for c in event_id if c.isalnum() or c in '-_')
                    if safe_collection_name in coll_list:
                        print(f"  Found collection {safe_collection_name}")
                        await db.drop_collection(safe_collection_name)
                        print(f"  Successfully dropped collection {safe_collection_name}")
                    else:
                        print(f"  Collection {safe_collection_name} not found")
                    
                    # Delete event document from events collection
                    print(f"- Deleting from events collection: {event_id}")
                    deleted = await DatabaseOperations.delete_one("events", {"event_id": event_id})
                    if deleted:
                        print(f"  Successfully deleted event record")
                    else:
                        print(f"  Failed to delete event record")
                
                success_count += 1
                print(f"✅ Successfully deleted {event_id}")
                
            except Exception as e:
                error_count += 1
                print(f"❌ Error deleting {event_id}: {str(e)}")
        
        print("\n📊 Summary:")
        print(f"✅ Successfully deleted: {success_count} events")
        if error_count > 0:
            print(f"❌ Failed to delete: {error_count} events")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        print("\n🔄 Closing database connection...")
        await Database.close_db()
        print("\n✨ Operation completed.")

if __name__ == "__main__":
    print("🚀 Starting event cleanup...")
    asyncio.run(delete_all_events())
