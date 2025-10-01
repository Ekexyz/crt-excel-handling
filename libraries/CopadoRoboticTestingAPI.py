import requests
import json
import os
import base64
import mimetypes
import re
from typing import Optional, Dict, Any, List
from robot.api import logger

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
        self._cached_headers = None
    
    def _parse_cookies_from_set_cookie_headers(self, response: requests.Response) -> Dict[str, str]:
        """
        Parse cookies from Set-Cookie headers.
        
        Args:
            response: The HTTP response object
            
        Returns:
            dict: Dictionary mapping cookie names to values
        """
        cookies = {}
        
        # Get all Set-Cookie headers (there might be multiple)
        set_cookie_headers = response.headers.get_list('Set-Cookie') if hasattr(response.headers, 'get_list') else [response.headers.get('Set-Cookie')]
        
        # Handle the case where get_list doesn't exist or returns None
        if not set_cookie_headers or set_cookie_headers == [None]:
            # Try to get raw headers if available
            if hasattr(response, 'raw') and hasattr(response.raw, '_original_response'):
                set_cookie_headers = response.raw._original_response.msg.get_all('Set-Cookie') or []
            else:
                set_cookie_headers = []
        
        for header_value in set_cookie_headers:
            if header_value:
                # Parse each cookie from the header
                # Format: "name=value; attribute=value; attribute"
                for cookie_part in header_value.split(','):
                    cookie_part = cookie_part.strip()
                    if '=' in cookie_part:
                        # Split only on the first '=' to handle values that might contain '='
                        name_value = cookie_part.split(';')[0]  # Get just the name=value part
                        if '=' in name_value:
                            name, value = name_value.split('=', 1)
                            cookies[name.strip()] = value.strip()
        
        return cookies
    
    def _get_robotic_headers(self) -> Optional[Dict[str, str]]:
        """
        Get the headers needed for API requests, including CSRF cookie and XSRF token.
        This follows the same pattern as the TypeScript implementation.
        
        Returns:
            dict: Headers dictionary with Cookie and X-XSRF-TOKEN, or None if failed
        """
        # Check if we have cached headers
        if self._cached_headers:
            return self._cached_headers
            
        # Use the robots endpoint like in the TypeScript code
        robots_url = f"{self.base_url}/projects/{self.project_id}/robots"
        
        # Set up initial headers
        headers = {
            "Cookie": "",  # Start with empty cookie
            "X-Authorization": self.personal_access_token
        }
        
        try:
            # Make the GET request to fetch CSRF token
            response = requests.get(robots_url, headers=headers)
            response.raise_for_status()
            
            # Parse cookies from Set-Cookie headers
            cookies = self._parse_cookies_from_set_cookie_headers(response)
            
            logger.console(f"Parsed cookies: {list(cookies.keys())}")
            
            # Get the CSRF and XSRF cookies
            csrf_cookie = cookies.get('_pace-csrf')
            xsrf_token = cookies.get('PACE-XSRF-TOKEN')
            
            if not xsrf_token:
                logger.console("Warning: PACE-XSRF-TOKEN not found in cookies")
                logger.console(f"Available cookies: {cookies}")
                return None
            
            # Build the cookie header
            cookie_parts = []
            if csrf_cookie:
                cookie_parts.append(f"_pace-csrf={csrf_cookie}")
            cookie_parts.append(f"PACE-XSRF-TOKEN={xsrf_token}")
            
            # Create the headers for subsequent requests
            robotic_headers = {
                "Content-Type": "application/json",
                "X-Authorization": self.personal_access_token,
                "Cookie": "; ".join(cookie_parts),
                "X-XSRF-TOKEN": xsrf_token
            }
            
            # Cache the headers
            self._cached_headers = robotic_headers
            
            token_display = f"{xsrf_token[:10]}..." if len(xsrf_token) > 10 else xsrf_token
            logger.console(f"Successfully retrieved XSRF token: {token_display}")
            logger.console(f"Cookie header: {robotic_headers['Cookie']}")
            
            return robotic_headers
            
        except requests.RequestException as e:
            logger.console(f"Failed to retrieve robotic headers: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.console(f"Response status: {e.response.status_code}")
                logger.console(f"Response headers: {dict(e.response.headers)}")
            return None

    def get_latest_commit_hash(self) -> Optional[str]:
        """
        Retrieve the latest commit hash from the project's main branch.
        
        Returns:
            str: The latest commit hash, or None if the request fails
        """
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files"
        
        # Get the robotic headers (will fetch XSRF token if needed)
        headers = self._get_robotic_headers()
        if not headers:
            logger.console("Failed to get robotic headers")
            return None
        
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
            
            # Extract the commit hash from the branch object
            commit_hash = data["branch"]["commitHash"]
            
            return commit_hash
            
        except requests.RequestException as e:
            logger.console(f"API request failed: {e}")
            # Clear cached headers on error in case they're stale
            self._cached_headers = None
            raise
        except KeyError as e:
            logger.console(f"Expected key not found in response: {e}")
            raise
        except ValueError as e:
            logger.console(f"Failed to parse JSON response: {e}")
            raise
    
    def get_branch_info(self) -> Optional[dict]:
        """
        Retrieve the complete branch information including name and commit hash.
        
        Returns:
            dict: Branch information with 'name' and 'commitHash', or None if failed
        """
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files"
        
        # Get the robotic headers
        headers = self._get_robotic_headers()
        if not headers:
            logger.console("Failed to get robotic headers")
            return None
        
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
            logger.console(f"Failed to retrieve branch info: {e}")
            # Clear cached headers on error
            self._cached_headers = None
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
                logger.console("Failed to retrieve latest commit hash")
                return False
        
        # Determine if file is binary and read content
        is_binary = self._is_binary_file(local_file_path, force_binary)
        file_content, encoding_type = self._read_file_content(local_file_path, is_binary)
        
        logger.console(f"Uploading {'binary' if is_binary else 'text'} file:")
        logger.console(f"  Local path: {local_file_path}")
        logger.console(f"  Repository path: {repository_path}")
        logger.console(f"  Encoding: {encoding_type}")
        
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
        """
        logger.console("Warning: save_file_with_custom_path() is deprecated. Use save_file() with repository_path parameter instead.")
        
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
        """
        # Get robotic headers (includes XSRF token and cookies)
        headers = self._get_robotic_headers()
        if not headers:
            logger.console("Failed to get robotic headers - cannot proceed with upload")
            return False
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
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
            
            logger.console(f"File uploaded successfully to '{repository_path}'")
            return True
            
        except requests.RequestException as e:
            logger.console(f"Failed to upload file: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.console(f"Response status: {e.response.status_code}")
                logger.console(f"Response: {e.response.text}")
            # Clear cached headers on error
            self._cached_headers = None
            raise

    def save_multiple_files(self, 
                           file_operations: List[Dict[str, str]], 
                           author_name: str, 
                           author_email: str, 
                           commit_message: str,
                           parent_commit_hash: Optional[str] = None) -> bool:
        """
        Upload multiple files in a single commit.
        """
        # Get parent commit hash if not provided
        if parent_commit_hash is None:
            parent_commit_hash = self.get_latest_commit_hash()
            if parent_commit_hash is None:
                logger.console("Failed to retrieve latest commit hash")
                return False
        
        # Get robotic headers
        headers = self._get_robotic_headers()
        if not headers:
            logger.console("Failed to get robotic headers - cannot proceed with upload")
            return False
        
        operations = []
        
        for file_op in file_operations:
            local_path = file_op['local_path']
            repo_path = file_op.get('repo_path', os.path.basename(local_path))
            force_binary = file_op.get('force_binary')
            
            # Check if file exists
            if not os.path.exists(local_path):
                logger.console(f"Warning: File not found: {local_path}")
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
            
            logger.console(f"Prepared {'binary' if is_binary else 'text'} file:")
            logger.console(f"  Local: {local_path} -> Repository: {repo_path} (encoding: {encoding_type})")
        
        if not operations:
            logger.console("No valid files to upload")
            return False
        
        # Construct the endpoint URL
        endpoint = f"{self.base_url}/projects/{self.project_id}/jobs/{self.job_id}/files/upload"
        
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
            
            logger.console(f"Successfully uploaded {len(operations)} files")
            return True
            
        except requests.RequestException as e:
            logger.console(f"Failed to upload files: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.console(f"Response status: {e.response.status_code}")
                logger.console(f"Response: {e.response.text}")
            # Clear cached headers on error
            self._cached_headers = None
            raise

    def clear_headers_cache(self):
        """
        Clear the cached headers. Useful if tokens expire or become invalid.
        """
        self._cached_headers = None
        logger.console("Headers cache cleared")
