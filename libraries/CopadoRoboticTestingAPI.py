import requests
import json
from typing import Optional

class CopadoRoboticTestingAPI:
    """
    A client class for interacting with Copado Robotic Testing API
    to retrieve project and job information.
    """
    
    def __init__(self, personal_access_token: str, project_id: str, job_id: str):
        """
        Initialize the API client with authentication and project details.
        
        Args:
            personal_access_token (str): Personal access token for authentication
            project_id (str): The project ID
            job_id (str): The job ID
        """
        self.personal_access_token = personal_access_token
        self.project_id = project_id
        self.job_id = job_id
        self.base_url = "https://api.robotic.copado.com/pace/v4"
    
    def get_latest_commit_hash(self) -> Optional[str]:
        """
        Retrieve the latest commit hash from the project's main branch.
        
        Returns:
            str: The latest commit hash, or None if the request fails
            
        Raises:
            requests.RequestException: If the API request fails
            KeyError: If the expected JSON structure is not found
            ValueError: If the response cannot be parsed as JSON
        """
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files"
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token
        }
        
        # Set up query parameters
        params = {
            "branch": "main",
            "sharedCredentials": "true"
        }
        
        try:
            # Make the GET request
            response = requests.get(endpoint, headers=headers, params=params)
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Extract the commit hash from the branch object
            commit_hash = data["branch"]["commitHash"]
            
            return commit_hash
            
        except requests.RequestException as e:
            print(f"API request failed: {e}")
            raise
        except KeyError as e:
            print(f"Expected key not found in response: {e}")
            raise
        except ValueError as e:
            print(f"Failed to parse JSON response: {e}")
            raise
    
    def get_branch_info(self) -> Optional[dict]:
        """
        Retrieve the complete branch information including name and commit hash.
        
        Returns:
            dict: Branch information with 'name' and 'commitHash', or None if failed
        """
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files"
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token
        }
        
        # Set up query parameters
        params = {
            "branch": "main",
            "sharedCredentials": "true"
        }
        
        try:
            # Make the GET request
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Return the complete branch object
            return data["branch"]
            
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"Failed to retrieve branch info: {e}")
            return None
