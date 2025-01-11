import pytest
import json
from mcp_server_hubspot.server import HubSpotClient
import mcp.types as types
from mcp.server import Server
from tests.test_data import TEST_CONTACT, UPDATED_CONTACT

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
    """Test updating a contact through the HubSpot API using test data"""
    # Create a test contact
    create_result = hubspot_client.create_contact(TEST_CONTACT["properties"])
    create_response = json.loads(create_result)
    assert "error" not in create_response, f"Create failed: {create_response.get('error')}"
    
    contact_id = create_response["id"]
    
    try:
        # Update the test contact
        update_result = hubspot_client.update_contact(
            contact_id=contact_id,
            properties=UPDATED_CONTACT["properties"]
        )
        
        # Verify the update
        update_response = json.loads(update_result)
        assert "error" not in update_response, f"Update failed: {update_response.get('error')}"
        assert update_response["properties"]["phone"] == UPDATED_CONTACT["properties"]["phone"]
        
        # Verify other properties remained unchanged
        for key in ["firstname", "lastname", "email", "company"]:
            assert update_response["properties"][key] == TEST_CONTACT["properties"][key]
            
    finally:
        # Clean up - delete the test contact
        delete_result = hubspot_client.delete_contact(contact_id)
        delete_response = json.loads(delete_result)
        assert "error" not in delete_response, f"Delete failed: {delete_response.get('error')}"

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
    
    response = json.loads(result)
    assert "error" in response
