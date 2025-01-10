import logging
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, SimplePublicObjectInput
from hubspot.crm.companies import SimplePublicObjectInputForCreate as CompanySimplePublicObjectInputForCreate
from hubspot.crm.companies import SimplePublicObjectInput as CompanySimplePublicObjectInput
from hubspot.crm.contacts.exceptions import ApiException
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
import json
from datetime import datetime, timedelta
from dateutil.tz import tzlocal

logger = logging.getLogger('mcp_hubspot_server')

def convert_datetime_fields(obj: Any) -> Any:
    """Convert any datetime or tzlocal objects to string in the given object"""
    if isinstance(obj, dict):
        return {k: convert_datetime_fields(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_fields(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, tzlocal):
        # Get the current timezone offset
        offset = datetime.now(tzlocal()).strftime('%z')
        return f"UTC{offset[:3]}:{offset[3:]}"  # Format like "UTC+08:00" or "UTC-05:00"
    return obj

class HubSpotClient:
    def __init__(self, access_token: Optional[str] = None):
        access_token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        logger.debug(f"Using access token: {'[MASKED]' if access_token else 'None'}")
        if not access_token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable is required")
        
        self.client = HubSpot(access_token=access_token)

    def update_contact(self, contact_id: str, properties: Dict[str, Any]) -> str:
        """Update an existing contact in HubSpot"""
        try:
            # Create SimplePublicObjectInput for update
            simple_public_object = SimplePublicObjectInput(properties=properties)
            
            # Update the contact
            api_response = self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=simple_public_object
            )
            return json.dumps(api_response.to_dict())
        except ApiException as e:
            logger.error(f"API Exception in update_contact: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception in update_contact: {str(e)}")
            return json.dumps({"error": str(e)})

    def update_company(self, company_id: str, properties: Dict[str, Any]) -> str:
        """Update an existing company in HubSpot"""
        try:
            # Create SimplePublicObjectInput for update
            simple_public_object = CompanySimplePublicObjectInput(properties=properties)
            
            # Update the company
            api_response = self.client.crm.companies.basic_api.update(
                company_id=company_id,
                simple_public_object_input=simple_public_object
            )
            return json.dumps(api_response.to_dict())
        except ApiException as e:
            logger.error(f"API Exception in update_company: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception in update_company: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_contacts(self) -> str:
        """Get all contacts from HubSpot"""
        try:
            contacts = self.client.crm.contacts.get_all()
            contacts_dict = [contact.to_dict() for contact in contacts]
            converted_contacts = convert_datetime_fields(contacts_dict)
            return json.dumps(converted_contacts)
        except ApiException as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_companies(self) -> str:
        """Get all companies from HubSpot"""
        try:
            companies = self.client.crm.companies.get_all()
            companies_dict = [company.to_dict() for company in companies]
            converted_companies = convert_datetime_fields(companies_dict)
            return json.dumps(converted_companies)
        except ApiException as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": str(e)})

[REST OF THE FILE REMAINS THE SAME...]