"""Test data for HubSpot integration tests"""

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
