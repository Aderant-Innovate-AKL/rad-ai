import os
import requests
import base64
import csv
import html
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class HTMLStripper(HTMLParser):
    """Helper class to strip HTML tags from text"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_text(self):
        return ''.join(self.text)

def strip_html(html_string):
    """Remove HTML tags from string"""
    if not html_string:
        return ""
    stripper = HTMLStripper()
    stripper.feed(html_string)
    return stripper.get_text().strip()

def parse_test_steps(steps_xml):
    """Parse test case steps from XML format"""
    if not steps_xml:
        return ""
    
    try:
        # Parse the XML
        root = ET.fromstring(steps_xml)
        steps_list = []
        
        # Find all step elements
        for idx, step in enumerate(root.findall('.//step'), 1):
            # Get action and expected result
            action_elem = step.find('.//parameterizedString[@isformatted="true"]')
            expected_elem = step.find('.//parameterizedString[@isformatted="true"][2]')
            
            # Handle both new and old XML structures
            if action_elem is None:
                action_elem = step.find('./parameterizedString')
            
            action = strip_html(action_elem.text) if action_elem is not None and action_elem.text else ""
            expected = ""
            
            # Try to get expected result
            if expected_elem is not None and expected_elem.text:
                expected = strip_html(expected_elem.text)
            else:
                # Alternative structure
                description_elems = step.findall('.//parameterizedString')
                if len(description_elems) > 1:
                    expected = strip_html(description_elems[1].text) if description_elems[1].text else ""
            
            # Format the step
            if action:
                step_text = f"Step {idx}: {action}"
                if expected:
                    step_text += f" | Expected: {expected}"
                steps_list.append(step_text)
        
        return " || ".join(steps_list)
    except Exception as e:
        return f"[Error parsing steps: {str(e)}]"

# Configuration - loaded from .env file
TFS_BASE_URL = os.getenv("TFS_BASE_URL", "")
COLLECTION = os.getenv("TFS_COLLECTION", "")
PROJECT = os.getenv("TFS_PROJECT", "")
PAT = os.getenv("TFS_PAT", "")

# Validate required environment variables
if not all([TFS_BASE_URL, COLLECTION, PROJECT, PAT]):
    missing = []
    if not TFS_BASE_URL: missing.append("TFS_BASE_URL")
    if not COLLECTION: missing.append("TFS_COLLECTION")
    if not PROJECT: missing.append("TFS_PROJECT")
    if not PAT: missing.append("TFS_PAT")
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    print("Please add them to your .env file")
    exit(1)

# Auth header
auth_header = base64.b64encode(f":{PAT}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/json"
}

# WIQL query for test cases in specific area
wiql_query = {
    "query": """
        SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate], [System.Description], [Microsoft.VSTS.TCM.Steps]
        FROM WorkItems
        WHERE [System.TeamProject] = 'ExpertSuite'
          AND [System.WorkItemType] = 'Test Case'
          AND [System.AreaPath] UNDER 'ExpertSuite\\Financials\\Expert Disbursements'
        ORDER BY [System.Id] ASC
    """
}

# Make the WIQL query
api_url = f"{TFS_BASE_URL}/{COLLECTION}/{PROJECT}/_apis/wit/wiql?api-version=4.1"
response = requests.post(api_url, headers=headers, json=wiql_query)

if response.status_code == 200:
    result = response.json()
    work_items = result.get("workItems", [])[:200]  # First 200 only
    print(f"Fetching first {len(work_items)} test cases...")
    
    if work_items:
        # Get details for first 100
        ids = [str(wi["id"]) for wi in work_items]
        ids_param = ",".join(ids)
        
        details_url = f"{TFS_BASE_URL}/{COLLECTION}/{PROJECT}/_apis/wit/workitems?ids={ids_param}&fields=System.Id,System.Title,System.State,System.AreaPath,System.CreatedDate,System.Description,Microsoft.VSTS.TCM.Steps&api-version=4.1"
        details_response = requests.get(details_url, headers=headers)
        
        if details_response.status_code == 200:
            test_cases = details_response.json().get("value", [])
            
            # Write to CSV
            csv_file = "test_cases_with_descriptions_expert_disbursements.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header
                writer.writerow(["ID", "Title", "State", "Area", "Created Date", "Description", "Steps"])
                
                # Data
                for tc in test_cases:
                    fields = tc.get("fields", {})
                    
                    # Get and clean description
                    description = strip_html(fields.get("System.Description", ""))
                    
                    # Parse test steps
                    steps_xml = fields.get("Microsoft.VSTS.TCM.Steps", "")
                    steps = parse_test_steps(steps_xml)
                    
                    writer.writerow([
                        fields.get("System.Id", ""),
                        fields.get("System.Title", ""),
                        fields.get("System.State", ""),
                        fields.get("System.AreaPath", ""),
                        fields.get("System.CreatedDate", ""),
                        description,
                        steps
                    ])
            
            print(f"\n✓ Exported {len(test_cases)} test cases to {csv_file}")
            print(f"\nFirst 5 entries with descriptions:")
            print("-" * 100)
            for tc in test_cases[:5]:
                fields = tc.get("fields", {})
                description = strip_html(fields.get("System.Description", ""))
                desc_preview = description[:50] + "..." if len(description) > 50 else description
                print(f"{fields.get('System.Id')} | {fields.get('System.Title')[:40]} | {desc_preview}")
        else:
            print(f"Error getting details: {details_response.status_code}")
else:
    print(f"Error: {response.status_code}")


