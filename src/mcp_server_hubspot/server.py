#!/usr/bin/env python3
from typing import Dict, Any, List
from urllib.parse import urlparse
import json
import os
from hubspot import HubSpot
from .industries import normalize_industry, is_valid_industry

from mcp.server import Server as McpServer
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    ListToolsRequest,
)

class HubSpotClient:
    def __init__(self, api_key: str):
        self.client = HubSpot(access_token=api_key)

    def _match_domains(self, criteria_domain: str, company_domain: str) -> float:
        """Match domains with support for variations and subdomains"""
        if not criteria_domain or not company_domain:
            return 0.0

        def normalize_domain(domain: str) -> str:
            """Normalize domain by removing www, http(s), and trailing slashes"""
            # Remove protocol if present
            if "://" in domain:
                domain = urlparse(domain).netloc
            # Remove www
            if domain.startswith("www."):
                domain = domain[4:]
            # Remove trailing slash and spaces
            domain = domain.rstrip("/").strip().lower()
            return domain

        criteria_domain = normalize_domain(criteria_domain)
        company_domain = normalize_domain(company_domain)

        # Exact match
        if criteria_domain == company_domain:
            return 1.0

        # Check if criteria domain is a subdomain of company domain or vice versa
        if criteria_domain.endswith("." + company_domain) or company_domain.endswith("." + criteria_domain):
            return 0.9

        # Check for partial matches (e.g., "example" matches "example.com")
        base_criteria = criteria_domain.split(".")[0]
        base_company = company_domain.split(".")[0]
        
        if base_criteria == base_company:
            return 0.8
        
        # Use Levenshtein for fuzzy matching of base domains
        base_similarity = self.levenshtein_ratio(base_criteria, base_company)
        if base_similarity > 0.8:
            return base_similarity * 0.7  # Scale down fuzzy matches

        return 0.0

    def levenshtein_ratio(self, s1: str, s2: str) -> float:
        """Calculate the similarity ratio between two strings using Levenshtein distance"""
        if not s1 or not s2:
            return 0.0
        
        # Get lengths of both strings
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
            
        # Create matrix of zeros
        matrix = [[0 for x in range(len2 + 1)] for x in range(len1 + 1)]
        
        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
            
        # Fill rest of the matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i-1] == s2[j-1]:
                    matrix[i][j] = matrix[i-1][j-1]
                else:
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,    # deletion
                        matrix[i][j-1] + 1,    # insertion
                        matrix[i-1][j-1] + 1   # substitution
                    )
        
        distance = float(matrix[len1][len2])
        max_len = float(max(len1, len2))
        
        # Convert distance to similarity ratio
        return 1.0 - (distance / max_len)

    def _calculate_match_score(self, company: Dict[str, Any], criteria: Dict[str, Any], fuzzy_match: bool) -> float:
        """Calculate how well a company matches the search criteria"""
        score = 0.0
        total_weight = 0.0
        weights = {
            "name": 0.4,
            "domain": 0.3,
            "industry": 0.2,
            "other": 0.1
        }

        properties = company.get("properties", {})
        if not properties:
            return 0.0

        # Track which criteria were actually used
        used_criteria = set()
        
        # Initialize match flags
        name_matched = False
        industry_matched = False

        # Name matching with improved fuzzy logic
        if "name" in criteria and "name" in properties and properties["name"] is not None:
            used_criteria.add("name")
            criteria_name = criteria["name"].lower().strip()
            company_name = properties["name"].lower().strip()
            
            # Exact match gets perfect score
            if criteria_name == company_name:
                return 1.0  # Perfect match should always return 1.0
            # Partial exact match (e.g., "Acme" matches "Acme Corporation")
            elif criteria_name in company_name:
                score += weights["name"] * 0.95  # High score for partial matches
                name_matched = True
            # Fuzzy match if enabled
            elif fuzzy_match:
                name_score = self.levenshtein_ratio(criteria_name, company_name)
                if name_score > 0.5:
                    # Boost score for very close matches
                    if name_score > 0.9:
                        name_score = 1.0
                    elif name_score > 0.8:
                        name_score = 0.95
                    elif name_score > 0.7:
                        name_score = 0.9
                    score += weights["name"] * name_score
                    name_matched = name_score > 0.8
        total_weight += weights["name"]

        # Domain matching with variations
        if "domain" in criteria and "domain" in properties and properties["domain"] is not None:
            used_criteria.add("domain")
            domain_score = self._match_domains(criteria["domain"], properties["domain"])
            if domain_score > 0:  # Only count if there's some match
                score += weights["domain"] * domain_score
            total_weight += weights["domain"]

        # Industry matching with improved normalization and aliases
        if "industry" in criteria and "industry" in properties and properties["industry"] is not None:
            used_criteria.add("industry")
        
            
            criteria_industry = normalize_industry(criteria["industry"])
            company_industry = normalize_industry(properties["industry"])
            
            # Exact match gets full score
            if criteria_industry == company_industry:
                score += weights["industry"]
                industry_matched = True
            # Fuzzy match if enabled
            elif fuzzy_match:
                industry_score = self.levenshtein_ratio(criteria_industry, company_industry)
                if industry_score > 0.6:
                    # Boost score for very close matches
                    if industry_score > 0.9:
                        industry_score = 1.0
                    elif industry_score > 0.8:
                        industry_score = 0.95
                    elif industry_score > 0.7:
                        industry_score = 0.9
                    score += weights["industry"] * industry_score
                    industry_matched = industry_score > 0.8
            total_weight += weights["industry"]

        # Other properties
        other_props = {k: v for k, v in criteria.items() if k not in ["name", "domain", "industry"]}
        if other_props:
            other_score = 0.0
            matched_props = 0
            for prop, value in other_props.items():
                used_criteria.add(prop)
                if prop in properties and properties[prop] is not None:
                    if str(value).lower() == str(properties[prop]).lower():
                        other_score += 1.0
                        matched_props += 1
                    elif fuzzy_match:
                        prop_score = self.levenshtein_ratio(str(value).lower(), str(properties[prop]).lower())
                        if prop_score > 0.7:  # Only count if similarity is above threshold
                            other_score += prop_score
                            matched_props += 1
            
            if matched_props > 0:
                score += weights["other"] * (other_score / matched_props)
            total_weight += weights["other"]

        # If no criteria matched or total weight is 0, return 0
        if not used_criteria or total_weight == 0:
            return 0.0

        # For exact name matches, boost the final score
        if "name" in criteria and name_matched:
            score *= 1.2  # 20% boost for name matches

        # For industry matches, boost the final score
        if "industry" in criteria and industry_matched:
            score *= 1.1  # 10% boost for industry matches

        # Normalize score based on weights actually used and cap at 1.0
        final_score = min(1.0, score / total_weight if total_weight > 0 else 0.0)
        return final_score
        
    def find_companies(self, criteria: Dict[str, Any], fuzzy_match: bool = True, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find companies matching the given criteria
        Args:
            criteria: Dict of company properties to match against
            fuzzy_match: Whether to use fuzzy matching for strings
            threshold: Minimum match score to include in results (0.0 to 1.0)
        Returns:
            List of matching companies with their match scores and details
        """
        print(f"Searching companies with criteria: {criteria}")
        if "industry" in criteria:
            print(f"Industry search criteria: {criteria['industry']}, normalized: {normalize_industry(criteria['industry'])}")
        
        all_companies = []
        after = None
        
        while True:
            companies_page = self.client.crm.companies.basic_api.get_page(after=after)
            if not companies_page.results:
                break
                
            for company in companies_page.results:
                match_details = {}
                properties = company.properties
                
                # Name matching
                name_score = 0.0
                if "name" in criteria and "name" in properties and properties["name"] is not None:
                    company_name = str(properties["name"]).lower()
                    criteria_name = str(criteria["name"]).lower()
                    if criteria_name == company_name:
                        name_score = 1.0
                    elif criteria_name in company_name:
                        name_score = 0.9
                    elif fuzzy_match:
                        name_score = self.levenshtein_ratio(criteria["name"].lower(), properties["name"].lower())
                    if name_score > 0:
                        match_details["name"] = {"match_score": name_score}
                
                # Domain matching
                domain_score = 0.0
                if "domain" in criteria and "domain" in properties:
                    domain_score = self._match_domains(criteria["domain"], properties["domain"])
                    if domain_score > 0:
                        match_details["domain"] = {"match_score": domain_score}
                
                # Industry matching with improved handling
                industry_score = 0.0
                if "industry" in criteria:
                    criteria_industry = normalize_industry(criteria["industry"])
                    if "industry" in properties and properties["industry"]:
                        try:
                            company_industry = normalize_industry(properties["industry"])
                            print(f"Comparing industries - Criteria: {criteria_industry}, Company: {company_industry}")
                            if criteria_industry == company_industry:
                                industry_score = 1.0
                                print(f"Exact industry match for company {properties.get('name', 'Unknown')}")
                            elif fuzzy_match:
                                industry_score = self.levenshtein_ratio(criteria_industry, company_industry)
                                print(f"Fuzzy industry match score: {industry_score}")
                            if industry_score > 0:
                                match_details["industry"] = {"match_score": industry_score}
                        except ValueError:
                            print(f"Invalid industry format for company {properties.get('name', 'Unknown')}: {properties['industry']}")
                    else:
                        print(f"Industry mismatch - Company {properties.get('name', 'Unknown')} - Has industry: {'industry' in properties}, Value: {properties.get('industry')}")
                
                # Calculate overall score
                total_score = 0.0
                weights = {"name": 0.5, "domain": 0.3, "industry": 0.2}
                total_weight = 0.0
                
                # Always include criteria weights in total_weight if they were searched for
                if "name" in criteria:
                    if "name" in match_details:
                        total_score += name_score * weights["name"]
                    total_weight += weights["name"]
                if "domain" in criteria:
                    if "domain" in match_details:
                        total_score += domain_score * weights["domain"]
                    total_weight += weights["domain"]
                if "industry" in criteria:
                    if "industry" in match_details:
                        total_score += industry_score * weights["industry"]
                    total_weight += weights["industry"]
                
                match_score = total_score / total_weight if total_weight > 0 else 0.0
                
                if match_score >= threshold:
                    # Convert SimplePublicObjectWithAssociations to dict
                    company_dict = {
                        "id": company.id,
                        "properties": company.properties,
                        "created_at": company.created_at.isoformat() if company.created_at else None,
                        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
                        "archived": company.archived
                    }
                    all_companies.append({
                        "company": company_dict,
                        "match_score": match_score,
                        "match_details": match_details
                    })
                    
            if not companies_page.paging:
                break
            after = companies_page.paging.next.after
            
        # Sort by match_score descending
        all_companies.sort(key=lambda x: x["match_score"], reverse=True)
        return all_companies

    def create_or_update_company(self, company_data: Dict[str, Any], fuzzy_match: bool = True, match_threshold: float = 0.8, test_mode: bool = False, allow_custom_industry: bool = False) -> Dict[str, Any]:
        """
        Create a new company or update existing if found
        Args:
            company_data: Company properties
            fuzzy_match: Whether to use fuzzy matching to find existing
            match_threshold: Minimum score to consider a match
            test_mode: Whether to use test subset of industries
            allow_custom_industry: Whether to allow custom industry values
        Returns:
            Created or updated company record
        """
        # Validate and normalize industry if present
        if "industry" in company_data:
            try:
                # This will raise ValueError if invalid
                is_valid_industry(company_data["industry"], test_mode, allow_custom_industry)
                # Normalize industry to approved format
                company_data["industry"] = normalize_industry(company_data["industry"], test_mode)
            except ValueError as e:
                raise ValueError(f"Industry validation failed: {str(e)}")
        # Try to find existing company
        matches = self.find_companies(company_data, fuzzy_match=fuzzy_match, threshold=match_threshold)
        
        if matches:
            # Update existing company
            best_match = matches[0]["company"]
            updated = self.client.crm.companies.basic_api.update(
                company_id=best_match.id,
                simple_public_object_input={"properties": company_data}
            )
            return updated
            
        # Create new company
        created = self.client.crm.companies.basic_api.create(
            simple_public_object_input_for_create={"properties": company_data}
        )
        return created

    def update_company(self, company_id: str, properties: Dict[str, Any], test_mode: bool = False, allow_custom_industry: bool = False) -> str:
        """
        Update an existing company by ID
        Args:
            company_id: HubSpot company ID
            properties: Company properties to update
        Returns:
            JSON string of updated company or error
        """
        # Validate industry if present
        if "industry" in properties:
            if not is_valid_industry(properties["industry"], test_mode, allow_custom_industry):
                raise ValueError(f"Invalid industry: {properties['industry']}. Must be one of the approved industries or a valid custom value.")
            try:
                # Normalize industry to approved format
                properties["industry"] = normalize_industry(properties["industry"], test_mode)
            except ValueError as e:
                raise ValueError(f"Industry format error: {str(e)}")
        try:
            result = self.client.crm.companies.basic_api.update(
                company_id=company_id,
                simple_public_object_input={"properties": properties}
            )
            return json.dumps({"id": result.id, "properties": result.properties})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def batch_update_companies(self, updates: List[Dict[str, Any]], test_mode: bool = False, allow_custom_industry: bool = False) -> List[Dict[str, Any]]:
        """
        Update multiple companies in batch
        Args:
            updates: List of {company_id, properties} dicts
            test_mode: Whether to use test subset of industries
            allow_custom_industry: Whether to allow custom industry values
        Returns:
            List of results with success/error status for each company
        """
        results = []
        batch_inputs = []

        # First validate all industries to fail fast if any are invalid
        for update in updates:
            properties = update.get("properties", {})
            if "industry" in properties:
                if not is_valid_industry(properties["industry"], test_mode, allow_custom_industry):
                    results.append({
                        "company_id": update["company_id"],
                        "error": f"Invalid industry: {properties['industry']}"
                    })
                    continue
                try:
                    properties["industry"] = normalize_industry(properties["industry"], test_mode)
                except ValueError as e:
                    results.append({
                        "company_id": update["company_id"],
                        "error": f"Industry format error: {str(e)}"
                    })
                    continue

            batch_inputs.append({
                "id": update["company_id"],
                "properties": properties
            })

        # If we have any valid updates, process them in batches of 100
        if batch_inputs:
            for i in range(0, len(batch_inputs), 100):
                batch = batch_inputs[i:i + 100]
                try:
                    batch_result = self.client.crm.companies.batch_api.update(
                        batch_input_simple_public_object_batch_input={"inputs": batch}
                    )
                    for status in batch_result.status:
                        if status.status_code == 200:
                            results.append({
                                "company_id": status.id,
                                "success": True,
                                "properties": status.properties
                            })
                        else:
                            results.append({
                                "company_id": status.id,
                                "error": f"Update failed: {status.message}"
                            })
                except Exception as e:
                    # If batch fails, try updating companies individually to prevent total failure
                    for company in batch:
                        try:
                            result = self.client.crm.companies.basic_api.update(
                                company_id=company["id"],
                                simple_public_object_input={"properties": company["properties"]}
                            )
                            results.append({
                                "company_id": company["id"],
                                "success": True,
                                "properties": result.properties
                            })
                        except Exception as inner_e:
                            results.append({
                                "company_id": company["id"],
                                "error": str(inner_e)
                            })

        return results

    def create_contact(self, properties: Dict[str, Any]) -> str:
        """
        Create a new contact
        Args:
            properties: Contact properties
        Returns:
            JSON string of created contact or error
        """
        try:
            # Check if contact exists first
            email = properties.get("email")
            if email:
                filter_groups = [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}]
                existing = self.client.crm.contacts.search_api.do_search(
                    public_object_search_request={"filterGroups": filter_groups}
                )
                if existing.total > 0:
                    return json.dumps({"error": f"Contact with email {email} already exists"})
                    
            result = self.client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create={"properties": properties}
            )
            return json.dumps({"id": result.id, "properties": result.properties})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def update_contact(self, contact_id: str, properties: Dict[str, Any]) -> str:
        """
        Update an existing contact by ID
        Args:
            contact_id: HubSpot contact ID
            properties: Contact properties to update
        Returns:
            JSON string of updated contact or error
        """
        try:
            result = self.client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input={"properties": properties}
            )
            return json.dumps({"id": result.id, "properties": result.properties})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def delete_contact(self, contact_id: str) -> str:
        """
        Delete a contact by ID
        Args:
            contact_id: HubSpot contact ID
        Returns:
            JSON string indicating success or error
        """
        try:
            self.client.crm.contacts.basic_api.archive(contact_id=contact_id)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

class Server:
    """MCP Server implementation for HubSpot integration"""
    
    def __init__(self):
        api_key = os.getenv("HUBSPOT_API_KEY")
        if not api_key:
            raise ValueError("HUBSPOT_API_KEY environment variable is required")
            
        self.hubspot = HubSpotClient(api_key)
        self.server = McpServer(
            {
                "name": "hubspot-server",
                "version": "0.1.0",
            },
            {
                "capabilities": {
                    "tools": {},
                }
            }
        )
        
        self.setup_tool_handlers()
        
        # Error handling
        self.server.onerror = lambda error: print(f"[MCP Error] {error}", file=sys.stderr)
        
    def setup_tool_handlers(self):
        """Set up handlers for MCP tools"""
        
        self.server.request_handlers[ListToolsRequest] = self.handle_list_tools
        self.server.request_handlers[CallToolRequest] = self.handle_call_tool
        
    async def handle_list_tools(self, request):
        """Handle listing available tools"""
        return {
            "tools": [
                {
                    "name": "find_companies",
                    "description": "Find companies matching given criteria with fuzzy matching support",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "criteria": {
                                "type": "object",
                                "description": "Company properties to match against (name, domain, industry, etc)",
                            },
                            "fuzzy_match": {
                                "type": "boolean",
                                "description": "Whether to use fuzzy string matching",
                                "default": True
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Minimum match score (0.0 to 1.0)",
                                "default": 0.7
                            }
                        },
                        "required": ["criteria"]
                    }
                },
                {
                    "name": "create_or_update_company",
                    "description": "Create a new company or update if matching company found",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "company_data": {
                                "type": "object",
                                "description": "Company properties"
                            },
                            "fuzzy_match": {
                                "type": "boolean",
                                "description": "Whether to use fuzzy matching to find existing",
                                "default": True
                            },
                            "match_threshold": {
                                "type": "number",
                                "description": "Minimum score to consider a match",
                                "default": 0.8
                            },
                            "test_mode": {
                                "type": "boolean",
                                "description": "Whether to use test subset of industries",
                                "default": False
                            }
                        },
                        "required": ["company_data"]
                    }
                },
                {
                    "name": "update_company",
                    "description": "Update an existing company by ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "company_id": {
                                "type": "string",
                                "description": "HubSpot company ID"
                            },
                            "properties": {
                                "type": "object",
                                "description": "Company properties to update"
                            },
                            "test_mode": {
                                "type": "boolean",
                                "description": "Whether to use test subset of industries",
                                "default": False
                            }
                        },
                        "required": ["company_id", "properties"]
                    }
                },
                {
                    "name": "create_contact",
                    "description": "Create a new contact",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "properties": {
                                "type": "object",
                                "description": "Contact properties"
                            }
                        },
                        "required": ["properties"]
                    }
                },
                {
                    "name": "update_contact",
                    "description": "Update an existing contact by ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "HubSpot contact ID"
                            },
                            "properties": {
                                "type": "object",
                                "description": "Contact properties to update"
                            }
                        },
                        "required": ["contact_id", "properties"]
                    }
                },
                {
                    "name": "delete_contact",
                    "description": "Delete a contact by ID",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "HubSpot contact ID"
                            }
                        },
                        "required": ["contact_id"]
                    }
                }
            ]
        }
        
    async def handle_call_tool(self, request):
        """Handle tool execution requests"""
        try:
            tool_name = request.params.name
            args = request.params.arguments
            
            if tool_name == "find_companies":
                result = self.hubspot.find_companies(
                    args["criteria"],
                    args.get("fuzzy_match", True),
                    args.get("threshold", 0.7)
                )
                # Convert each company object to a serializable dict
                serializable_result = []
                for item in result:
                    company_dict = item["company"]
                    serializable_result.append({
                        "company": company_dict,
                        "match_score": item["match_score"],
                        "match_details": item["match_details"]
                    })
                return {"content": [{"type": "text", "text": json.dumps(serializable_result, indent=2)}]}
                
            elif tool_name == "create_or_update_company":
                result = self.hubspot.create_or_update_company(
                    args["company_data"],
                    args.get("fuzzy_match", True),
                    args.get("match_threshold", 0.8),
                    args.get("test_mode", False)
                )
                # Convert company object to a serializable dict
                result_dict = {
                    "id": result.id,
                    "properties": result.properties,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                    "archived": result.archived
                }
                return {"content": [{"type": "text", "text": json.dumps(result_dict, indent=2)}]}
                
            elif tool_name == "update_company":
                result = self.hubspot.update_company(
                    args["company_id"],
                    args["properties"],
                    args.get("test_mode", False)
                )
                return {"content": [{"type": "text", "text": result}]}
                
            elif tool_name == "create_contact":
                result = self.hubspot.create_contact(args["properties"])
                return {"content": [{"type": "text", "text": result}]}
                
            elif tool_name == "update_contact":
                result = self.hubspot.update_contact(
                    args["contact_id"],
                    args["properties"]
                )
                return {"content": [{"type": "text", "text": result}]}
                
            elif tool_name == "delete_contact":
                result = self.hubspot.delete_contact(args["contact_id"])
                return {"content": [{"type": "text", "text": result}]}
                
            else:
                raise Exception(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            raise Exception(str(e))
            
    async def run(self):
        """Run the MCP server"""
        async with stdio_server(self.server) as server:
            print("HubSpot MCP server running on stdio", file=sys.stderr)
            await server.serve_forever()

if __name__ == "__main__":
    import sys
    import asyncio
    
    server = Server()
    asyncio.run(server.run())
