import requests
import base64
import csv

# Configuration
TFS_URL = "https://tfs.aderant.com/tfs"
COLLECTION = "ADERANT"
PROJECT = "ExpertSuite"
PAT = "szafzrwqrh7bqeqfmlf2vrkirvq3cv7xhvocrxf2chh7laxnqm4q"

# Auth header
auth_header = base64.b64encode(f":{PAT}".encode()).decode()
headers = {
    "Authorization": f"Basic {auth_header}",
    "Content-Type": "application/json"
}

# WIQL query for test cases in specific area
wiql_query = {
    "query": """
        SELECT [System.Id], [System.Title], [System.State], [System.CreatedDate]
        FROM WorkItems
        WHERE [System.TeamProject] = 'ExpertSuite'
          AND [System.WorkItemType] = 'Test Case'
          AND [System.AreaPath] UNDER 'ExpertSuite\\Financials\\Expert Disbursements'
        ORDER BY [System.Id] ASC
    """
}

# Make the WIQL query
api_url = f"{TFS_URL}/{COLLECTION}/{PROJECT}/_apis/wit/wiql?api-version=4.1"
response = requests.post(api_url, headers=headers, json=wiql_query)

if response.status_code == 200:
    result = response.json()
    work_items = result.get("workItems", [])[:100]  # First 100 only
    print(f"Fetching first {len(work_items)} test cases...")
    
    if work_items:
        # Get details for first 100
        ids = [str(wi["id"]) for wi in work_items]
        ids_param = ",".join(ids)
        
        details_url = f"{TFS_URL}/{COLLECTION}/{PROJECT}/_apis/wit/workitems?ids={ids_param}&fields=System.Id,System.Title,System.State,System.AreaPath,System.CreatedDate&api-version=4.1"
        details_response = requests.get(details_url, headers=headers)
        
        if details_response.status_code == 200:
            test_cases = details_response.json().get("value", [])
            
            # Write to CSV
            csv_file = "test_cases_expert_disbursements.csv"
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header
                writer.writerow(["ID", "Title", "State", "Area", "Created Date"])
                
                # Data
                for tc in test_cases:
                    fields = tc.get("fields", {})
                    writer.writerow([
                        fields.get("System.Id", ""),
                        fields.get("System.Title", ""),
                        fields.get("System.State", ""),
                        fields.get("System.AreaPath", ""),
                        fields.get("System.CreatedDate", "")
                    ])
            
            print(f"\n✓ Exported {len(test_cases)} test cases to {csv_file}")
            print(f"\nFirst 10 entries:")
            print("-" * 100)
            for tc in test_cases[:10]:
                fields = tc.get("fields", {})
                print(f"{fields.get('System.Id')} | {fields.get('System.Title')[:60]}...")
        else:
            print(f"Error getting details: {details_response.status_code}")
else:
    print(f"Error: {response.status_code}")


