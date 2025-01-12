import pytest
import json
import os
from mcp_server_hubspot.server import HubSpotClient, Server
from mcp_server_hubspot.industries import normalize_industry, is_valid_industry
from mcp.types import CallToolRequest, ListToolsRequest
from tests.test_data import (
    TEST_CONTACT, 
    UPDATED_CONTACT, 
    TEST_COMPANIES, 
    UPDATED_COMPANY,
    SEARCH_CRITERIA
)

@pytest.fixture
async def hubspot_client(hubspot_token):
    """Fixture to create a HubSpot client instance"""
    client = HubSpotClient(hubspot_token)
    
    # Create test companies
    company_ids = []
    for company in TEST_COMPANIES:
        try:
            result = client.client.crm.companies.basic_api.create(
                simple_public_object_input_for_create={"properties": company["properties"]}
            )
            company_ids.append(result.id)
            print(f"Created test company: {company['properties']['name']} with ID: {result.id}")
        except Exception as e:
            print(f"Error creating test company {company['properties']['name']}: {str(e)}")
    
    try:
        yield client
    finally:
        # Clean up test companies
        for company_id in company_ids:
            try:
                client.client.crm.companies.basic_api.archive(company_id=company_id)
                print(f"Cleaned up test company with ID: {company_id}")
            except Exception as e:
                print(f"Error cleaning up company {company_id}: {str(e)}")

@pytest.fixture
async def mcp_server(hubspot_token):
    """Fixture to create an MCP Server instance"""
    os.environ["HUBSPOT_API_KEY"] = hubspot_token
    server = Server()
    try:
        yield server
    finally:
        del os.environ["HUBSPOT_API_KEY"]

# HubSpotClient Tests

@pytest.mark.asyncio
async def test_find_companies_exact_name(hubspot_client):
    """Test finding companies by exact name match"""
    client = await hubspot_client.__anext__()
    results = client.find_companies(SEARCH_CRITERIA["exact_name"])
    
    assert len(results) >= 1, "Should find at least one company"
    best_match = results[0]
    assert best_match["match_score"] == 1.0, "Should have perfect match score"
    assert best_match["company"]["properties"]["name"] == "Acme Corporation"
    assert "name" in best_match["match_details"], "Should include match details"

@pytest.mark.asyncio
async def test_find_companies_fuzzy_name(hubspot_client):
    """Test finding companies with fuzzy name matching"""
    client = await hubspot_client.__anext__()
    results = client.find_companies(SEARCH_CRITERIA["fuzzy_name"])
    
    assert len(results) >= 1, "Should find at least one company"
    best_match = results[0]
    assert best_match["match_score"] > 0.8, "Should have high match score"
    assert "Acme" in best_match["company"]["properties"]["name"]
    assert best_match["match_details"]["name"]["match_score"] > 0.8

@pytest.mark.asyncio
async def test_find_companies_domain(hubspot_client):
    """Test finding companies by domain"""
    client = await hubspot_client.__anext__()
    results = client.find_companies(SEARCH_CRITERIA["domain"])
    
    assert len(results) >= 1, "Should find at least one company"
    best_match = results[0]
    assert best_match["company"]["properties"]["domain"] == "acme.com"
    assert "domain" in best_match["match_details"]

@pytest.mark.asyncio
async def test_find_companies_industry(hubspot_client):
    """Test finding companies by industry"""
    client = await hubspot_client.__anext__()
    results = client.find_companies(SEARCH_CRITERIA["industry"])
    
    assert len(results) >= 1, "Should find companies with matching industry"
    for result in results[:1]:
        assert result["company"]["properties"]["industry"] == "BUSINESS_SUPPLIES_AND_EQUIPMENT"
        assert "industry" in result["match_details"]

@pytest.mark.asyncio
async def test_find_companies_multiple_criteria(hubspot_client):
    """Test finding companies with multiple search criteria"""
    client = await hubspot_client.__anext__()
    results = client.find_companies(SEARCH_CRITERIA["multiple_fields"])
    
    assert len(results) >= 1, "Should find Acme companies with matching industry"
    for result in results[:1]:
        assert "Acme" in result["company"]["properties"]["name"]
        assert result["company"]["properties"]["industry"] == "BUSINESS_SUPPLIES_AND_EQUIPMENT"
        assert "name" in result["match_details"]
        assert "industry" in result["match_details"]

@pytest.mark.asyncio
async def test_find_companies_no_matches(hubspot_client):
    """Test finding companies with criteria that should return no matches"""
    client = await hubspot_client.__anext__()
    results = client.find_companies({
        "name": "Nonexistent Company XYZ",
        "domain": "nonexistent.com"
    })
    
    assert len(results) == 0, "Should not find any matches"

@pytest.mark.asyncio
async def test_update_company(hubspot_client):
    """Test updating a company's properties"""
    client = await hubspot_client.__anext__()
    # First find the company to update
    results = client.find_companies({"name": "Acme Corporation"})
    assert len(results) > 0, "Test company should exist"
    
    company_id = results[0]["company"]["id"]
    
    try:
        # Update the company
        update_result = json.loads(client.update_company(
            company_id=company_id,
            properties=UPDATED_COMPANY["properties"]
        ))
        
        assert "error" not in update_result, f"Update failed: {update_result.get('error')}"
        
        # Verify the updates
        assert update_result["properties"]["industry"] == UPDATED_COMPANY["properties"]["industry"]
        assert update_result["properties"]["description"] == UPDATED_COMPANY["properties"]["description"]
        
        # Verify other properties remained unchanged
        for key in ["name", "domain", "city", "country"]:
            assert update_result["properties"][key] == UPDATED_COMPANY["properties"][key]
            
    except Exception as e:
        pytest.fail(f"Error updating company: {str(e)}")

@pytest.mark.asyncio
async def test_update_company_invalid_id(hubspot_client):
    """Test updating a company with an invalid ID"""
    client = await hubspot_client.__anext__()
    result = json.loads(client.update_company(
        company_id="invalid_id",
        properties=UPDATED_COMPANY["properties"]
    ))
    
    assert "error" in result, "Should return error for invalid company ID"

@pytest.mark.asyncio
async def test_update_contact(hubspot_client):
    """Test updating a contact through the HubSpot API using test data"""
    client = await hubspot_client.__anext__()
    # Create a test contact
    create_result = client.create_contact(TEST_CONTACT["properties"])
    create_response = json.loads(create_result)
    assert "error" not in create_response, f"Create failed: {create_response.get('error')}"
    
    contact_id = create_response["id"]
    
    try:
        # Update the test contact
        update_result = client.update_contact(
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
        delete_result = client.delete_contact(contact_id)
        delete_response = json.loads(delete_result)
        assert "error" not in delete_response, f"Delete failed: {delete_response.get('error')}"

@pytest.mark.asyncio
async def test_update_contact_invalid_id(hubspot_client):
    """Test updating a contact with an invalid ID"""
    client = await hubspot_client.__anext__()
    result = client.update_contact(
        contact_id="invalid_id",
        properties={
            "firstname": "Test",
            "lastname": "Contact"
        }
    )
    
    response = json.loads(result)
    assert "error" in response

# MCP Server Tests

@pytest.mark.asyncio
async def test_mcp_server_initialization(mcp_server):
    """Test MCP server initialization"""
    server = await mcp_server.__anext__()
    assert server.hubspot is not None, "HubSpot client should be initialized"
    assert server.server is not None, "MCP server should be initialized"

@pytest.mark.asyncio
async def test_mcp_list_tools(mcp_server):
    """Test listing available MCP tools"""
    server = await mcp_server.__anext__()
    request = ListToolsRequest(method="tools/list", params={})
    response = await server.handle_list_tools(request)
    
    assert "tools" in response
    tools = response["tools"]
    assert len(tools) == 6  # Should have 6 tools
    
    # Verify each tool has required fields
    tool_names = set()
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        tool_names.add(tool["name"])
    
    # Verify all expected tools are present
    expected_tools = {
        "find_companies",
        "create_or_update_company",
        "update_company",
        "create_contact",
        "update_contact",
        "delete_contact"
    }
    assert tool_names == expected_tools

@pytest.mark.asyncio
async def test_mcp_find_companies(mcp_server):
    """Test find_companies tool"""
    server = await mcp_server.__anext__()
    request = CallToolRequest(method="tools/call", params={
        "name": "find_companies",
        "arguments": {
            "criteria": SEARCH_CRITERIA["exact_name"],
            "fuzzy_match": True,
            "threshold": 0.7
        }
    })
    
    response = await server.handle_call_tool(request)
    assert "content" in response
    assert len(response["content"]) == 1
    
    result = json.loads(response["content"][0]["text"])
    assert len(result) >= 1, "Should find at least one company"
    assert result[0]["match_score"] == 1.0, "Should have perfect match score"

@pytest.mark.asyncio
async def test_mcp_create_contact(mcp_server):
    """Test create_contact tool"""
    server = await mcp_server.__anext__()
    request = CallToolRequest(method="tools/call", params={
        "name": "create_contact",
        "arguments": {
            "properties": TEST_CONTACT["properties"]
        }
    })
    
    response = await server.handle_call_tool(request)
    assert "content" in response
    assert len(response["content"]) == 1
    
    result = json.loads(response["content"][0]["text"])
    assert "id" in result
    assert "properties" in result
    
    # Clean up
    delete_request = CallToolRequest(method="tools/call", params={
        "name": "delete_contact",
        "arguments": {
            "contact_id": result["id"]
        }
    })
    delete_response = await server.handle_call_tool(delete_request)
    delete_result = json.loads(delete_response["content"][0]["text"])
    assert delete_result["success"] is True

@pytest.mark.asyncio
async def test_industry_validation():
    """Test industry validation functionality in production mode"""
    # Test valid industries in production mode
    assert is_valid_industry("COMPUTER_SOFTWARE", test_mode=False)
    assert is_valid_industry("Computer Software", test_mode=False)
    assert is_valid_industry("computer software", test_mode=False)
    assert is_valid_industry("INFORMATION_TECHNOLOGY_AND_SERVICES", test_mode=False)
    
    # Test invalid industries in production mode
    assert not is_valid_industry("", test_mode=False)
    assert not is_valid_industry(None, test_mode=False)
    assert not is_valid_industry("Invalid Industry", test_mode=False)
    assert not is_valid_industry("NOT_A_REAL_INDUSTRY", test_mode=False)
    
    # Test case sensitivity validation
    with pytest.raises(ValueError) as exc_info:
        normalize_industry("Computer-Software")  # Should raise error due to mixed case
    assert "must be uppercase" in str(exc_info.value)
    
    # Test custom industry values
    assert not is_valid_industry("CUSTOM_INDUSTRY", test_mode=False)
    assert is_valid_industry("CUSTOM_INDUSTRY", test_mode=False, allow_custom=True)
    
    # Test null/empty handling
    assert normalize_industry(None) == ""
    assert normalize_industry("") == ""
    assert normalize_industry("  ") == ""

@pytest.mark.asyncio
async def test_industry_validation_test_mode():
    """Test industry validation functionality in test mode"""
    # Test valid industries in test mode
    assert is_valid_industry("BANKING", test_mode=True)
    assert is_valid_industry("Financial Services", test_mode=True)
    assert is_valid_industry("Technology", test_mode=True)
    assert is_valid_industry("E-commerce", test_mode=True)
    
    # Test invalid industries in test mode
    assert not is_valid_industry("COMPUTER_SOFTWARE", test_mode=True)
    assert not is_valid_industry("APPAREL_FASHION", test_mode=True)
    assert not is_valid_industry("", test_mode=True)
    assert not is_valid_industry(None, test_mode=True)

@pytest.mark.asyncio
async def test_industry_normalization():
    """Test industry name normalization in production mode"""
    # Test exact matches
    assert normalize_industry("COMPUTER_SOFTWARE", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry("Computer Software", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry("computer software", test_mode=False) == "COMPUTER_SOFTWARE"
    
    # Test aliases
    assert normalize_industry("Software", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry("Software Development", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry("IT", test_mode=False) == "INFORMATION_TECHNOLOGY_AND_SERVICES"
    assert normalize_industry("Technology", test_mode=False) == "INFORMATION_TECHNOLOGY_AND_SERVICES"
    assert normalize_industry("Manufacturing", test_mode=False) == "INDUSTRIAL_AUTOMATION"
    
    # Test spacing and special characters
    assert normalize_industry("Computer-Software", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry("Computer - Software", test_mode=False) == "COMPUTER_SOFTWARE"
    assert normalize_industry(" Computer Software ", test_mode=False) == "COMPUTER_SOFTWARE"

@pytest.mark.asyncio
async def test_industry_normalization_test_mode():
    """Test industry name normalization in test mode"""
    # Test exact matches in test subset
    assert normalize_industry("BANKING", test_mode=True) == "BANKING"
    assert normalize_industry("Financial Services", test_mode=True) == "FINANCIAL_SERVICES"
    assert normalize_industry("E-commerce", test_mode=True) == "E_COMMERCE"
    
    # Test aliases in test subset
    assert normalize_industry("Tech", test_mode=True) == "TECHNOLOGY"
    assert normalize_industry("Healthcare", test_mode=True) == "HEALTH_CARE"
    assert normalize_industry("Manufacturing", test_mode=True) == "MANUFACTURING"
    
    # Test spacing and special characters
    assert normalize_industry("E-Commerce", test_mode=True) == "E_COMMERCE"
    assert normalize_industry(" Financial Services ", test_mode=True) == "FINANCIAL_SERVICES"

@pytest.mark.asyncio
async def test_create_company_with_invalid_industry(hubspot_client):
    """Test creating a company with an invalid industry"""
    client = await hubspot_client.__anext__()
    
    # Test invalid industry
    invalid_company = {
        "name": "Test Company",
        "domain": "test.com",
        "industry": "INVALID_INDUSTRY"
    }
    with pytest.raises(ValueError) as exc_info:
        client.create_or_update_company(invalid_company)
    assert "Invalid industry" in str(exc_info.value)
    
    # Test case sensitivity
    mixed_case_company = {
        "name": "Test Company",
        "domain": "test.com",
        "industry": "Computer-Software"
    }
    with pytest.raises(ValueError) as exc_info:
        client.create_or_update_company(mixed_case_company)
    assert "must be uppercase" in str(exc_info.value)
    
    # Test custom industry allowed
    custom_company = {
        "name": "Test Company",
        "domain": "test.com",
        "industry": "CUSTOM_INDUSTRY_VALUE"
    }
    try:
        result = client.create_or_update_company(custom_company, allow_custom_industry=True)
        assert result.properties["industry"] == "CUSTOM_INDUSTRY_VALUE"
    except ValueError:
        pytest.fail("Should allow custom industry when allow_custom_industry=True")

@pytest.mark.asyncio
async def test_batch_update_companies(hubspot_client):
    """Test batch updating companies"""
    client = await hubspot_client.__anext__()
    
    # Create test companies
    companies = []
    for i in range(3):
        company = {
            "name": f"Test Company {i}",
            "domain": f"test{i}.com",
            "industry": "COMPUTER_SOFTWARE"
        }
        result = client.create_or_update_company(company)
        companies.append({"id": result.id, "properties": result.properties})
    
    # Test batch update with mixed valid/invalid industries
    updates = [
        {
            "company_id": companies[0]["id"],
            "properties": {"industry": "BANKING"}  # Valid industry
        },
        {
            "company_id": companies[1]["id"],
            "properties": {"industry": "Invalid-Industry"}  # Invalid case
        },
        {
            "company_id": companies[2]["id"],
            "properties": {"industry": "CUSTOM_VALUE"}  # Custom industry
        }
    ]
    
    # Test without custom industries allowed
    results = client.batch_update_companies(updates)
    assert len(results) == 3
    assert results[0]["success"]  # Valid industry should succeed
    assert "error" in results[1]  # Invalid case should fail
    assert "error" in results[2]  # Custom industry should fail without allow_custom
    
    # Test with custom industries allowed
    results = client.batch_update_companies(updates, allow_custom_industry=True)
    assert len(results) == 3
    assert results[0]["success"]  # Valid industry should succeed
    assert "error" in results[1]  # Invalid case should still fail
    assert results[2]["success"]  # Custom industry should succeed with allow_custom
    
    # Clean up test companies
    for company in companies:
        client.client.crm.companies.basic_api.archive(company_id=company["id"])

@pytest.mark.asyncio
async def test_update_company_with_invalid_industry(hubspot_client):
    """Test updating a company with an invalid industry"""
    client = await hubspot_client.__anext__()
    
    # First find a company to update
    results = client.find_companies({"name": "Acme Corporation"})
    assert len(results) > 0, "Test company should exist"
    
    company_id = results[0]["company"]["id"]
    
    # Test invalid industry
    with pytest.raises(ValueError) as exc_info:
        client.update_company(
            company_id=company_id,
            properties={"industry": "INVALID_INDUSTRY"}
        )
    assert "Invalid industry" in str(exc_info.value)
    
    # Test case sensitivity
    with pytest.raises(ValueError) as exc_info:
        client.update_company(
            company_id=company_id,
            properties={"industry": "Computer-Software"}
        )
    assert "must be uppercase" in str(exc_info.value)
    
    # Test null/empty handling
    result = json.loads(client.update_company(
        company_id=company_id,
        properties={"industry": ""}
    ))
    assert "error" not in result
    assert result["properties"]["industry"] == ""
    
    # Test custom industry
    result = json.loads(client.update_company(
        company_id=company_id,
        properties={"industry": "CUSTOM_INDUSTRY"},
        allow_custom_industry=True
    ))
    assert "error" not in result
    assert result["properties"]["industry"] == "CUSTOM_INDUSTRY"

@pytest.mark.asyncio
async def test_mcp_invalid_tool(mcp_server):
    """Test calling an invalid tool"""
    server = await mcp_server.__anext__()
    request = CallToolRequest(method="tools/call", params={
        "name": "invalid_tool",
        "arguments": {}
    })
    
    with pytest.raises(Exception) as exc_info:
        await server.handle_call_tool(request)
    assert "Unknown tool" in str(exc_info.value)
