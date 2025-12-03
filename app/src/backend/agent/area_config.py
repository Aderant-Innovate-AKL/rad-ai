"""
Configuration for test case area detection and CSV file mapping.

This module contains mappings between app families, their keywords,
CSV files, and area path patterns for intelligent test case retrieval.
"""

import os
from pathlib import Path

# Base path to CSV files (relative to backend directory)
CSV_BASE_PATH = Path(__file__).parent.parent.parent.parent.parent

# Mapping of app families to their CSV filenames
CSV_FILE_MAPPING = {
    "Expert Disbursements": "test_cases_expert_disbursements.csv",
    "Billing": "test_cases_billing.csv",
    "Accounts Payable": "test_cases_accounts_payable.csv",
    "Collections": "test_cases_collections.csv",
    "Infrastructure": "test_cases_infrastructure.csv"
}

# Get absolute paths to CSV files
CSV_FILE_PATHS = {
    area: str(CSV_BASE_PATH / filename)
    for area, filename in CSV_FILE_MAPPING.items()
}

# Keywords associated with each app family for detection
AREA_KEYWORDS = {
    "Expert Disbursements": [
        "disbursement", "disb", "disbursements", "expense", 
        "reimbursement", "posting", "split", "merge", 
        "session", "cost code", "anticipated", "release",
        "hard disbursement", "soft disbursement", "WIP"
    ],
    "Billing": [
        "billing", "bill", "prebill", "invoice", "WIP", 
        "prebilling", "markup", "realization", "timekeeper",
        "rate", "narrative", "proforma", "writeoff", "write-off",
        "billing worksheet", "final bill"
    ],
    "Accounts Payable": [
        "accounts payable", "AP", "vendor", "payment", 
        "invoice entry", "payable", "check", "voucher",
        "vendor invoice", "AP invoice", "payment processing"
    ],
    "Collections": [
        "collections", "collector", "payor", "payment plan",
        "AR", "receivable", "activity", "expected payment",
        "aging", "outstanding", "collection activity",
        "payor workspace"
    ],
    "Infrastructure": [
        "infrastructure", "security", "expansion code", 
        "smartform", "customization", "deployment", 
        "upgrade", "toolkit", "workflow", "UX toolkit",
        "permissions", "user management", "configuration"
    ]
}

# Area path patterns for each app family (regex-friendly)
AREA_PATH_PATTERNS = {
    "Expert Disbursements": r"ExpertSuite\\Financials\\Expert Disbursements",
    "Billing": r"ExpertSuite\\Billing",
    "Accounts Payable": r"ExpertSuite\\Financials\\Accounts Payable",
    "Collections": r"ExpertSuite\\Financials\\Collections",
    "Infrastructure": r"ExpertSuite\\Infrastructure"
}

# Detailed descriptions of each app family for Claude
AREA_DESCRIPTIONS = {
    "Expert Disbursements": """
        Expert Disbursements module handles expense tracking and reimbursement processing.
        Key features include:
        - Creating, editing, and posting disbursements
        - Split and merge operations for disbursements
        - Session management and release processes
        - Currency handling and cost code management
        - Hard and soft disbursement categorization
    """,
    "Billing": """
        Billing module manages the invoicing and billing workflow.
        Key features include:
        - Prebilling and billing markup workflows
        - WIP (Work in Progress) management
        - Invoice generation and proforma bills
        - Timekeeper rate management
        - Realization and writeoff processes
    """,
    "Accounts Payable": """
        Accounts Payable module handles vendor invoice processing and payments.
        Key features include:
        - Vendor invoice entry and editing
        - Payment processing and check generation
        - Voucher management
        - AP invoice workflow and approval
    """,
    "Collections": """
        Collections module manages account receivables and collection activities.
        Key features include:
        - Collector workspace and activities
        - Payor management and payment plans
        - Expected payment tracking
        - Aging analysis and outstanding balances
    """,
    "Infrastructure": """
        Infrastructure encompasses system-level features and customizations.
        Key features include:
        - Security and user management
        - Expansion codes and SmartForms
        - UX Toolkit and workflow customization
        - System configuration and deployment
        - Permissions and access control
    """
}

# Priority order for area detection (some areas are more specific than others)
AREA_PRIORITY = [
    "Expert Disbursements",
    "Accounts Payable",
    "Collections",
    "Billing",
    "Infrastructure"  # Most generic, check last
]


def get_csv_path(area_name: str) -> str:
    """
    Get the absolute path to a CSV file for a given area.
    
    Args:
        area_name: Name of the app family/area
        
    Returns:
        Absolute path to the CSV file
        
    Raises:
        KeyError: If area name is not found
    """
    if area_name not in CSV_FILE_PATHS:
        raise KeyError(f"Unknown area: {area_name}. Available areas: {list(CSV_FILE_PATHS.keys())}")
    
    path = CSV_FILE_PATHS[area_name]
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV file not found: {path}")
    
    return path


def get_all_csv_paths() -> dict:
    """
    Get all CSV file paths.
    
    Returns:
        Dictionary mapping area names to their CSV file paths
    """
    return CSV_FILE_PATHS.copy()


def get_area_keywords(area_name: str) -> list:
    """
    Get keywords associated with an area.
    
    Args:
        area_name: Name of the app family/area
        
    Returns:
        List of keywords
    """
    return AREA_KEYWORDS.get(area_name, [])


def get_all_areas() -> list:
    """
    Get list of all available areas.
    
    Returns:
        List of area names
    """
    return list(CSV_FILE_MAPPING.keys())
