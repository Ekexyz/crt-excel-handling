import requests
import json
import os
from typing import Optional, Dict, Any

class CopadoRoboticTestingAPI:
    """
    A client class for interacting with Copado Robotic Testing API
    to retrieve project and job information and upload files.
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

    def save_file(self, 
                  file_path: str, 
                  author_name: str, 
                  author_email: str, 
                  commit_message: str,
                  parent_commit_hash: Optional[str] = None) -> bool:
        """
        Upload a file to the Copado Robotic Testing repository.
        
        Args:
            file_path (str): Path to the file to upload
            author_name (str): Name of the commit author
            author_email (str): Email of the commit author
            commit_message (str): Commit message
            parent_commit_hash (str, optional): Parent commit hash. If None, will fetch latest
            
        Returns:
            bool: True if upload was successful, False otherwise
            
        Raises:
            FileNotFoundError: If the specified file doesn't exist
            requests.RequestException: If the API request fails
            UnicodeDecodeError: If the file cannot be decoded as UTF-8
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get parent commit hash if not provided
        if parent_commit_hash is None:
            parent_commit_hash = self.get_latest_commit_hash()
            if parent_commit_hash is None:
                print("Failed to retrieve latest commit hash")
                return False
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except UnicodeDecodeError as e:
            print(f"Failed to read file as UTF-8: {e}")
            raise
        
        # Extract filename from path for the operation
        filename = os.path.basename(file_path)
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token
        }
        
        # Set up query parameters
        params = {
            "branch": "main"
        }
        
        # Construct the payload
        payload = {
            "author": {
                "name": author_name,
                "email": author_email
            },
            "commitMessage": commit_message,
            "operations": [
                {
                    "encoding": "utf-8",
                    "op": "replace",
                    "path": filename,
                    "value": file_content
                }
            ],
            "parentCommitHash": parent_commit_hash
        }
        
        try:
            # Make the POST request
            response = requests.post(endpoint, headers=headers, params=params, json=payload)
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            print(f"File '{filename}' uploaded successfully")
            return True
            
        except requests.RequestException as e:
            print(f"Failed to upload file: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def save_file_with_custom_path(self, 
                                   file_path: str, 
                                   repository_path: str,
                                   author_name: str, 
                                   author_email: str, 
                                   commit_message: str,
                                   parent_commit_hash: Optional[str] = None) -> bool:
        """
        Upload a file to the Copado Robotic Testing repository with a custom repository path.
        
        Args:
            file_path (str): Path to the local file to upload
            repository_path (str): Path where the file should be stored in the repository
            author_name (str): Name of the commit author
            author_email (str): Email of the commit author
            commit_message (str): Commit message
            parent_commit_hash (str, optional): Parent commit hash. If None, will fetch latest
            
        Returns:
            bool: True if upload was successful, False otherwise
            
        Raises:
            FileNotFoundError: If the specified file doesn't exist
            requests.RequestException: If the API request fails
            UnicodeDecodeError: If the file cannot be decoded as UTF-8
        """
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get parent commit hash if not provided
        if parent_commit_hash is None:
            parent_commit_hash = self.get_latest_commit_hash()
            if parent_commit_hash is None:
                print("Failed to retrieve latest commit hash")
                return False
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()
        except UnicodeDecodeError as e:
            print(f"Failed to read file as UTF-8: {e}")
            raise
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
        # Set up headers
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token
        }
        
        # Set up query parameters
        params = {
            "branch": "main"
        }
        
        # Construct the payload
        payload = {
            "author": {
                "name": author_name,
                "email": author_email
            },
            "commitMessage": commit_message,
            "operations": [
                {
                    "encoding": "utf-8",
                    "op": "replace",
                    "path": repository_path,
                    "value": file_content
                }
            ],
            "parentCommitHash": parent_commit_hash
        }
        
        try:
            # Make the POST request
            response = requests.post(endpoint, headers=headers, params=params, json=payload)
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            print(f"File uploaded successfully to '{repository_path}'")
            return True
            
        except requests.RequestException as e:
            print(f"Failed to upload file: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
