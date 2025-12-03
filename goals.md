# Overall Goal
To surface and link related TFS test cases matching/related to changes made in a PR using AI LLM agent and MCP server to assist in manual testing.
 
## Steps to achieve goal:
- Use TFS API to extract test cases related the changed files in the given PR, filtering by area/module.
- Load the extracted test cases into MCP server.
- Looks at bug description (repro steps), PR description and file changes, and use AI LLM Agent to match against the data from MCP server.
- Give a list of related test cases and ask for a user review. Once reviewed, it can link test cases (use test case id to find TFS item) to the bug.
 
## Problem we are solving:
Due to test cases being widely spread out in many different folders. It is difficult for QAs to find affected test cases to a specific bug report which leads to missing out on testing edge cases and unusual scenarios.
 
Test cases are not regularly updated and maintained to stay up to date with the feature and UI changes.
 
Furthermore, duplicate test cases exist within the test suite and there is no common place to find them all.
 
## The solution:
With this solution, we will be able to surface all the test cases related to the current bug in question, while suggesting updates and identify duplicate test cases allowing QAs to review them and accept or reject any changes.