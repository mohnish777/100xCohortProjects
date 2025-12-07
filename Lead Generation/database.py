import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Optional
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class DatabaseManager:
    def __init__(self):
        self.table_name = "customers"
    
    def create_customer(self, customer_data: dict) -> dict:
        """Create a new customer in the database"""
        try:
            # Convert datetime objects to ISO format strings for Supabase
            if customer_data.get('webinar_join'):
                if isinstance(customer_data['webinar_join'], datetime):
                    customer_data['webinar_join'] = customer_data['webinar_join'].isoformat()
            if customer_data.get('webinar_leave'):
                if isinstance(customer_data['webinar_leave'], datetime):
                    customer_data['webinar_leave'] = customer_data['webinar_leave'].isoformat()
            
            result = supabase.table(self.table_name).insert(customer_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating customer: {e}")
            raise e
    
    def get_all_customers(self) -> List[dict]:
        """Get all customers from the database"""
        try:
            result = supabase.table(self.table_name).select("*").execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error fetching customers: {e}")
            raise e
    
    def get_customer_by_id(self, customer_id: int) -> Optional[dict]:
        """Get a customer by ID"""
        try:
            result = supabase.table(self.table_name).select("*").eq("id", customer_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching customer by ID: {e}")
            raise e
    
    def update_customer(self, customer_id: int, customer_data: dict) -> Optional[dict]:
        """Update a customer in the database"""
        try:
            # Convert datetime objects to ISO format strings for Supabase
            if customer_data.get('webinar_join'):
                if isinstance(customer_data['webinar_join'], datetime):
                    customer_data['webinar_join'] = customer_data['webinar_join'].isoformat()
            if customer_data.get('webinar_leave'):
                if isinstance(customer_data['webinar_leave'], datetime):
                    customer_data['webinar_leave'] = customer_data['webinar_leave'].isoformat()
            
            result = supabase.table(self.table_name).update(customer_data).eq("id", customer_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating customer: {e}")
            raise e
    
    def delete_customer(self, customer_id: int) -> Optional[dict]:
        """Delete a customer from the database"""
        try:
            result = supabase.table(self.table_name).delete().eq("id", customer_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error deleting customer: {e}")
            raise e

# Create a global instance
db_manager = DatabaseManager()
