import pytest
from mcp_server_hubspot.server import HubSpotClient
import mcp.types as types
from mcp.server import Server

@pytest.fixture
def hubspot_client(hubspot_token):
    """Fixture to create a HubSpot client instance"""
    return HubSpotClient(hubspot_token)

@pytest.fixture
def server():
    """Fixture to create a Server instance"""
    return Server("hubspot-manager")

@pytest.mark.asyncio
async def test_update_contact(hubspot_client, server):
    """Test updating a contact through the HubSpot API"""
    # First get a list of contacts to get a valid ID
    contacts_json = hubspot_client.get_contacts()
    contacts = eval(contacts_json)  # Convert string to Python object
    
    if not contacts or isinstance(contacts, dict) and "error" in contacts:
        pytest.skip("No contacts available to test with")
    
    # Get the first contact's ID
    contact_id = contacts[0]["id"]
    
    # Test direct client update
    update_result = hubspot_client.update_contact(
        contact_id=contact_id,
        properties={
            "firstname": "Updated",
            "lastname": "Contact",
            "email": "updated@example.com"
        }
    )
    
    # Verify the result
    response = eval(update_result)  # Convert string to Python object
    assert "error" not in response, f"Update failed: {response.get('error')}"
    assert response["properties"]["firstname"] == "Updated"
    assert response["properties"]["lastname"] == "Contact"
    assert response["properties"]["email"] == "updated@example.com"

@pytest.mark.asyncio
async def test_update_contact_invalid_id(hubspot_client):
    """Test updating a contact with an invalid ID"""
    result = hubspot_client.update_contact(
        contact_id="invalid_id",
        properties={
            "firstname": "Test",
            "lastname": "Contact"
        }
    )
    
    response = eval(result)
    assert "error" in response
