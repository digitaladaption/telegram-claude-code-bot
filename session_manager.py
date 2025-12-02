"""
Session Manager for Telegram Claude Code Bot
Manages active Claude Code sessions per user
"""

import uuid
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Claude Code session information"""
    token: str
    user_id: int
    user_name: str
    working_dir: str
    created_at: datetime
    last_used: datetime
    is_active: bool = True

    def to_dict(self) -> dict:
        """Convert session to dictionary"""
        return {
            'token': self.token,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'working_dir': self.working_dir,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'is_active': self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        """Create session from dictionary"""
        return cls(
            token=data['token'],
            user_id=data['user_id'],
            user_name=data['user_name'],
            working_dir=data['working_dir'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_used=datetime.fromisoformat(data['last_used']),
            is_active=data.get('is_active', True)
        )


class SessionManager:
    """Manages Claude Code sessions for Telegram users"""

    def __init__(self, sessions_file: str = "data/sessions.json", default_working_dir: str = "/root/projects"):
        self.sessions_file = Path(sessions_file)
        self.default_working_dir = default_working_dir
        self.sessions: Dict[str, Session] = {}  # token -> Session
        self.user_sessions: Dict[int, str] = {}  # user_id -> active token

        # Ensure data directory exists
        self.sessions_file.parent.mkdir(exist_ok=True)

        # Load existing sessions
        self._load_sessions()

        # Clean up old sessions
        self._cleanup_old_sessions()

        logger.info(f"Session manager initialized with {len(self.sessions)} sessions")

    def create_session(self, user_id: int, user_name: str, working_dir: str = None) -> Session:
        """Create a new Claude Code session"""
        # Generate unique token
        token = str(uuid.uuid4())[:8]  # Short token for ease of use

        # Use provided working dir or default
        if not working_dir:
            working_dir = self.default_working_dir

        # Ensure working directory exists
        Path(working_dir).mkdir(exist_ok=True)

        # Create session
        session = Session(
            token=token,
            user_id=user_id,
            user_name=user_name,
            working_dir=working_dir,
            created_at=datetime.now(),
            last_used=datetime.now()
        )

        # Store session
        self.sessions[token] = session
        self.user_sessions[user_id] = token

        # Save to file
        self._save_sessions()

        logger.info(f"Created new session for user {user_name} ({user_id}) with token {token}")
        return session

    def get_session(self, token: str) -> Optional[Session]:
        """Get session by token"""
        return self.sessions.get(token)

    def get_user_active_session(self, user_id: int) -> Optional[Session]:
        """Get active session for user"""
        token = self.user_sessions.get(user_id)
        if token:
            session = self.sessions.get(token)
            if session and session.is_active:
                return session
            else:
                # Clean up invalid session
                self.user_sessions.pop(user_id, None)
        return None

    def validate_session(self, token: str, user_id: int) -> Optional[Session]:
        """Validate session token and ownership"""
        session = self.sessions.get(token)
        if session and session.is_active and session.user_id == user_id:
            # Check if session is not too old (24 hours)
            if datetime.now() - session.last_used < timedelta(hours=24):
                return session
            else:
                # Deactivate old session
                session.is_active = False
                logger.info(f"Deactivated old session {token}")
        return None

    def update_session(self, token: str):
        """Update session last used time"""
        session = self.sessions.get(token)
        if session:
            session.last_used = datetime.now()
            self._save_sessions()

    def end_session(self, token: str) -> bool:
        """End a session"""
        session = self.sessions.get(token)
        if session:
            session.is_active = False
            # Remove from user sessions
            self.user_sessions.pop(session.user_id, None)
            self._save_sessions()
            logger.info(f"Ended session {token} for user {session.user_name}")
            return True
        return False

    def end_user_session(self, user_id: int) -> bool:
        """End active session for user"""
        token = self.user_sessions.get(user_id)
        if token:
            return self.end_session(token)
        return False

    def get_user_sessions(self, user_id: int) -> List[Session]:
        """Get all sessions for a user"""
        user_sessions = []
        for session in self.sessions.values():
            if session.user_id == user_id:
                user_sessions.append(session)
        return sorted(user_sessions, key=lambda s: s.created_at, reverse=True)

    def get_all_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        active_sessions = []
        for session in self.sessions.values():
            if session.is_active:
                active_sessions.append(session)
        return active_sessions

    def _load_sessions(self):
        """Load sessions from file"""
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for session_data in data:
                    session = Session.from_dict(session_data)
                    self.sessions[session.token] = session

                    # Rebuild user_sessions mapping for active sessions
                    if session.is_active:
                        self.user_sessions[session.user_id] = session.token

                logger.info(f"Loaded {len(self.sessions)} sessions from file")
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")

    def _save_sessions(self):
        """Save sessions to file"""
        try:
            sessions_data = []
            for session in self.sessions.values():
                sessions_data.append(session.to_dict())

            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        cutoff_time = datetime.now() - timedelta(days=7)  # Keep sessions for 7 days
        sessions_to_remove = []

        for token, session in self.sessions.items():
            if not session.is_active and session.created_at < cutoff_time:
                sessions_to_remove.append(token)

        for token in sessions_to_remove:
            del self.sessions[token]
            logger.info(f"Cleaned up old session {token}")

        if sessions_to_remove:
            self._save_sessions()

    def get_session_stats(self) -> dict:
        """Get session statistics"""
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() if s.is_active])
        unique_users = len(set(s.user_id for s in self.sessions.values()))

        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'unique_users': unique_users,
            'oldest_session': min((s.created_at for s in self.sessions.values()), default=None),
            'newest_session': max((s.created_at for s in self.sessions.values()), default=None)
        }

    def export_sessions(self, user_id: int = None) -> List[dict]:
        """Export sessions data"""
        sessions = []

        if user_id:
            # Export specific user's sessions
            user_session_list = self.get_user_sessions(user_id)
            sessions = [session.to_dict() for session in user_session_list]
        else:
            # Export all sessions
            sessions = [session.to_dict() for session in self.sessions.values()]

        return sessions

    def import_sessions(self, sessions_data: List[dict]) -> int:
        """Import sessions data"""
        imported_count = 0

        for session_data in sessions_data:
            try:
                session = Session.from_dict(session_data)

                # Don't overwrite existing sessions
                if session.token not in self.sessions:
                    self.sessions[session.token] = session

                    # Rebuild user_sessions for active sessions
                    if session.is_active:
                        self.user_sessions[session.user_id] = session.token

                    imported_count += 1

            except Exception as e:
                logger.error(f"Failed to import session: {e}")

        if imported_count > 0:
            self._save_sessions()

        logger.info(f"Imported {imported_count} sessions")
        return imported_count