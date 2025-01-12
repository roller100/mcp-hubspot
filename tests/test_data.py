"""Test data for HubSpot integration tests"""

TEST_COMPANIES = [
    {
        "properties": {
            "name": "Acme Corporation",
            "domain": "acme.com",
            "industry": "BUSINESS_SUPPLIES_AND_EQUIPMENT",
            "description": "Leading manufacturer of innovative products",
            "city": "San Francisco",
            "country": "United States"
        }
    },
    {
        "properties": {
            "name": "Acme Industries",
            "domain": "acmeindustries.com",
            "industry": "INDUSTRIAL_AUTOMATION",
            "description": "Industrial solutions provider",
            "city": "Chicago",
            "country": "United States"
        }
    },
    {
        "properties": {
            "name": "TechCorp Solutions",
            "domain": "techcorp.com",
            "industry": "COMPUTER_SOFTWARE",
            "description": "Enterprise software solutions",
            "city": "Boston",
            "country": "United States"
        }
    }
]

UPDATED_COMPANY = {
    "properties": {
        "name": "Acme Corporation",
        "domain": "acme.com",
        "industry": "COMPUTER_SOFTWARE",  # Updated industry
        "description": "Leading manufacturer of innovative products and solutions",  # Updated description
        "city": "San Francisco",
        "country": "United States"
    }
}

SEARCH_CRITERIA = {
    "exact_name": {
        "name": "Acme Corporation"
    },
    "fuzzy_name": {
        "name": "Acme Corp"
    },
    "domain": {
        "domain": "acme.com"
    },
    "industry": {
        "industry": "BUSINESS_SUPPLIES_AND_EQUIPMENT"
    },
    "multiple_fields": {
        "name": "Acme",
        "industry": "BUSINESS_SUPPLIES_AND_EQUIPMENT"
    }
}

TEST_CONTACT = {
    "properties": {
        "firstname": "Testing 1",
        "lastname": "Testing 1",
        "email": "test1@example.com",
        "phone": "1234567890",
        "company": "Test Company",
        "website": "http://test.com",
        "address": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "zip": "12345"
    }
}

UPDATED_CONTACT = {
    "properties": {
        "firstname": "Testing 1",
        "lastname": "Testing 1",
        "email": "test1@example.com",
        "phone": "1234567891",  # Changed last digit
        "company": "Test Company",
        "website": "http://test.com",
        "address": "123 Test St",
        "city": "Test City",
        "state": "TS",
        "zip": "12345"
    }
}
