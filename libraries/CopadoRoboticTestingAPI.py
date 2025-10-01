import requests
import json
import os
import base64
import mimetypes
from typing import Optional, Dict, Any, List

class CopadoRoboticTestingAPI:
    """
    A client class for interacting with Copado Robotic Testing API
    to retrieve project and job information and upload files (text and binary).
    """
    
    # Common binary file extensions
    BINARY_EXTENSIONS = {
        '.xlsx', '.xls', '.xlsm', '.xlsb',  # Excel files
        '.docx', '.doc', '.docm',           # Word files
        '.pptx', '.ppt', '.pptm',           # PowerPoint files
        '.pdf',                             # PDF files
        '.zip', '.rar', '.7z',              # Archive files
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',  # Image files
        '.mp3', '.wav', '.mp4', '.avi',     # Media files
        '.exe', '.dll', '.so',              # Executable files
        '.jar', '.war',                     # Java files
        '.bin', '.dat'                      # Generic binary files
    }
    
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
        self._cached_xsrf_token = None
    
    def _get_xsrf_token(self) -> Optional[str]:
        """
        Retrieve the XSRF token from the GET request headers.
        This token is required for POST requests.
        
        Returns:
            str: The XSRF token, or None if not found
            
        Raises:
            requests.RequestException: If the API request fails
        """
        # Check if we have a cached token
        if self._cached_xsrf_token:
            return self._cached_xsrf_token
            
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
            
            # Extract XSRF token from response headers
            xsrf_token = response.headers.get('x-xsrf-token')
            if xsrf_token:
                self._cached_xsrf_token = xsrf_token
                print(f"Retrieved XSRF token: {xsrf_token[:10]}..." if len(xsrf_token) > 10 else f"Retrieved XSRF token: {xsrf_token}")
            else:
                print("Warning: No x-xsrf-token found in response headers")
                # Print available headers for debugging
                print("Available headers:", list(response.headers.keys()))
            
            return xsrf_token
            
        except requests.RequestException as e:
            print(f"Failed to retrieve XSRF token: {e}")
            raise

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
            
            # Cache XSRF token if available
            xsrf_token = response.headers.get('x-xsrf-token')
            if xsrf_token:
                self._cached_xsrf_token = xsrf_token
            
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
            
            # Cache XSRF token if available
            xsrf_token = response.headers.get('x-xsrf-token')
            if xsrf_token:
                self._cached_xsrf_token = xsrf_token
            
            # Parse the JSON response
            data = response.json()
            
            # Return the complete branch object
            return data["branch"]
            
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"Failed to retrieve branch info: {e}")
            return None

    def _is_binary_file(self, file_path: str, force_binary: Optional[bool] = None) -> bool:
        """
        Determine if a file should be treated as binary.
        
        Args:
            file_path (str): Path to the file
            force_binary (bool, optional): Force binary/text mode regardless of detection
            
        Returns:
            bool: True if file should be treated as binary
        """
        if force_binary is not None:
            return force_binary
            
        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        if ext in self.BINARY_EXTENSIONS:
            return True
            
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if not mime_type.startswith('text/') and mime_type != 'application/json':
                return True
                
        # Try to read a small portion as text to detect binary content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read first 1KB as text
            return False
        except (UnicodeDecodeError, UnicodeError):
            return True

    def _read_file_content(self, file_path: str, is_binary: bool) -> tuple[str, str]:
        """
        Read file content and return content and encoding type.
        
        Args:
            file_path (str): Path to the file
            is_binary (bool): Whether to treat file as binary
            
        Returns:
            tuple: (file_content, encoding_type)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If text file can't be decoded as UTF-8
            IOError: If file can't be read
        """
        if is_binary:
            # Read as binary and base64 encode
            with open(file_path, 'rb') as file:
                binary_content = file.read()
                encoded_content = base64.b64encode(binary_content).decode('ascii')
                return encoded_content, "base64"
        else:
            # Read as text
            with open(file_path, 'r', encoding='utf-8') as file:
                text_content = file.read()
                return text_content, "utf-8"

    def save_file(self, 
                  local_file_path: str, 
                  author_name: str, 
                  author_email: str, 
                  commit_message: str,
                  repository_path: Optional[str] = None,
                  parent_commit_hash: Optional[str] = None,
                  force_binary: Optional[bool] = None) -> bool:
        """
        Upload a file to the Copado Robotic Testing repository.
        
        Args:
            local_file_path (str): Local file system path to the file to upload
            author_name (str): Name of the commit author
            author_email (str): Email of the commit author
            commit_message (str): Commit message
            repository_path (str, optional): Path where file should be stored in repository. 
                                           If None, uses just the filename from local_file_path
            parent_commit_hash (str, optional): Parent commit hash. If None, will fetch latest
            force_binary (bool, optional): Force binary (True) or text (False) mode. If None, auto-detect
            
        Returns:
            bool: True if upload was successful, False otherwise
            
        Raises:
            FileNotFoundError: If the specified file doesn't exist
            requests.RequestException: If the API request fails
            UnicodeDecodeError: If text file cannot be decoded as UTF-8
            IOError: If file cannot be read
        """
        # Check if file exists
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"File not found: {local_file_path}")
        
        # Determine repository path
        if repository_path is None:
            repository_path = os.path.basename(local_file_path)
        
        # Get parent commit hash if not provided
        if parent_commit_hash is None:
            parent_commit_hash = self.get_latest_commit_hash()
            if parent_commit_hash is None:
                print("Failed to retrieve latest commit hash")
                return False
        
        # Determine if file is binary and read content
        is_binary = self._is_binary_file(local_file_path, force_binary)
        file_content, encoding_type = self._read_file_content(local_file_path, is_binary)
        
        print(f"Uploading {'binary' if is_binary else 'text'} file:")
        print(f"  Local path: {local_file_path}")
        print(f"  Repository path: {repository_path}")
        print(f"  Encoding: {encoding_type}")
        
        return self._upload_file_content(
            repository_path, file_content, encoding_type, 
            author_name, author_email, commit_message, parent_commit_hash
        )

    def save_file_with_custom_path(self, 
                                   file_path: str, 
                                   repository_path: str,
                                   author_name: str, 
                                   author_email: str, 
                                   commit_message: str,
                                   parent_commit_hash: Optional[str] = None,
                                   force_binary: Optional[bool] = None) -> bool:
        """
        Upload a file to the Copado Robotic Testing repository with a custom repository path.
        
        DEPRECATED: Use save_file() with repository_path parameter instead.
        
        Args:
            file_path (str): Path to the local file to upload
            repository_path (str): Path where the file should be stored in the repository
            author_name (str): Name of the commit author
            author_email (str): Email of the commit author
            commit_message (str): Commit message
            parent_commit_hash (str, optional): Parent commit hash. If None, will fetch latest
            force_binary (bool, optional): Force binary (True) or text (False) mode. If None, auto-detect
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        print("Warning: save_file_with_custom_path() is deprecated. Use save_file() with repository_path parameter instead.")
        
        return self.save_file(
            local_file_path=file_path,
            repository_path=repository_path,
            author_name=author_name,
            author_email=author_email,
            commit_message=commit_message,
            parent_commit_hash=parent_commit_hash,
            force_binary=force_binary
        )

    def _upload_file_content(self, 
                           repository_path: str,
                           file_content: str,
                           encoding_type: str,
                           author_name: str, 
                           author_email: str, 
                           commit_message: str,
                           parent_commit_hash: str) -> bool:
        """
        Internal method to upload file content to the API.
        
        Args:
            repository_path (str): Path in the repository
            file_content (str): File content (text or base64 encoded)
            encoding_type (str): Either "utf-8" or "base64"
            author_name (str): Commit author name
            author_email (str): Commit author email
            commit_message (str): Commit message
            parent_commit_hash (str): Parent commit hash
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Get XSRF token - required for POST requests
        xsrf_token = self._get_xsrf_token()
        if not xsrf_token:
            print("Failed to retrieve XSRF token - POST request may fail")
            return False
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
        # Set up headers including XSRF token
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token,
            "x-xsrf-token": xsrf_token
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
                    "encoding": encoding_type,
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
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            raise

    def save_multiple_files(self, 
                           file_operations: List[Dict[str, str]], 
                           author_name: str, 
                           author_email: str, 
                           commit_message: str,
                           parent_commit_hash: Optional[str] = None) -> bool:
        """
        Upload multiple files in a single commit.
        
        Args:
            file_operations (List[Dict]): List of file operations with keys:
                - 'local_path': Local file system path
                - 'repo_path': Repository path (optional, uses filename if not provided)
                - 'force_binary': Force binary mode (optional)
            author_name (str): Name of the commit author
            author_email (str): Email of the commit author
            commit_message (str): Commit message
            parent_commit_hash (str, optional): Parent commit hash. If None, will fetch latest
            
        Returns:
            bool: True if upload was successful, False otherwise
        """
        # Get parent commit hash if not provided
        if parent_commit_hash is None:
            parent_commit_hash = self.get_latest_commit_hash()
            if parent_commit_hash is None:
                print("Failed to retrieve latest commit hash")
                return False
        
        # Get XSRF token - required for POST requests
        xsrf_token = self._get_xsrf_token()
        if not xsrf_token:
            print("Failed to retrieve XSRF token - POST request may fail")
            return False
        
        operations = []
        
        for file_op in file_operations:
            local_path = file_op['local_path']
            repo_path = file_op.get('repo_path', os.path.basename(local_path))
            force_binary = file_op.get('force_binary')
            
            # Check if file exists
            if not os.path.exists(local_path):
                print(f"Warning: File not found: {local_path}")
                continue
            
            # Determine if file is binary and read content
            is_binary = self._is_binary_file(local_path, force_binary)
            file_content, encoding_type = self._read_file_content(local_path, is_binary)
            
            operations.append({
                "encoding": encoding_type,
                "op": "replace",
                "path": repo_path,
                "value": file_content
            })
            
            print(f"Prepared {'binary' if is_binary else 'text'} file:")
            print(f"  Local: {local_path} -> Repository: {repo_path} (encoding: {encoding_type})")
        
        if not operations:
            print("No valid files to upload")
            return False
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
        # Set up headers including XSRF token
        headers = {
            "Content-Type": "application/json",
            "X-Authorization": self.personal_access_token,
            "x-xsrf-token": xsrf_token
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
            "operations": operations,
            "parentCommitHash": parent_commit_hash
        }
        
        try:
            # Make the POST request
            response = requests.post(endpoint, headers=headers, params=params, json=payload)
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            print(f"Successfully uploaded {len(operations)} files")
            return True
            
        except requests.RequestException as e:
            print(f"Failed to upload files: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            raise

    def clear_xsrf_cache(self):
        """
        Clear the cached XSRF token. Useful if the token expires or becomes invalid.
        """
        self._cached_xsrf_token = None
        print("XSRF token cache cleared")
