import logging
from typing import Any, Dict, List, Optional
import os
from dotenv import load_dotenv
from hubspot import HubSpot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate
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

    def get_company_activity(self, company_id: str) -> str:
        """Get activity history for a specific company"""
        try:
            # Step 1: Get all engagement IDs associated with the company using CRM Associations v4 API
            associated_engagements = self.client.crm.associations.v4.basic_api.get_page(
                object_type="companies",
                object_id=company_id,
                to_object_type="engagements",
                limit=500
            )
            
            # Extract engagement IDs from the associations response
            engagement_ids = []
            if hasattr(associated_engagements, 'results'):
                for result in associated_engagements.results:
                    engagement_ids.append(result.to_object_id)

            # Step 2: Get detailed information for each engagement
            activities = []
            for engagement_id in engagement_ids:
                engagement_response = self.client.api_request({
                    "method": "GET",
                    "path": f"/engagements/v1/engagements/{engagement_id}"
                }).json()
                
                engagement_data = engagement_response.get('engagement', {})
                metadata = engagement_response.get('metadata', {})
                
                # Format the engagement
                formatted_engagement = {
                    "id": engagement_data.get("id"),
                    "type": engagement_data.get("type"),
                    "created_at": engagement_data.get("createdAt"),
                    "last_updated": engagement_data.get("lastUpdated"),
                    "created_by": engagement_data.get("createdBy"),
                    "modified_by": engagement_data.get("modifiedBy"),
                    "timestamp": engagement_data.get("timestamp"),
                    "associations": engagement_response.get("associations", {})
                }
                
                # Add type-specific metadata formatting
                if engagement_data.get("type") == "NOTE":
                    formatted_engagement["content"] = metadata.get("body", "")
                elif engagement_data.get("type") == "EMAIL":
                    formatted_engagement["content"] = {
                        "subject": metadata.get("subject", ""),
                        "from": {
                            "raw": metadata.get("from", {}).get("raw", ""),
                            "email": metadata.get("from", {}).get("email", ""),
                            "firstName": metadata.get("from", {}).get("firstName", ""),
                            "lastName": metadata.get("from", {}).get("lastName", "")
                        },
                        "to": [{
                            "raw": recipient.get("raw", ""),
                            "email": recipient.get("email", ""),
                            "firstName": recipient.get("firstName", ""),
                            "lastName": recipient.get("lastName", "")
                        } for recipient in metadata.get("to", [])],
                        "cc": [{
                            "raw": recipient.get("raw", ""),
                            "email": recipient.get("email", ""),
                            "firstName": recipient.get("firstName", ""),
                            "lastName": recipient.get("lastName", "")
                        } for recipient in metadata.get("cc", [])],
                        "bcc": [{
                            "raw": recipient.get("raw", ""),
                            "email": recipient.get("email", ""),
                            "firstName": recipient.get("firstName", ""),
                            "lastName": recipient.get("lastName", "")
                        } for recipient in metadata.get("bcc", [])],
                        "sender": {
                            "email": metadata.get("sender", {}).get("email", "")
                        },
                        "body": metadata.get("text", "") or metadata.get("html", "")
                    }
                elif engagement_data.get("type") == "TASK":
                    formatted_engagement["content"] = {
                        "subject": metadata.get("subject", ""),
                        "body": metadata.get("body", ""),
                        "status": metadata.get("status", ""),
                        "for_object_type": metadata.get("forObjectType", "")
                    }
                elif engagement_data.get("type") == "MEETING":
                    formatted_engagement["content"] = {
                        "title": metadata.get("title", ""),
                        "body": metadata.get("body", ""),
                        "start_time": metadata.get("startTime"),
                        "end_time": metadata.get("endTime"),
                        "internal_notes": metadata.get("internalMeetingNotes", "")
                    }
                elif engagement_data.get("type") == "CALL":
                    formatted_engagement["content"] = {
                        "body": metadata.get("body", ""),
                        "from_number": metadata.get("fromNumber", ""),
                        "to_number": metadata.get("toNumber", ""),
                        "duration_ms": metadata.get("durationMilliseconds"),
                        "status": metadata.get("status", ""),
                        "disposition": metadata.get("disposition", "")
                    }
                
                activities.append(formatted_engagement)

            # Convert any datetime fields and return
            converted_activities = convert_datetime_fields(activities)
            return json.dumps(converted_activities)
            
        except ApiException as e:
            logger.error(f"API Exception: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception: {str(e)}")
            return json.dumps({"error": str(e)})

    def update_contact(self, contact_id: str, properties: Dict[str, Any]) -> str:
        """Update a HubSpot contact with the given properties"""
        try:
            # Create SimplePublicObjectInput for the update
            from hubspot.crm.contacts import SimplePublicObjectInput
            
            simple_public_object_input = SimplePublicObjectInput(
                properties=properties
            )
            
            # Update the contact
            api_response = self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=simple_public_object_input
            )
            
            # Convert and return the response
            response_dict = api_response.to_dict()
            converted_response = convert_datetime_fields(response_dict)
            return json.dumps(converted_response)
            
        except ApiException as e:
            logger.error(f"API Exception in update_contact: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception in update_contact: {str(e)}")
            return json.dumps({"error": str(e)})

    def update_company(self, company_id: str, properties: Dict[str, Any]) -> str:
        """Update a HubSpot company with the given properties"""
        try:
            # Create SimplePublicObjectInput for the update
            from hubspot.crm.companies import SimplePublicObjectInput
            
            simple_public_object_input = SimplePublicObjectInput(
                properties=properties
            )
            
            # Update the company
            api_response = self.client.crm.companies.basic_api.update(
                company_id=company_id,
                simple_public_object_input=simple_public_object_input
            )
            
            # Convert and return the response
            response_dict = api_response.to_dict()
            converted_response = convert_datetime_fields(response_dict)
            return json.dumps(converted_response)
            
        except ApiException as e:
            logger.error(f"API Exception in update_company: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception in update_company: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_recent_activities(self) -> str:
        """Get recent activities from HubSpot for the last 3 days"""
        try:
            # Calculate timestamp for 3 days ago
            three_days_ago = int((datetime.now() - timedelta(days=3)).timestamp() * 1000)
            
            activities = []
            offset = None
            
            while True:
                # Prepare request parameters
                params = {
                    "count": 100,  # Get maximum allowed per request
                    "since": three_days_ago
                }
                if offset:
                    params["offset"] = offset
                
                # Get recent modified engagements
                response = self.client.api_request({
                    "method": "GET",
                    "path": "/engagements/v1/engagements/recent/modified",
                    "params": params
                }).json()
                
                # Process results
                if 'results' in response:
                    for result in response['results']:
                        engagement_data = result.get('engagement', {})
                        metadata = result.get('metadata', {})
                        
                        # Format the engagement
                        formatted_engagement = {
                            "id": engagement_data.get("id"),
                            "type": engagement_data.get("type"),
                            "created_at": engagement_data.get("createdAt"),
                            "last_updated": engagement_data.get("lastUpdated"),
                            "created_by": engagement_data.get("createdBy"),
                            "modified_by": engagement_data.get("modifiedBy"),
                            "timestamp": engagement_data.get("timestamp"),
                            "associations": result.get("associations", {})
                        }
                        
                        # Add type-specific metadata formatting
                        if engagement_data.get("type") == "NOTE":
                            formatted_engagement["content"] = metadata.get("body", "")
                        elif engagement_data.get("type") == "EMAIL":
                            formatted_engagement["content"] = {
                                "subject": metadata.get("subject", ""),
                                "from": {
                                    "raw": metadata.get("from", {}).get("raw", ""),
                                    "email": metadata.get("from", {}).get("email", ""),
                                    "firstName": metadata.get("from", {}).get("firstName", ""),
                                    "lastName": metadata.get("from", {}).get("lastName", "")
                                },
                                "to": [{
                                    "raw": recipient.get("raw", ""),
                                    "email": recipient.get("email", ""),
                                    "firstName": recipient.get("firstName", ""),
                                    "lastName": recipient.get("lastName", "")
                                } for recipient in metadata.get("to", [])],
                                "cc": [{
                                    "raw": recipient.get("raw", ""),
                                    "email": recipient.get("email", ""),
                                    "firstName": recipient.get("firstName", ""),
                                    "lastName": recipient.get("lastName", "")
                                } for recipient in metadata.get("cc", [])],
                                "bcc": [{
                                    "raw": recipient.get("raw", ""),
                                    "email": recipient.get("email", ""),
                                    "firstName": recipient.get("firstName", ""),
                                    "lastName": recipient.get("lastName", "")
                                } for recipient in metadata.get("bcc", [])],
                                "sender": {
                                    "email": metadata.get("sender", {}).get("email", "")
                                },
                                "body": metadata.get("text", "") or metadata.get("html", "")
                            }
                        elif engagement_data.get("type") == "TASK":
                            formatted_engagement["content"] = {
                                "subject": metadata.get("subject", ""),
                                "body": metadata.get("body", ""),
                                "status": metadata.get("status", ""),
                                "for_object_type": metadata.get("forObjectType", "")
                            }
                        elif engagement_data.get("type") == "MEETING":
                            formatted_engagement["content"] = {
                                "title": metadata.get("title", ""),
                                "body": metadata.get("body", ""),
                                "start_time": metadata.get("startTime"),
                                "end_time": metadata.get("endTime"),
                                "internal_notes": metadata.get("internalMeetingNotes", "")
                            }
                        elif engagement_data.get("type") == "CALL":
                            formatted_engagement["content"] = {
                                "body": metadata.get("body", ""),
                                "from_number": metadata.get("fromNumber", ""),
                                "to_number": metadata.get("toNumber", ""),
                                "duration_ms": metadata.get("durationMilliseconds"),
                                "status": metadata.get("status", ""),
                                "disposition": metadata.get("disposition", "")
                            }
                        
                        activities.append(formatted_engagement)
                
                # Check if there are more results to fetch
                if not response.get('hasMore', False):
                    break
                    
                # Get next page offset
                offset = response.get('offset')
            
            # Convert any datetime fields and return
            converted_activities = convert_datetime_fields(activities)
            return json.dumps(converted_activities)
            
        except ApiException as e:
            logger.error(f"API Exception: {str(e)}")
            return json.dumps({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception: {str(e)}")
            return json.dumps({"error": str(e)})

async def main(access_token: Optional[str] = None):
    """Run the HubSpot MCP server."""
    logger.info("Server starting")
    hubspot = HubSpotClient(access_token)
    server = Server("hubspot-manager")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl("hubspot://hubspot_contacts"),
                name="HubSpot Contacts",
                description="List of HubSpot contacts",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("hubspot://hubspot_companies"),
                name="HubSpot Companies", 
                description="List of HubSpot companies",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("hubspot://hubspot_recent_engagements"),
                name="HubSpot Recent Engagements",
                description="HubSpot engagements from all companies and contacts from the last 3 days",
                mimeType="application/json",
            )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        if uri.scheme != "hubspot":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        path = str(uri).replace("hubspot://", "")
        if path == "hubspot_contacts":
            return str(hubspot.get_contacts())
        elif path == "hubspot_companies":
            return str(hubspot.get_companies())
        elif path == "hubspot_recent_engagements":
            return str(hubspot.get_recent_activities())
        else:
            raise ValueError(f"Unknown resource path: {path}")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="hubspot_get_contacts",
                description="Get contacts from HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="hubspot_create_contact",
                description="Create a new contact in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "firstname": {"type": "string", "description": "Contact's first name"},
                        "lastname": {"type": "string", "description": "Contact's last name"},
                        "email": {"type": "string", "description": "Contact's email address"},
                        "properties": {"type": "object", "description": "Additional contact properties"}
                    },
                    "required": ["firstname", "lastname"]
                },
            ),
            types.Tool(
                name="hubspot_get_companies",
                description="Get companies from HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="hubspot_create_company",
                description="Create a new company in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Company name"},
                        "properties": {"type": "object", "description": "Additional company properties"}
                    },
                    "required": ["name"]
                },
            ),
            types.Tool(
                name="hubspot_get_company_activity",
                description="Get activity history for a specific company",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "HubSpot company ID"}
                    },
                    "required": ["company_id"]
                },
            ),
            types.Tool(
                name="hubspot_get_recent_engagements",
                description="Get HubSpot engagements from all companies and contacts from the last 3 days",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="hubspot_update_contact",
                description="Update an existing contact in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {"type": "string", "description": "HubSpot contact ID"},
                        "properties": {
                            "type": "object",
                            "description": "Properties to update for the contact",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["contact_id", "properties"]
                },
            ),
            types.Tool(
                name="hubspot_update_company",
                description="Update an existing company in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_id": {"type": "string", "description": "HubSpot company ID"},
                        "properties": {
                            "type": "object",
                            "description": "Properties to update for the company",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["company_id", "properties"]
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "hubspot_get_contacts":
                results = hubspot.get_contacts()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "hubspot_create_contact":
                if not arguments:
                    raise ValueError("Missing arguments for create_contact")
                
                firstname = arguments["firstname"]
                lastname = arguments["lastname"]
                company = arguments.get("properties", {}).get("company")
                
                # Search for existing contacts with same name and company
                try:
                    from hubspot.crm.contacts import PublicObjectSearchRequest
                    
                    filter_groups = [{
                        "filters": [
                            {
                                "propertyName": "firstname",
                                "operator": "EQ",
                                "value": firstname
                            },
                            {
                                "propertyName": "lastname",
                                "operator": "EQ",
                                "value": lastname
                            }
                        ]
                    }]
                    
                    # Add company filter if provided
                    if company:
                        filter_groups[0]["filters"].append({
                            "propertyName": "company",
                            "operator": "EQ",
                            "value": company
                        })
                    
                    search_request = PublicObjectSearchRequest(
                        filter_groups=filter_groups
                    )
                    
                    search_response = hubspot.client.crm.contacts.search_api.do_search(
                        public_object_search_request=search_request
                    )
                    
                    if search_response.total > 0:
                        # Contact already exists
                        return [types.TextContent(
                            type="text", 
                            text=f"Contact already exists: {search_response.results[0].to_dict()}"
                        )]
                    
                    # If no existing contact found, proceed with creation
                    properties = {
                        "firstname": firstname,
                        "lastname": lastname
                    }
                    
                    # Add email if provided
                    if "email" in arguments:
                        properties["email"] = arguments["email"]
                    
                    # Add any additional properties
                    if "properties" in arguments:
                        properties.update(arguments["properties"])
                    
                    # Create contact using SimplePublicObjectInputForCreate
                    simple_public_object_input = SimplePublicObjectInputForCreate(
                        properties=properties
                    )
                    
                    api_response = hubspot.client.crm.contacts.basic_api.create(
                        simple_public_object_input_for_create=simple_public_object_input
                    )
                    return [types.TextContent(type="text", text=str(api_response.to_dict()))]
                    
                except ApiException as e:
                    return [types.TextContent(type="text", text=f"HubSpot API error: {str(e)}")]

            elif name == "hubspot_get_companies":
                results = hubspot.get_companies()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "hubspot_create_company":
                if not arguments:
                    raise ValueError("Missing arguments for create_company")
                
                company_name = arguments["name"]
                
                # Search for existing companies with same name
                try:
                    from hubspot.crm.companies import PublicObjectSearchRequest
                    
                    search_request = PublicObjectSearchRequest(
                        filter_groups=[{
                            "filters": [
                                {
                                    "propertyName": "name",
                                    "operator": "EQ",
                                    "value": company_name
                                }
                            ]
                        }]
                    )
                    
                    search_response = hubspot.client.crm.companies.search_api.do_search(
                        public_object_search_request=search_request
                    )
                    
                    if search_response.total > 0:
                        # Company already exists
                        return [types.TextContent(
                            type="text", 
                            text=f"Company already exists: {search_response.results[0].to_dict()}"
                        )]
                    
                    # If no existing company found, proceed with creation
                    properties = {
                        "name": company_name
                    }
                    
                    # Add any additional properties
                    if "properties" in arguments:
                        properties.update(arguments["properties"])
                    
                    # Create company using SimplePublicObjectInputForCreate
                    simple_public_object_input = SimplePublicObjectInputForCreate(
                        properties=properties
                    )
                    
                    api_response = hubspot.client.crm.companies.basic_api.create(
                        simple_public_object_input_for_create=simple_public_object_input
                    )
                    return [types.TextContent(type="text", text=str(api_response.to_dict()))]
                    
                except ApiException as e:
                    return [types.TextContent(type="text", text=f"HubSpot API error: {str(e)}")]

            elif name == "hubspot_get_company_activity":
                if not arguments:
                    raise ValueError("Missing arguments for get_company_activity")
                results = hubspot.get_company_activity(arguments["company_id"])
                return [types.TextContent(type="text", text=results)]

            elif name == "hubspot_get_recent_engagements":
                results = hubspot.get_recent_activities()
                return [types.TextContent(type="text", text=str(results))]

            elif name == "hubspot_update_contact":
                if not arguments:
                    raise ValueError("Missing arguments for update_contact")
                
                contact_id = arguments["contact_id"]
                properties = arguments["properties"]
                
                # Validate properties
                if not isinstance(properties, dict):
                    raise ValueError("Properties must be a dictionary")
                
                results = hubspot.update_contact(contact_id, properties)
                return [types.TextContent(type="text", text=str(results))]

            elif name == "hubspot_update_company":
                if not arguments:
                    raise ValueError("Missing arguments for update_company")
                
                company_id = arguments["company_id"]
                properties = arguments["properties"]
                
                # Validate properties
                if not isinstance(properties, dict):
                    raise ValueError("Properties must be a dictionary")
                
                results = hubspot.update_company(company_id, properties)
                return [types.TextContent(type="text", text=str(results))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except ApiException as e:
            return [types.TextContent(type="text", text=f"HubSpot API error: {str(e)}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="hubspot",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
