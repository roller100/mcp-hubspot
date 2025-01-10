import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables at import time
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / '.env'

print(f"Looking for .env file at: {dotenv_path}")
print(f"File exists: {dotenv_path.exists()}")

load_dotenv(dotenv_path)

token = os.getenv('HUBSPOT_ACCESS_TOKEN')
print(f"Loaded token: {'[FOUND]' if token else '[NOT FOUND]'}")

@pytest.fixture(scope="session")
def hubspot_token():
    """Fixture to provide the HubSpot API token"""
    token = os.getenv('HUBSPOT_ACCESS_TOKEN')
    if not token:
        pytest.skip("HUBSPOT_ACCESS_TOKEN not found in .env file")
    return token
