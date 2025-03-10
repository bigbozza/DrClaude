"""Database models for Dr. Claude application."""

import sqlite3
import json
import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class TherapyApproach(Enum):
    """Different therapeutic approaches available."""
    FREUDIAN = "Freudian"
    JUNGIAN = "Jungian" 
    CBT = "Cognitive Behavioral Therapy"
    HUMANISTIC = "Humanistic"
    EXISTENTIAL = "Existential"
    PSYCHODYNAMIC = "Psychodynamic"

class Database:
    """SQLite database manager with encryption capabilities."""
    
    def __init__(self, db_path: str, password: str):
        """Initialize database with encryption."""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.key = self._derive_key(password)
        self.fernet = Fernet(self.key)
        
        # Create database directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the database
        self._initialize_db()
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        salt = b'dr_claude_salt'  # In production, use a unique salt stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _initialize_db(self):
        """Create database and tables if they don't exist."""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        
        # Create user profile table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY,
            profile_data TEXT NOT NULL
        )
        ''')
        
        # Create journal entries table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            entry TEXT NOT NULL,
            is_condensed INTEGER DEFAULT 0
        )
        ''')
        
        # Create therapy sessions table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS therapy_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            approach TEXT NOT NULL,
            session_data TEXT NOT NULL
        )
        ''')
        
        # Create therapist notes table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS therapist_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            notes TEXT NOT NULL
        )
        ''')
        
        self.connection.commit()
    
    def encrypt(self, data: str) -> str:
        """Encrypt data before storing in database."""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data retrieved from database."""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def save_user_profile(self, profile_data: Dict[str, Any]):
        """Save or update user profile."""
        json_data = json.dumps(profile_data)
        encrypted_data = self.encrypt(json_data)
        
        # Check if profile exists
        self.cursor.execute("SELECT COUNT(*) FROM user_profile")
        count = self.cursor.fetchone()[0]
        
        if count == 0:
            self.cursor.execute("INSERT INTO user_profile (id, profile_data) VALUES (1, ?)", 
                             (encrypted_data,))
        else:
            self.cursor.execute("UPDATE user_profile SET profile_data = ? WHERE id = 1", 
                             (encrypted_data,))
        
        self.connection.commit()
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Retrieve user profile."""
        self.cursor.execute("SELECT profile_data FROM user_profile WHERE id = 1")
        result = self.cursor.fetchone()
        
        if result is None:
            return {}
        
        encrypted_data = result[0]
        json_data = self.decrypt(encrypted_data)
        return json.loads(json_data)
    
    def add_journal_entry(self, entry: str, date: Optional[str] = None):
        """Add a new journal entry."""
        if date is None:
            date = datetime.datetime.now().isoformat()
        
        encrypted_entry = self.encrypt(entry)
        self.cursor.execute(
            "INSERT INTO journal_entries (date, entry) VALUES (?, ?)",
            (date, encrypted_entry)
        )
        self.connection.commit()
    
    def get_journal_entries(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get journal entries within a date range."""
        query = "SELECT id, date, entry, is_condensed FROM journal_entries"
        params = []
        
        if start_date or end_date:
            query += " WHERE "
            if start_date:
                query += "date >= ?"
                params.append(start_date)
            if start_date and end_date:
                query += " AND "
            if end_date:
                query += "date <= ?"
                params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        self.cursor.execute(query, params)
        entries = []
        
        for row in self.cursor.fetchall():
            entry_id, date, encrypted_entry, is_condensed = row
            entry_text = self.decrypt(encrypted_entry)
            entries.append({
                "id": entry_id,
                "date": date,
                "entry": entry_text,
                "is_condensed": bool(is_condensed)
            })
        
        return entries
    
    def add_therapy_session(self, approach: TherapyApproach, session_data: Dict[str, Any], date: Optional[str] = None):
        """Add a new therapy session."""
        if date is None:
            date = datetime.datetime.now().isoformat()
        
        json_data = json.dumps(session_data)
        encrypted_data = self.encrypt(json_data)
        
        self.cursor.execute(
            "INSERT INTO therapy_sessions (date, approach, session_data) VALUES (?, ?, ?)",
            (date, approach.value, encrypted_data)
        )
        self.connection.commit()
    
    def get_therapy_sessions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get therapy sessions within a date range."""
        query = "SELECT id, date, approach, session_data FROM therapy_sessions"
        params = []
        
        if start_date or end_date:
            query += " WHERE "
            if start_date:
                query += "date >= ?"
                params.append(start_date)
            if start_date and end_date:
                query += " AND "
            if end_date:
                query += "date <= ?"
                params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        self.cursor.execute(query, params)
        sessions = []
        
        for row in self.cursor.fetchall():
            session_id, date, approach, encrypted_data = row
            session_data = json.loads(self.decrypt(encrypted_data))
            sessions.append({
                "id": session_id,
                "date": date,
                "approach": approach,
                "session_data": session_data
            })
        
        return sessions
    
    def add_therapist_note(self, note: str, date: Optional[str] = None):
        """Add a therapist note."""
        if date is None:
            date = datetime.datetime.now().isoformat()
        
        encrypted_note = self.encrypt(note)
        self.cursor.execute(
            "INSERT INTO therapist_notes (date, notes) VALUES (?, ?)",
            (date, encrypted_note)
        )
        self.connection.commit()
    
    def get_therapist_notes(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get therapist notes within a date range."""
        query = "SELECT id, date, notes FROM therapist_notes"
        params = []
        
        if start_date or end_date:
            query += " WHERE "
            if start_date:
                query += "date >= ?"
                params.append(start_date)
            if start_date and end_date:
                query += " AND "
            if end_date:
                query += "date <= ?"
                params.append(end_date)
        
        query += " ORDER BY date DESC"
        
        self.cursor.execute(query, params)
        notes = []
        
        for row in self.cursor.fetchall():
            note_id, date, encrypted_note = row
            note_text = self.decrypt(encrypted_note)
            notes.append({
                "id": note_id,
                "date": date,
                "note": note_text
            })
        
        return notes
    
    def condense_journal_entries(self, month: int, year: int):
        """Condense daily entries to a monthly summary for entries older than 2 months."""
        # Convert month/year to datetime objects for comparison
        target_month = datetime.datetime(year, month, 1)
        
        # Get entries for the specified month
        start_date = target_month.isoformat()
        end_date = (target_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1, hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(microseconds=1)
        end_date = end_date.isoformat()
        
        entries = self.get_journal_entries(start_date, end_date)
        
        if not entries:
            return
        
        # Create a condensed entry
        condensed_text = f"Condensed journal entries for {target_month.strftime('%B %Y')}:\n\n"
        for entry in entries:
            condensed_text += f"Date: {entry['date']}\n{entry['entry']}\n\n"
        
        # Add the condensed entry
        condensed_date = target_month.isoformat()
        encrypted_condensed = self.encrypt(condensed_text)
        
        self.cursor.execute(
            "INSERT INTO journal_entries (date, entry, is_condensed) VALUES (?, ?, 1)",
            (condensed_date, encrypted_condensed)
        )
        
        # Delete the original entries
        for entry in entries:
            self.cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry['id'],))
        
        self.connection.commit()
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()