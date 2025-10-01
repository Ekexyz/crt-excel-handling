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
    
    def __init__(self, personal_access_token: str, project_id: str, job_id: str, debug_logging: bool = False):
        """
        Initialize the API client with authentication and project details.
        
        Args:
            personal_access_token (str): Personal access token for authentication
            project_id (str): The project ID
            job_id (str): The job ID
            debug_logging (bool): Enable detailed debug logging for headers and cookies
        """
        self.personal_access_token = personal_access_token
        self.project_id = project_id
        self.job_id = job_id
        self.base_url = "https://api.robotic.copado.com/pace/v4"
        self._cached_headers = None
        self.debug_logging = debug_logging
    
    def _log_response_debug(self, response: requests.Response, operation: str = "API Request"):
        """
        Log detailed debug information about the HTTP response including headers and cookies.
        
        Args:
            response: The HTTP response object
            operation: Description of the operation for logging context
        """
        if not self.debug_logging:
            return
            
        logger.console(f"\n=== DEBUG: {operation} ===")
        logger.console(f"Status Code: {response.status_code}")
        logger.console(f"URL: {response.url}")
        
        # Log request headers (mask sensitive information)
        logger.console("\n--- Request Headers ---")
        for header_name, header_value in response.request.headers.items():
            if header_name.lower() in ['authorization', 'x-authorization', 'cookie']:
                # Mask sensitive headers
                if header_name.lower() == 'cookie':
                    # Show cookie names but mask values
                    cookie_parts = header_value.split(';')
                    masked_cookies = []
                    for part in cookie_parts:
                        if '=' in part:
                            name, _ = part.split('=', 1)
                            masked_cookies.append(f"{name.strip()}=***")
                        else:
                            masked_cookies.append(part.strip())
                    logger.console(f"{header_name}: {'; '.join(masked_cookies)}")
                else:
                    # Mask other sensitive headers
                    masked_value = f"{header_value[:10]}..." if len(header_value) > 10 else "***"
                    logger.console(f"{header_name}: {masked_value}")
            else:
                logger.console(f"{header_name}: {header_value}")
        
        # Log response headers
        logger.console("\n--- Response Headers ---")
        for header_name, header_value in response.headers.items():
            logger.console(f"{header_name}: {header_value}")
        
        # Log Set-Cookie headers with detailed parsing
        set_cookie_headers = self._get_all_set_cookie_headers(response)
        if set_cookie_headers:
            logger.console("\n--- Set-Cookie Headers (Raw) ---")
            for i, cookie_header in enumerate(set_cookie_headers, 1):
                logger.console(f"Set-Cookie #{i}: {cookie_header}")
        
        # Log parsed cookies
        parsed_cookies = self._parse_cookies_from_set_cookie_headers(response)
        if parsed_cookies:
            logger.console("\n--- Parsed Cookies ---")
            for cookie_name, cookie_value in parsed_cookies.items():
                # Show first few characters of cookie value for debugging
                masked_value = f"{cookie_value[:10]}..." if len(cookie_value) > 10 else cookie_value
                logger.console(f"{cookie_name}: {masked_value}")
        
        # Log response cookies from requests session
        if response.cookies:
            logger.console("\n--- Response Cookies (requests.cookies) ---")
            for cookie in response.cookies:
                masked_value = f"{cookie.value[:10]}..." if len(cookie.value) > 10 else cookie.value
                logger.console(f"{cookie.name}: {masked_value} (domain: {cookie.domain}, path: {cookie.path})")
        
        logger.console("=== END DEBUG ===\n")
    
    def _get_all_set_cookie_headers(self, response: requests.Response) -> List[str]:
        """
        Get all Set-Cookie headers from the response, handling different ways they might be stored.
        
        Args:
            response: The HTTP response object
            
        Returns:
            List of Set-Cookie header values
        """
        set_cookie_headers = []
        
        # Method 1: Try get_list if available
        if hasattr(response.headers, 'get_list'):
            headers = response.headers.get_list('Set-Cookie')
            if headers:
                set_cookie_headers.extend(headers)
        
        # Method 2: Try single header
        single_header = response.headers.get('Set-Cookie')
        if single_header and single_header not in set_cookie_headers:
            set_cookie_headers.append(single_header)
        
        # Method 3: Try raw response if available
        if hasattr(response, 'raw') and hasattr(response.raw, '_original_response'):
            try:
                raw_headers = response.raw._original_response.msg.get_all('Set-Cookie')
                if raw_headers:
                    for header in raw_headers:
                        if header not in set_cookie_headers:
                            set_cookie_headers.append(header)
            except AttributeError:
                pass
        
        # Method 4: Try response.raw._original_response.headers if available
        if hasattr(response, 'raw') and hasattr(response.raw, '_original_response'):
            try:
                if hasattr(response.raw._original_response, 'headers'):
                    raw_headers = response.raw._original_response.headers
                    if hasattr(raw_headers, 'get_all'):
                        headers = raw_headers.get_all('Set-Cookie')
                        if headers:
                            for header in headers:
                                if header not in set_cookie_headers:
                                    set_cookie_headers.append(header)
            except AttributeError:
                pass
        
        return set_cookie_headers
    
    def _parse_cookies_from_set_cookie_headers(self, response: requests.Response) -> Dict[str, str]:
        """
        Parse cookies from Set-Cookie headers.
        
        Args:
            response: The HTTP response object
            
        Returns:
            dict: Dictionary mapping cookie names to values
        """
        cookies = {}
        
        # Get all Set-Cookie headers using the comprehensive method
        set_cookie_headers = self._get_all_set_cookie_headers(response)
        
        if self.debug_logging:
            logger.console(f"Found {len(set_cookie_headers)} Set-Cookie headers")
        
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
                            cookie_name = name.strip()
                            cookie_value = value.strip()
                            cookies[cookie_name] = cookie_value
                            
                            if self.debug_logging:
                                masked_value = f"{cookie_value[:10]}..." if len(cookie_value) > 10 else cookie_value
                                logger.console(f"Parsed cookie: {cookie_name} = {masked_value}")
        
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
            if self.debug_logging:
                logger.console("Using cached robotic headers")
            return self._cached_headers
            
        # Use the robots endpoint like in the TypeScript code
        robots_url = f"{self.base_url}/projects/{self.project_id}/robots"
        
        if self.debug_logging:
            logger.console(f"Fetching CSRF token from: {robots_url}")
        
        # Set up initial headers
        headers = {
            "Cookie": "",  # Start with empty cookie
            "X-Authorization": self.personal_access_token
        }
        
        try:
            # Make the GET request to fetch CSRF token
            response = requests.get(robots_url, headers=headers)
            
            # Log debug information about the response
            self._log_response_debug(response, "CSRF Token Fetch")
            
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
                if self.debug_logging:
                    logger.console("Debug: Full response analysis for missing XSRF token")
                    self._log_response_debug(response, "Missing XSRF Token Analysis")
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
                if self.debug_logging:
                    self._log_response_debug(e.response, "Error Response Analysis")
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
            
            # Log debug information
            self._log_response_debug(response, "Get Latest Commit Hash")
            
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Extract the commit hash from the branch object
            commit_hash = data["branch"]["commitHash"]
            
            if self.debug_logging:
                logger.console(f"Retrieved commit hash: {commit_hash}")
            
            return commit_hash
            
        except requests.RequestException as e:
            logger.console(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None and self.debug_logging:
                self._log_response_debug(e.response, "Get Commit Hash Error")
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
            
            # Log debug information
            self._log_response_debug(response, "Get Branch Info")
            
            response.raise_for_status()
            
            # Parse the JSON response
            data = response.json()
            
            # Return the complete branch object
            branch_info = data["branch"]
            
            if self.debug_logging:
                logger.console(f"Retrieved branch info: {branch_info}")
            
            return branch_info
            
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.console(f"Failed to retrieve branch info: {e}")
            if isinstance(e, requests.RequestException) and hasattr(e, 'response') and e.response is not None and self.debug_logging:
                self._log_response_debug(e.response, "Get Branch Info Error")
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
            
            # Log debug information
            self._log_response_debug(response, "File Upload")
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            logger.console(f"File uploaded successfully to '{repository_path}'")
            return True
            
        except requests.RequestException as e:
            logger.console(f"Failed to upload file: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.console(f"Response status: {e.response.status_code}")
                logger.console(f"Response: {e.response.text}")
                if self.debug_logging:
                    self._log_response_debug(e.response, "File Upload Error")
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
            
            # Log debug information
            self._log_response_debug(response, "Multiple Files Upload")
            
            # Raise an exception for bad status codes
            response.raise_for_status()
            
            logger.console(f"Successfully uploaded {len(operations)} files")
            return True
            
        except requests.RequestException as e:
            logger.console(f"Failed to upload files: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.console(f"Response status: {e.response.status_code}")
                logger.console(f"Response: {e.response.text}")
                if self.debug_logging:
                    self._log_response_debug(e.response, "Multiple Files Upload Error")
            # Clear cached headers on error
            self._cached_headers = None
            raise

    def enable_debug_logging(self):
        """
        Enable detailed debug logging for headers and cookies.
        """
        self.debug_logging = True
        logger.console("Debug logging enabled for HTTP headers and cookies")

    def disable_debug_logging(self):
        """
        Disable detailed debug logging for headers and cookies.
        """
        self.debug_logging = False
        logger.console("Debug logging disabled")

    def clear_headers_cache(self):
        """
        Clear the cached headers. Useful if tokens expire or become invalid.
        """
        self._cached_headers = None
        logger.console("Headers cache cleared")
