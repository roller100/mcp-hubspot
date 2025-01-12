"""Industry validation and normalization for HubSpot companies"""

# Test subset of industries for development/testing
TEST_INDUSTRIES = {
    "BANKING",
    "FINANCIAL_SERVICES",
    "INSURANCE", 
    "FINANCE",
    "INVESTMENT_MANAGEMENT",
    "HEALTH_CARE",
    "PHARMACEUTICALS",
    "ENERGY",
    "TELECOMMUNICATIONS",
    "TRANSPORTATION",
    "TECHNOLOGY",
    "E_COMMERCE",
    "ENTERTAINMENT",
    "BUSINESS_SERVICES",
    "MANUFACTURING",
    "INFORMATION_TECHNOLOGY_AND_SERVICES"
}

# Complete list of approved industries for production
APPROVED_INDUSTRIES = {
    "ACCOUNTING",
    "AIRLINES_AVIATION",
    "ALTERNATIVE_DISPUTE_RESOLUTION",
    "ALTERNATIVE_MEDICINE",
    "ANIMATION",
    "APPAREL_FASHION",
    "ARCHITECTURE_PLANNING",
    "ARTS_AND_CRAFTS",
    "AUTOMOTIVE",
    "AVIATION_AEROSPACE",
    "BANKING",
    "BIOTECHNOLOGY",
    "BROADCAST_MEDIA",
    "BUILDING_MATERIALS",
    "BUSINESS_SUPPLIES_AND_EQUIPMENT",
    "CAPITAL_MARKETS",
    "CHEMICALS",
    "CIVIC_SOCIAL_ORGANIZATION",
    "CIVIL_ENGINEERING",
    "COMMERCIAL_REAL_ESTATE",
    "COMPUTER_NETWORK_SECURITY",
    "COMPUTER_GAMES",
    "COMPUTER_HARDWARE",
    "COMPUTER_NETWORKING",
    "COMPUTER_SOFTWARE",
    "INTERNET",
    "CONSTRUCTION",
    "CONSUMER_ELECTRONICS",
    "CONSUMER_GOODS",
    "CONSUMER_SERVICES",
    "COSMETICS",
    "DAIRY",
    "DEFENSE_SPACE",
    "DESIGN",
    "EDUCATION_MANAGEMENT",
    "E_LEARNING",
    "ELECTRICAL_ELECTRONIC_MANUFACTURING",
    "ENTERTAINMENT",
    "ENVIRONMENTAL_SERVICES",
    "EVENTS_SERVICES",
    "EXECUTIVE_OFFICE",
    "FACILITIES_SERVICES",
    "FARMING",
    "FINANCIAL_SERVICES",
    "FINE_ART",
    "FISHERY",
    "FOOD_BEVERAGES",
    "FOOD_PRODUCTION",
    "FUND_RAISING",
    "FURNITURE",
    "GAMBLING_CASINOS",
    "GLASS_CERAMICS_CONCRETE",
    "GOVERNMENT_ADMINISTRATION",
    "GOVERNMENT_RELATIONS",
    "GRAPHIC_DESIGN",
    "HEALTH_WELLNESS_AND_FITNESS",
    "HIGHER_EDUCATION",
    "HOSPITAL_HEALTH_CARE",
    "HOSPITALITY",
    "HUMAN_RESOURCES",
    "IMPORT_AND_EXPORT",
    "INDIVIDUAL_FAMILY_SERVICES",
    "INDUSTRIAL_AUTOMATION",
    "INFORMATION_SERVICES",
    "INFORMATION_TECHNOLOGY_AND_SERVICES",
    "INSURANCE",
    "INTERNATIONAL_AFFAIRS",
    "INTERNATIONAL_TRADE_AND_DEVELOPMENT",
    "INVESTMENT_BANKING",
    "INVESTMENT_MANAGEMENT",
    "JUDICIARY",
    "LAW_ENFORCEMENT",
    "LAW_PRACTICE",
    "LEGAL_SERVICES",
    "LEGISLATIVE_OFFICE",
    "LEISURE_TRAVEL_TOURISM",
    "LIBRARIES",
    "LOGISTICS_AND_SUPPLY_CHAIN",
    "LUXURY_GOODS_JEWELRY",
    "MACHINERY",
    "MANAGEMENT_CONSULTING",
    "MARITIME",
    "MARKET_RESEARCH",
    "MARKETING_AND_ADVERTISING",
    "MECHANICAL_OR_INDUSTRIAL_ENGINEERING",
    "MEDIA_PRODUCTION",
    "MEDICAL_DEVICES",
    "MEDICAL_PRACTICE",
    "MENTAL_HEALTH_CARE",
    "MILITARY",
    "MINING_METALS",
    "MOTION_PICTURES_AND_FILM",
    "MUSEUMS_AND_INSTITUTIONS",
    "MUSIC",
    "NANOTECHNOLOGY",
    "NEWSPAPERS",
    "NONPROFIT_ORGANIZATION_MANAGEMENT",
    "OIL_ENERGY",
    "ONLINE_MEDIA",
    "OUTSOURCING_OFFSHORING",
    "PACKAGE_FREIGHT_DELIVERY",
    "PACKAGING_AND_CONTAINERS",
    "PAPER_FOREST_PRODUCTS",
    "PERFORMING_ARTS",
    "PHARMACEUTICALS",
    "PHILANTHROPY",
    "PHOTOGRAPHY",
    "PLASTICS",
    "POLITICAL_ORGANIZATION",
    "PRIMARY_SECONDARY_EDUCATION",
    "PRINTING",
    "PROFESSIONAL_TRAINING_COACHING",
    "PROGRAM_DEVELOPMENT",
    "PUBLIC_POLICY",
    "PUBLIC_RELATIONS_AND_COMMUNICATIONS",
    "PUBLIC_SAFETY",
    "PUBLISHING",
    "RAILROAD_MANUFACTURE",
    "RANCHING",
    "REAL_ESTATE",
    "RECREATIONAL_FACILITIES_AND_SERVICES",
    "RELIGIOUS_INSTITUTIONS",
    "RENEWABLES_ENVIRONMENT",
    "RESEARCH",
    "RESTAURANTS",
    "RETAIL",
    "SECURITY_AND_INVESTIGATIONS",
    "SEMICONDUCTORS",
    "SHIPBUILDING",
    "SPORTING_GOODS",
    "SPORTS",
    "STAFFING_AND_RECRUITING",
    "SUPERMARKETS",
    "TELECOMMUNICATIONS",
    "TEXTILES",
    "THINK_TANKS",
    "TOBACCO",
    "TRANSLATION_AND_LOCALIZATION",
    "TRANSPORTATION_TRUCKING_RAILROAD",
    "UTILITIES",
    "VENTURE_CAPITAL_PRIVATE_EQUITY",
    "VETERINARY",
    "WAREHOUSING",
    "WHOLESALE",
    "WINE_AND_SPIRITS",
    "WIRELESS",
    "WRITING_AND_EDITING"
}

def normalize_industry(industry: str | None, test_mode: bool = False) -> str:
    """
    Normalize an industry string to match the approved format
    Args:
        industry: Industry string to normalize or None
        test_mode: Whether to use test subset of industries
    Returns:
        Normalized industry string or empty string for None/empty input
    Raises:
        ValueError: If industry value doesn't match V3 API format
    """
    if industry is None or industry.strip() == "":
        return ""
    
    # Convert to uppercase and normalize separators to underscores
    normalized = industry.upper().strip()
    normalized = normalized.replace("-", " ").replace("  ", " ")  # Convert hyphens to spaces and clean up double spaces
    normalized = normalized.replace(" ", "_")  # Convert spaces to underscores
    normalized = "_".join(filter(None, normalized.split("_")))  # Clean up multiple underscores

    # Validate format matches V3 API requirements (all uppercase with underscores)
    if not all(c.isupper() or c == '_' for c in normalized):
        raise ValueError(f"Industry must be uppercase with underscores (V3 API format). Got: {normalized}")
    
    # Handle special cases and common variations
    test_aliases = {
        "TECH": "TECHNOLOGY",
        "IT": "TECHNOLOGY",
        "IT_SERVICES": "TECHNOLOGY",
        "TECHNOLOGY": "TECHNOLOGY",  # Ensure TECHNOLOGY maps to itself
        "HEALTHCARE": "HEALTH_CARE",
        "FINANCE": "FINANCIAL_SERVICES",
        "BANKING_AND_FINANCE": "FINANCIAL_SERVICES",
        "ECOMMERCE": "E_COMMERCE"
    } if test_mode else {
        "MANUFACTURING": "INDUSTRIAL_AUTOMATION",
        "INDUSTRIAL_MANUFACTURING": "INDUSTRIAL_AUTOMATION",
        "IT_SERVICES": "INFORMATION_TECHNOLOGY_AND_SERVICES",
        "IT": "INFORMATION_TECHNOLOGY_AND_SERVICES",
        "TECH": "INFORMATION_TECHNOLOGY_AND_SERVICES",
        "TECHNOLOGY": "INFORMATION_TECHNOLOGY_AND_SERVICES",
        "SOFTWARE": "COMPUTER_SOFTWARE",
        "SOFTWARE_DEVELOPMENT": "COMPUTER_SOFTWARE",
        "REAL_ESTATE_COMMERCIAL": "COMMERCIAL_REAL_ESTATE",
        "HEALTHCARE": "HOSPITAL_HEALTH_CARE",
        "HEALTH_CARE": "HOSPITAL_HEALTH_CARE",
        "EDUCATION": "EDUCATION_MANAGEMENT",
        "CONSULTING": "MANAGEMENT_CONSULTING",
        "MARKETING": "MARKETING_AND_ADVERTISING",
        "ADVERTISING": "MARKETING_AND_ADVERTISING",
        "LEGAL": "LEGAL_SERVICES",
        "LAW": "LEGAL_SERVICES",
        "FINANCE": "FINANCIAL_SERVICES",
        "BANKING_AND_FINANCE": "FINANCIAL_SERVICES",
        "MANUFACTURING_INDUSTRIAL": "INDUSTRIAL_AUTOMATION",
        "INDUSTRIAL": "INDUSTRIAL_AUTOMATION",
        "MEDIA": "MEDIA_PRODUCTION",
        "ENTERTAINMENT_AND_MEDIA": "ENTERTAINMENT"
    }
    
    # Check aliases first
    if normalized in test_aliases:
        normalized = test_aliases[normalized]
    
    return normalized

def is_valid_industry(industry: str | None, test_mode: bool = False, allow_custom: bool = False) -> bool:
    """
    Check if an industry is in the approved list
    Args:
        industry: Industry string to check or None
        test_mode: Whether to use test subset of industries
        allow_custom: Whether to allow custom industry values
    Returns:
        True if industry is valid, False otherwise
    """
    if industry is None or industry.strip() == "":
        return False
        
    try:
        normalized = normalize_industry(industry, test_mode)
        if not normalized:
            return False
    except ValueError:
        return False

    # If custom industries are allowed, any properly formatted value is valid
    if allow_custom:
        return True
        
    valid_industries = TEST_INDUSTRIES if test_mode else APPROVED_INDUSTRIES
    return normalized in valid_industries
