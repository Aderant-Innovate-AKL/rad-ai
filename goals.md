# Overall Goal
To surface and link related TFS test cases that match/relate to changes made in the given PR and associated bug description using AI LLM agent and MCP server to assist with manual testing.
 
## Steps to achieve goal:
- Use TFS API to extract test cases related to the module changed in the given PR, filtered by area/module and cache in csv file.
- Load the extracted test cases into MCP server.
- Looks at bug description (repro steps), PR description, AI summary of the PR and files changed, and use AI LLM Agent to match against the data from MCP server.
- Gives a list of related test cases and asks for user review. Once reviewed, it can link test cases (use test case id to find TFS item) to the bug.
 
## Problem we are solving:
Due to test cases being widely scattered in many different folders. It is difficult for QAs to find affected test cases for a specific bug which leads to missing out on testing edge cases and unusual scenarios.
 
Test cases are not regularly updated and maintained to stay up to date with the feature and UI changes.
 
Furthermore, duplicate test cases exist within the test suite and there is no common place to find them all.
 
## The solution:

With this solution, we will be able to surface all relevant test cases for the current bug and PR.
 Suggest updates where needed.
 Identify duplicates for cleanup.
 This empowers QAs to make informed decisions, reduce manual effort, and improve coverage.
