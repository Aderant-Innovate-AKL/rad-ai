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

# Define app families to query
APP_FAMILIES = {
    "Expert Disbursements": "ExpertSuite\\Financials\\Expert Disbursements",
    "Billing": "ExpertSuite\\Billing",
    "Accounts Payable": "ExpertSuite\\Financials\\Accounts Payable",
    "Collections": "ExpertSuite\\Financials\\Collections",
    "Infrastructure": "ExpertSuite\\Infrastructure"
}

def fetch_and_export_test_cases(app_family_name, area_path):
    """Fetch test cases for a specific area path and export to CSV"""
    print(f"\n{'='*100}")
    print(f"Processing: {app_family_name}")
    print(f"Area Path: {area_path}")
    print(f"{'='*100}")
    
    # WIQL query for test cases in specific area
    wiql_query = {
        "query": f"""
            SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate], [System.Description], [Microsoft.VSTS.TCM.Steps]
            FROM WorkItems
            WHERE [System.TeamProject] = 'ExpertSuite'
              AND [System.WorkItemType] = 'Test Case'
              AND [System.AreaPath] UNDER '{area_path}'
            ORDER BY [System.Id] ASC
        """
    }
    
    # Make the WIQL query
    api_url = f"{TFS_URL}/{COLLECTION}/{PROJECT}/_apis/wit/wiql?api-version=4.1"
    
    try:
        response = requests.post(api_url, headers=headers, json=wiql_query, timeout=30)
    except requests.exceptions.Timeout:
        print(f"✗ Connection timeout - unable to reach TFS server")
        return 0
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Connection error: {str(e)[:100]}")
        return 0
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)[:100]}")
        return 0
    
    if response.status_code == 200:
        result = response.json()
        work_items = result.get("workItems", [])[:200]  # First 200 only
        
        if not work_items:
            print(f"⚠ No test cases found for {app_family_name}")
            return 0
        
        print(f"Found {len(work_items)} test cases...")
        
        # Get details
        ids = [str(wi["id"]) for wi in work_items]
        ids_param = ",".join(ids)
        
        details_url = f"{TFS_URL}/{COLLECTION}/{PROJECT}/_apis/wit/workitems?ids={ids_param}&fields=System.Id,System.Title,System.State,System.AreaPath,System.CreatedDate,System.Description,Microsoft.VSTS.TCM.Steps&api-version=4.1"
        
        try:
            details_response = requests.get(details_url, headers=headers, timeout=30)
        except requests.exceptions.Timeout:
            print(f"✗ Timeout getting test case details")
            return 0
        except Exception as e:
            print(f"✗ Error getting details: {str(e)[:100]}")
            return 0
        
        if details_response.status_code == 200:
            test_cases = details_response.json().get("value", [])
            
            # Create safe filename
            safe_filename = app_family_name.lower().replace(" ", "_")
            csv_file = f"test_cases_{safe_filename}.csv"
            
            # Write to CSV
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
            
            print(f"✓ Exported {len(test_cases)} test cases to {csv_file}")
            
            # Show sample
            if test_cases:
                print(f"\nFirst 3 entries:")
                print("-" * 100)
                for tc in test_cases[:3]:
                    fields = tc.get("fields", {})
                    description = strip_html(fields.get("System.Description", ""))
                    desc_preview = description[:50] + "..." if len(description) > 50 else description
                    title_preview = fields.get('System.Title', '')[:40] + "..." if len(fields.get('System.Title', '')) > 40 else fields.get('System.Title', '')
                    print(f"{fields.get('System.Id')} | {title_preview} | {desc_preview}")
            
            return len(test_cases)
        else:
            print(f"✗ Error getting details: {details_response.status_code}")
            return 0
    else:
        print(f"✗ Error querying test cases: {response.status_code}")
        if response.status_code == 401:
            print("  Authentication failed. Please check your PAT token.")
        return 0

# Main execution
print("\n" + "="*100)
print("TFS Test Case Extractor - Multiple App Families")
print("="*100)

total_test_cases = 0
successful_families = 0
failed_families = []

for app_family_name, area_path in APP_FAMILIES.items():
    count = fetch_and_export_test_cases(app_family_name, area_path)
    if count > 0:
        successful_families += 1
        total_test_cases += count
    else:
        failed_families.append(app_family_name)

# Summary
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"App families processed: {successful_families}/{len(APP_FAMILIES)}")
print(f"Total test cases exported: {total_test_cases}")
print(f"\nCSV files generated:")
for app_family_name in APP_FAMILIES.keys():
    safe_filename = app_family_name.lower().replace(" ", "_")
    print(f"  - test_cases_{safe_filename}.csv")

if failed_families:
    print(f"\n⚠ Failed to process: {', '.join(failed_families)}")
    print("\nPossible reasons:")
    print("  - Network connectivity issues (VPN required?)")
    print("  - Area path doesn't exist in TFS")
    print("  - No test cases in that area")
    print("  - PAT token expired or insufficient permissions")
print("="*100)


