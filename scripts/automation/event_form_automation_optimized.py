#!/usr/bin/env python3
"""
Event Form Automation Script for UCG Event Registration System
=============================================================

This script automates the complete event creation process using Selenium WebDriver.
It reads event data from the sample_event_data.json file and fills in the 9-step 
event creation form automatically.

Features:
- Logs in as admin user
- Navigates through all 9 steps of event creation
- Fills in form fields with data from JSON file
- Handles file uploads for certificate template and assets
- Waits for success page and holds for 10 seconds before closing

Author: UCG Development Team
Version: 2.0 (Optimized)
"""

import json
import time
import os
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

class EventFormAutomation:
    def __init__(self):
        """Initialize the automation script with configuration."""
        self.driver = None
        self.wait = None
        self.base_url = "http://localhost:8000"
        self.data_file = Path(__file__).parent.parent.parent / "data" / "sample_event_data.json"
        self.event_data = None
        self.login_credentials = None
        
        # Load event data
        self.load_event_data()
        
        # Initialize webdriver
        self.setup_driver()
    
    def load_event_data(self):
        """Load event data from JSON file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.event_data = data.get('event_data', {})
                self.login_credentials = data.get('login_credentials', {})
                
            print(f"✅ Event data loaded successfully from {self.data_file}")
            print(f"📄 Event: {self.event_data.get('event_name', 'Unknown')}")
            print(f"👤 Login User: {self.login_credentials.get('username', 'Unknown')}")
            
        except FileNotFoundError:
            print(f"❌ Error: Event data file not found at {self.data_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON format in data file: {e}")
            sys.exit(1)
    
    def setup_driver(self):
        """Setup Chrome WebDriver with optimized options."""
        print("🔧 Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Use webdriver-manager to handle driver installation
        service = Service(ChromeDriverManager().install())
        
        try:
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing WebDriver: {e}")
            sys.exit(1)
    
    def login_admin(self):
        """Login to the admin panel."""
        print("🔐 Logging in as admin...")
        
        try:
            # Navigate to login page
            self.driver.get(f"{self.base_url}/auth/login")
            
            # Wait for login form
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Fill login credentials
            username_field.clear()
            username_field.send_keys(self.login_credentials.get('username', ''))
            
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.login_credentials.get('password', ''))
            
            # Submit login form
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # Wait for successful login (admin dashboard)
            self.wait.until(
                EC.any_of(
                    EC.url_contains("/admin"),
                    EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
                )
            )
            
            print("✅ Login successful")
            time.sleep(2)  # Brief pause after login
            
        except TimeoutException:
            print("❌ Error: Login timeout - check credentials or server status")
            self.cleanup()
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error during login: {e}")
            self.cleanup()
            sys.exit(1)
    
    def navigate_to_event_creation(self):
        """Navigate to the event creation page."""
        print("📝 Navigating to event creation page...")
        
        try:
            # Navigate to event creation page
            self.driver.get(f"{self.base_url}/admin/events/create")
            
            # Wait for form to load
            self.wait.until(
                EC.presence_of_element_located((By.ID, "eventForm"))
            )
            
            print("✅ Event creation page loaded")
            time.sleep(1)
            
        except TimeoutException:
            print("❌ Error: Event creation page failed to load")
            self.cleanup()
            sys.exit(1)
    
    def fill_step_1_basic_info(self):
        """Fill Step 1: Basic Event Information."""
        print("📝 Filling Step 1: Basic Event Information...")
        
        try:
            # Event ID
            event_id_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "event_id"))
            )
            event_id_field.clear()
            event_id_field.send_keys(self.event_data.get('event_id', ''))
            
            # Event Name
            event_name_field = self.driver.find_element(By.NAME, "event_name")
            event_name_field.clear()
            event_name_field.send_keys(self.event_data.get('event_name', ''))
            
            # Event Type - Map bootcamp to workshop since bootcamp might not be in dropdown
            event_type_select = Select(self.driver.find_element(By.NAME, "event_type"))
            event_type_value = self.event_data.get('event_type', '')
            if event_type_value == 'bootcamp':
                event_type_value = 'workshop'  # Map bootcamp to workshop
            event_type_select.select_by_value(event_type_value)
            
            # Short Description
            short_desc_field = self.driver.find_element(By.NAME, "short_description")
            short_desc_field.clear()
            short_desc_field.send_keys(self.event_data.get('short_description', ''))
            
            # Detailed Description
            detailed_desc_field = self.driver.find_element(By.NAME, "detailed_description")
            detailed_desc_field.clear()
            detailed_desc_field.send_keys(self.event_data.get('detailed_description', ''))
            
            print("✅ Step 1 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 1: {e}")
            raise
    
    def fill_step_2_organizers(self):
        """Fill Step 2: Organizer & Contact Information."""
        print("📝 Filling Step 2: Organizer & Contact Information...")
        
        try:
            # Click Next to go to step 2
            self.click_next_button()
            
            # Organizing Department
            dept_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "organizing_department"))
            )
            dept_field.clear()
            dept_field.send_keys(self.event_data.get('organizing_department', ''))
            
            # Organizers
            organizers = self.event_data.get('organizers', [])
            if organizers:
                # Fill first organizer (already present)
                first_organizer_field = self.driver.find_element(By.NAME, "organizers[]")
                first_organizer_field.clear()
                first_organizer_field.send_keys(organizers[0])
                
                # Add additional organizers
                for organizer in organizers[1:]:
                    self.add_organizer(organizer)
            
            # Contacts
            contacts = self.event_data.get('contacts', [])
            if contacts:
                # Fill first contact (already present)
                contact_entries = self.driver.find_elements(By.CLASS_NAME, "contact-entry")
                if contact_entries:
                    first_contact = contact_entries[0]
                    name_field = first_contact.find_element(By.NAME, "contacts[][name]")
                    contact_field = first_contact.find_element(By.NAME, "contacts[][contact]")
                    
                    name_field.clear()
                    name_field.send_keys(contacts[0].get('name', ''))
                    contact_field.clear()
                    contact_field.send_keys(contacts[0].get('contact', ''))
                
                # Add additional contacts
                for contact in contacts[1:]:
                    self.add_contact(contact)
            
            print("✅ Step 2 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 2: {e}")
            raise
    
    def convert_date_format(self, date_str):
        """Convert date from YYYY-MM-DD to DD-MM-YYYY format for frontend."""
        try:
            if date_str and '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3 and len(parts[0]) == 4:  # YYYY-MM-DD format
                    return f"{parts[2]}-{parts[1]}-{parts[0]}"  # Convert to DD-MM-YYYY
            return date_str
        except Exception:
            return date_str

    def fill_step_3_schedule(self):
        """Fill Step 3: Date & Time."""
        print("📝 Filling Step 3: Date & Time...")
        
        try:
            # Click Next to go to step 3
            self.click_next_button()
              # Start Date & Time
            start_date_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "start_date"))
            )
            start_date_field.clear()
            start_date_field.send_keys(self.convert_date_format(self.event_data.get('start_date', '')))
            
            start_time_field = self.driver.find_element(By.NAME, "start_time")
            start_time_field.clear()
            start_time_field.send_keys(self.event_data.get('start_time', ''))
            
            # End Date & Time
            end_date_field = self.driver.find_element(By.NAME, "end_date")
            end_date_field.clear()
            end_date_field.send_keys(self.convert_date_format(self.event_data.get('end_date', '')))
            
            end_time_field = self.driver.find_element(By.NAME, "end_time")
            end_time_field.clear()
            end_time_field.send_keys(self.event_data.get('end_time', ''))
            
            # Registration Start Date & Time
            reg_start_date_field = self.driver.find_element(By.NAME, "registration_start_date")
            reg_start_date_field.clear()
            reg_start_date_field.send_keys(self.convert_date_format(self.event_data.get('registration_start_date', '')))
            
            reg_start_time_field = self.driver.find_element(By.NAME, "registration_start_time")
            reg_start_time_field.clear()
            reg_start_time_field.send_keys(self.event_data.get('registration_start_time', ''))
            
            # Registration End Date & Time
            reg_end_date_field = self.driver.find_element(By.NAME, "registration_end_date")
            reg_end_date_field.clear()
            reg_end_date_field.send_keys(self.convert_date_format(self.event_data.get('registration_end_date', '')))
            
            reg_end_time_field = self.driver.find_element(By.NAME, "registration_end_time")
            reg_end_time_field.clear()
            reg_end_time_field.send_keys(self.event_data.get('registration_end_time', ''))
            
            # Certificate End Date & Time
            cert_end_date_field = self.driver.find_element(By.NAME, "certificate_end_date")
            cert_end_date_field.clear()
            cert_end_date_field.send_keys(self.convert_date_format(self.event_data.get('certificate_end_date', '')))
            
            cert_end_time_field = self.driver.find_element(By.NAME, "certificate_end_time")
            cert_end_time_field.clear()
            cert_end_time_field.send_keys(self.event_data.get('certificate_end_time', ''))
            
            print("✅ Step 3 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 3: {e}")
            raise
    
    def fill_step_4_venue(self):
        """Fill Step 4: Event Mode & Location."""
        print("📝 Filling Step 4: Event Mode & Location...")
        
        try:
            # Click Next to go to step 4
            self.click_next_button()
            
            # Mode
            mode_select = Select(self.wait.until(
                EC.element_to_be_clickable((By.NAME, "mode"))
            ))
            mode_select.select_by_value(self.event_data.get('mode', ''))
            
            # Venue
            venue_field = self.driver.find_element(By.NAME, "venue")
            venue_field.clear()
            venue_field.send_keys(self.event_data.get('venue', ''))
            
            print("✅ Step 4 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 4: {e}")
            raise
    
    def fill_step_5_goals(self):
        """Fill Step 5: Target Outcomes / Goals."""
        print("📝 Filling Step 5: Target Outcomes / Goals...")
        
        try:
            # Click Next to go to step 5
            self.click_next_button()
            
            # Target Outcomes
            outcomes_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "target_outcomes"))
            )
            outcomes_field.clear()
            outcomes_field.send_keys(self.event_data.get('target_outcomes', ''))
            
            print("✅ Step 5 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 5: {e}")
            raise
    
    def fill_step_6_prerequisites(self):
        """Fill Step 6: Prerequisites & What to Bring."""
        print("📝 Filling Step 6: Prerequisites & What to Bring...")
        
        try:
            # Click Next to go to step 6
            self.click_next_button()
            
            # Prerequisites
            prereq_field = self.wait.until(
                EC.element_to_be_clickable((By.NAME, "prerequisites"))
            )
            prereq_field.clear()
            prereq_field.send_keys(self.event_data.get('prerequisites', ''))
            
            # What to Bring
            bring_field = self.driver.find_element(By.NAME, "what_to_bring")
            bring_field.clear()
            bring_field.send_keys(self.event_data.get('what_to_bring', ''))
            
            print("✅ Step 6 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 6: {e}")
            raise
    
    def fill_step_7_registration(self):
        """Fill Step 7: Registration Type & Fee Structure."""
        print("📝 Filling Step 7: Registration Type & Fee Structure...")
        
        try:
            # Click Next to go to step 7
            self.click_next_button()
            
            # Registration Type
            reg_type_select = Select(self.wait.until(
                EC.element_to_be_clickable((By.NAME, "registration_type"))
            ))
            reg_type_select.select_by_value(self.event_data.get('registration_type', ''))
            
            # Wait for fee fields to appear if paid registration
            if self.event_data.get('registration_type') == 'paid':
                time.sleep(1)  # Wait for fields to become visible
                
                # Registration Fee
                fee_field = self.wait.until(
                    EC.element_to_be_clickable((By.NAME, "registration_fee"))
                )
                fee_field.clear()
                fee_field.send_keys(str(self.event_data.get('registration_fee', '0')))
                
                # Fee Description
                if self.event_data.get('fee_description'):
                    fee_desc_field = self.driver.find_element(By.NAME, "fee_description")
                    fee_desc_field.clear()
                    fee_desc_field.send_keys(self.event_data.get('fee_description', ''))
            
            # Registration Mode
            reg_mode_select = Select(self.driver.find_element(By.NAME, "registration_mode"))
            reg_mode_select.select_by_value(self.event_data.get('registration_mode', ''))
            
            # Team size fields if team registration
            if self.event_data.get('registration_mode') == 'team':
                time.sleep(1)  # Wait for fields to become visible
                
                team_min_field = self.wait.until(
                    EC.element_to_be_clickable((By.NAME, "team_size_min"))
                )
                team_min_field.clear()
                team_min_field.send_keys(str(self.event_data.get('team_size_min', '')))
                
                team_max_field = self.driver.find_element(By.NAME, "team_size_max")
                team_max_field.clear()
                team_max_field.send_keys(str(self.event_data.get('team_size_max', '')))
            
            # Max Participants
            if self.event_data.get('max_participants'):
                max_part_field = self.driver.find_element(By.NAME, "max_participants")
                max_part_field.clear()
                max_part_field.send_keys(str(self.event_data.get('max_participants', '')))
            
            # Min Participants
            min_part_field = self.driver.find_element(By.NAME, "min_participants")
            min_part_field.clear()
            min_part_field.send_keys(str(self.event_data.get('min_participants', '1')))
            
            print("✅ Step 7 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 7: {e}")
            raise
    
    def fill_step_8_certificate(self):
        """Fill Step 8: Certificate Template."""
        print("📝 Filling Step 8: Certificate Template...")
        
        try:
            # Click Next to go to step 8
            self.click_next_button()
            
            # Certificate Template File
            cert_template_path = self.event_data.get('certificate_template_path')
            if cert_template_path and os.path.exists(cert_template_path):
                cert_file_input = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "certificate_template"))
                )
                # Convert to absolute path to ensure compatibility
                abs_cert_path = os.path.abspath(cert_template_path)
                cert_file_input.send_keys(abs_cert_path)
                print(f"📄 Certificate template uploaded: {abs_cert_path}")
            else:
                print(f"⚠️  Warning: Certificate template file not found at: {cert_template_path}")
                print("❌ Cannot proceed without certificate template - this is required")
                raise FileNotFoundError(f"Certificate template file not found: {cert_template_path}")
            
            # Asset Files (optional)
            asset_files = self.event_data.get('asset_files', [])
            if asset_files:
                assets_input = self.driver.find_element(By.NAME, "assets")
                uploaded_assets = []
                
                # For multiple files, we need to send all paths at once
                valid_asset_paths = []
                for asset_file in asset_files:
                    if os.path.exists(asset_file):
                        abs_asset_path = os.path.abspath(asset_file)
                        valid_asset_paths.append(abs_asset_path)
                        print(f"📎 Asset file found: {abs_asset_path}")
                    else:
                        print(f"⚠️  Warning: Asset file not found: {asset_file}")
                
                if valid_asset_paths:
                    # Send all valid asset paths (for multiple file selection)
                    assets_input.send_keys('\n'.join(valid_asset_paths))
                    print(f"✅ Uploaded {len(valid_asset_paths)} asset file(s)")
            else:
                print("ℹ️  No asset files specified")
            
            print("✅ Step 8 completed")
            
        except Exception as e:
            print(f"❌ Error in Step 8: {e}")
            raise
    
    def review_and_submit(self):
        """Step 9: Review and Submit the form."""
        print("📝 Step 9: Review and Submit...")
        
        try:
            # Click Next to go to step 9 (Review)
            self.click_next_button()
            
            # Wait for review content to load
            self.wait.until(
                EC.presence_of_element_located((By.ID, "reviewContent"))
            )
            
            print("📋 Review content loaded")
            time.sleep(2)  # Brief pause to review
            
            # Click Create Event button
            create_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit-form"))
            )
            
            print("🚀 Submitting event creation form...")
            create_button.click()
            
            # Wait for success page
            self.wait_for_success_page()
            
        except Exception as e:
            print(f"❌ Error in Step 9: {e}")
            raise
    
    def wait_for_success_page(self):
        """Wait for the success page and hold for 10 seconds."""
        print("⏳ Waiting for event creation success page...")
        
        try:
            # Wait for success page to load (check for success indicators)
            success_indicators = [
                EC.url_contains("/success"),
                EC.presence_of_element_located((By.CLASS_NAME, "success")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Event Created Successfully')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Success')]"))
            ]
            
            self.wait.until(EC.any_of(*success_indicators))
            
            print("🎉 Event created successfully!")
            print("✅ Success page loaded - holding for 10 seconds...")
            
            # Hold for 10 seconds as requested
            time.sleep(10)
            
            print("⏰ 10 seconds completed - automation finished")
            
        except TimeoutException:
            print("⚠️  Success page not detected, but form may have been submitted")
            print("📝 Current URL:", self.driver.current_url)
            print("🔍 Checking page content...")
            
            # Try to detect success by checking current page
            page_source = self.driver.page_source.lower()
            if any(keyword in page_source for keyword in ['success', 'created', 'event']):
                print("✅ Event likely created successfully based on page content")
                time.sleep(10)
            else:
                print("❌ Could not confirm event creation success")
    
    def click_next_button(self):
        """Click the Next button to proceed to next step."""
        try:
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.next-step"))
            )
            
            # Scroll into view if needed
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(0.5)
            
            next_button.click()
            time.sleep(1)  # Brief pause after clicking
            
        except ElementClickInterceptedException:
            # Try JavaScript click if regular click fails
            next_button = self.driver.find_element(By.CSS_SELECTOR, "button.next-step")
            self.driver.execute_script("arguments[0].click();", next_button)
            time.sleep(1)
    
    def add_organizer(self, organizer_name):
        """Add an additional organizer field."""
        try:
            add_organizer_btn = self.driver.find_element(By.CSS_SELECTOR, "button.add-organizer")
            add_organizer_btn.click()
            time.sleep(0.5)
            
            # Find the newly added organizer field
            organizer_fields = self.driver.find_elements(By.NAME, "organizers[]")
            if organizer_fields:
                organizer_fields[-1].send_keys(organizer_name)
                
        except Exception as e:
            print(f"⚠️  Could not add organizer '{organizer_name}': {e}")
    
    def add_contact(self, contact_info):
        """Add an additional contact field."""
        try:
            add_contact_btn = self.driver.find_element(By.CSS_SELECTOR, "button.add-contact")
            add_contact_btn.click()
            time.sleep(0.5)
            
            # Find the newly added contact fields
            contact_entries = self.driver.find_elements(By.CLASS_NAME, "contact-entry")
            if contact_entries:
                latest_entry = contact_entries[-1]
                name_field = latest_entry.find_element(By.NAME, "contacts[][name]")
                contact_field = latest_entry.find_element(By.NAME, "contacts[][contact]")
                
                name_field.send_keys(contact_info.get('name', ''))
                contact_field.send_keys(contact_info.get('contact', ''))
                
        except Exception as e:
            print(f"⚠️  Could not add contact '{contact_info}': {e}")
    
    def cleanup(self):
        """Clean up resources and close browser."""
        if self.driver:
            print("🧹 Cleaning up and closing browser...")
            self.driver.quit()
    
    def run_automation(self):
        """Run the complete event creation automation."""
        try:
            print("🚀 Starting Event Form Automation...")
            print("=" * 60)
            
            # Step 1: Login
            self.login_admin()
            
            # Step 2: Navigate to event creation
            self.navigate_to_event_creation()
            
            # Step 3-11: Fill all form steps
            self.fill_step_1_basic_info()
            self.fill_step_2_organizers()
            self.fill_step_3_schedule()
            self.fill_step_4_venue()
            self.fill_step_5_goals()
            self.fill_step_6_prerequisites()
            self.fill_step_7_registration()
            self.fill_step_8_certificate()
            self.review_and_submit()
            
            print("=" * 60)
            print("🎉 Event creation automation completed successfully!")
            
        except Exception as e:
            print(f"❌ Automation failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

def main():
    """Main function to run the automation."""
    print("🤖 UCG Event Form Automation Script")
    print("📅 Version: 2.0 (Optimized with Date Conversion)")
    print("=" * 60)
    
    automation = None
    try:
        print("🔧 Initializing automation...")
        automation = EventFormAutomation()
        
        print("🚀 Starting automation process...")
        automation.run_automation()
        
        print("🎉 Automation completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Automation interrupted by user (Ctrl+C)")
        return 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if automation:
            automation.cleanup()

if __name__ == "__main__":
    main()
