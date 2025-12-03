"""
Repository Manager
Handles GitHub repository cloning, indexing, and file operations
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RepoManager:
    """Manages GitHub repositories for users"""

    def __init__(self, base_repos_dir: str = "./repos"):
        self.base_repos_dir = Path(base_repos_dir)
        self.base_repos_dir.mkdir(exist_ok=True)

        # In-memory cache for user repos
        self.user_repos: Dict[int, Dict] = {}

        logger.info(f"RepoManager initialized with base directory: {self.base_repos_dir}")

    def validate_github_url(self, url: str) -> Tuple[bool, str]:
        """
        Validate GitHub URL and extract owner/repo

        Returns:
            (is_valid, normalized_url_or_error_message)
        """
        try:
            # Remove .git suffix if present
            url = url.rstrip('/')

            if url.endswith('.git'):
                url = url[:-4]

            # Parse different GitHub URL formats
            patterns = [
                r'https?://github\.com/([^/]+)/([^/]+)/?$',
                r'([^/]+)/([^/]+)$'  # Simple owner/repo format
            ]

            for pattern in patterns:
                match = re.match(pattern, url)
                if match:
                    owner, repo = match.groups()
                    normalized_url = f"https://github.com/{owner}/{repo}"
                    return True, normalized_url

            return False, "Invalid GitHub URL format. Expected: https://github.com/owner/repo"

        except Exception as e:
            return False, f"Error parsing URL: {str(e)}"

    def get_user_repo_dir(self, user_id: int, owner: str, repo: str) -> Path:
        """Get the local directory path for a user's repo"""
        return self.base_repos_dir / str(user_id) / owner / repo

    async def clone_or_update_repo(self, user_id: int, github_url: str) -> Dict:
        """
        Clone or update a GitHub repository for a user

        Returns:
            Dict with success status, repo info, or error details
        """
        # Validate URL
        is_valid, result = self.validate_github_url(github_url)
        if not is_valid:
            return {
                'success': False,
                'error': result,
                'error_type': 'invalid_url'
            }

        normalized_url = result

        # Extract owner and repo
        match = re.match(r'https?://github\.com/([^/]+)/([^/]+)/?$', normalized_url)
        if not match:
            return {
                'success': False,
                'error': 'Could not extract owner/repo from URL',
                'error_type': 'parse_error'
            }

        owner, repo_name = match.groups()

        # Check if git is available
        if not self._check_git_available():
            return {
                'success': False,
                'error': 'Git is not installed or not available',
                'error_type': 'git_missing'
            }

        # Get repo directory
        repo_dir = self.get_user_repo_dir(user_id, owner, repo_name)

        try:
            # Clone or update repo
            if repo_dir.exists():
                # Update existing repo
                success, message = await self._update_repo(repo_dir)
                if success:
                    action = "updated"
                else:
                    return {
                        'success': False,
                        'error': f'Failed to update repository: {message}',
                        'error_type': 'update_error'
                    }
            else:
                # Clone new repo
                success, message = await self._clone_repo(normalized_url, repo_dir)
                if success:
                    action = "cloned"
                else:
                    return {
                        'success': False,
                        'error': f'Failed to clone repository: {message}',
                        'error_type': 'clone_error'
                    }

            # Index the repo
            repo_info = self._index_repo(repo_dir, owner, repo_name, normalized_url)

            # Store in user's active repos
            self.user_repos[user_id] = {
                'owner': owner,
                'repo': repo_name,
                'url': normalized_url,
                'path': str(repo_dir),
                'info': repo_info,
                'last_accessed': str(repo_dir.stat().st_mtime)
            }

            return {
                'success': True,
                'action': action,
                'owner': owner,
                'repo': repo_name,
                'url': normalized_url,
                'path': str(repo_dir),
                'info': repo_info
            }

        except Exception as e:
            logger.error(f"Error in clone_or_update_repo: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'error_type': 'system_error'
            }

    def get_user_active_repo(self, user_id: int) -> Optional[Dict]:
        """Get the active repository for a user"""
        return self.user_repos.get(user_id)

    def list_files_in_repo(self, user_id: int, relative_path: str = "") -> Optional[List[Dict]]:
        """
        List files in user's active repo, optionally filtered by path

        Returns:
            List of file/directory info dicts or None if no repo loaded
        """
        user_repo = self.get_user_active_repo(user_id)
        if not user_repo:
            return None

        repo_path = Path(user_repo['path'])
        target_path = repo_path / relative_path if relative_path else repo_path

        if not target_path.exists():
            return []

        if not target_path.is_dir():
            return []

        try:
            files = []
            for item in target_path.iterdir():
                # Skip hidden files and git directories
                if item.name.startswith('.'):
                    continue

                relative_item_path = item.relative_to(repo_path)

                file_info = {
                    'name': item.name,
                    'path': str(relative_item_path),
                    'is_dir': item.is_dir(),
                    'size': item.stat().st_size if item.is_file() else 0,
                    'extension': item.suffix if item.is_file() else None
                }

                # Add language detection for common files
                if item.is_file():
                    file_info['language'] = self._detect_language(item.suffix, item.name)

                files.append(file_info)

            # Sort: directories first, then files, both alphabetically
            files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

            return files

        except Exception as e:
            logger.error(f"Error listing files in {target_path}: {e}")
            return []

    async def _clone_repo(self, url: str, target_dir: Path) -> Tuple[bool, str]:
        """Clone a GitHub repository"""
        try:
            # Create parent directories
            target_dir.parent.mkdir(parents=True, exist_ok=True)

            # Clone the repository
            result = subprocess.run(
                ['git', 'clone', url, str(target_dir)],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            if result.returncode == 0:
                return True, "Repository cloned successfully"
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Clone operation timed out (60s)"
        except Exception as e:
            return False, f"Clone error: {str(e)}"

    async def _update_repo(self, repo_dir: Path) -> Tuple[bool, str]:
        """Update an existing repository"""
        try:
            # Change to repo directory and pull latest changes
            result = subprocess.run(
                ['git', 'pull', 'origin', 'main'],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            if result.returncode == 0:
                return True, "Repository updated successfully"
            else:
                # Try 'master' branch if 'main' failed
                result = subprocess.run(
                    ['git', 'pull', 'origin', 'master'],
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True, "Repository updated successfully (master branch)"
                else:
                    return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Update operation timed out (30s)"
        except Exception as e:
            return False, f"Update error: {str(e)}"

    def _index_repo(self, repo_dir: Path, owner: str, repo_name: str, url: str) -> Dict:
        """Index repository and gather basic metadata"""
        try:
            # Count files and directories
            total_files = 0
            total_dirs = 0
            extensions = set()

            for root, dirs, files in os.walk(repo_dir):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')

                total_dirs += len(dirs)
                total_files += len(files)

                for file in files:
                    if not file.startswith('.'):
                        ext = Path(file).suffix.lower()
                        if ext:
                            extensions.add(ext)

            return {
                'owner': owner,
                'repo': repo_name,
                'url': url,
                'total_files': total_files,
                'total_dirs': total_dirs,
                'extensions': sorted(list(extensions)),
                'languages': self._extensions_to_languages(extensions),
                'indexed_at': str(repo_dir.stat().st_mtime)
            }

        except Exception as e:
            logger.error(f"Error indexing repo {repo_dir}: {e}")
            return {
                'owner': owner,
                'repo': repo_name,
                'url': url,
                'total_files': 0,
                'total_dirs': 0,
                'extensions': [],
                'languages': [],
                'error': str(e)
            }

    def _check_git_available(self) -> bool:
        """Check if git is available on the system"""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _detect_language(self, extension: str, filename: str) -> Optional[str]:
        """Detect programming language from file extension"""
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'Sass',
            '.less': 'Less',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.json': 'JSON',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.md': 'Markdown',
            '.txt': 'Text',
            '.dockerfile': 'Docker',
            '.gitignore': 'Git',
            '.env': 'Environment',
        }

        # Check extension first
        if extension.lower() in language_map:
            return language_map[extension.lower()]

        # Check special filenames
        if filename.lower() in ['dockerfile', 'makefile', 'readme', 'license']:
            return filename.lower().title()

        return None

    def _extensions_to_languages(self, extensions: set) -> List[str]:
        """Convert file extensions to language names"""
        languages = set()
        for ext in extensions:
            lang = self._detect_language(ext, "")
            if lang:
                languages.add(lang)
        return sorted(list(languages))