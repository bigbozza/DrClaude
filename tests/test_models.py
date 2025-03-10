"""Tests for database models."""

import unittest
import os
import tempfile
import json
import datetime
from src.models import Database, TherapyApproach

class TestDatabase(unittest.TestCase):
    """Test cases for the Database class."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_db.db")
        self.test_password = "test_password"
        self.db = Database(self.db_path, self.test_password)
    
    def tearDown(self):
        """Clean up after tests."""
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_encryption_decryption(self):
        """Test that encryption and decryption work properly."""
        test_data = "This is a test string for encryption."
        encrypted = self.db.encrypt(test_data)
        decrypted = self.db.decrypt(encrypted)
        self.assertEqual(decrypted, test_data)
        self.assertNotEqual(encrypted, test_data)
    
    def test_user_profile(self):
        """Test saving and retrieving user profile."""
        test_profile = {
            "name": "Test User",
            "age": "30",
            "gender": "Non-binary",
            "therapy_goal": "Reduce anxiety"
        }
        
        # Save profile
        self.db.save_user_profile(test_profile)
        
        # Retrieve profile
        retrieved_profile = self.db.get_user_profile()
        
        # Check that the retrieved profile matches the original
        self.assertEqual(retrieved_profile, test_profile)
    
    def test_journal_entries(self):
        """Test adding and retrieving journal entries."""
        test_entries = [
            "Today was a difficult day. I felt anxious about my presentation.",
            "I'm feeling better today. The presentation went well.",
            "I had a good conversation with my friend today."
        ]
        
        # Add entries with dates
        today = datetime.datetime.now()
        
        for i, entry in enumerate(test_entries):
            entry_date = (today - datetime.timedelta(days=i)).isoformat()
            self.db.add_journal_entry(entry, entry_date)
        
        # Retrieve entries
        retrieved_entries = self.db.get_journal_entries()
        
        # Check that we have the correct number of entries
        self.assertEqual(len(retrieved_entries), len(test_entries))
        
        # Check entry content
        for i, original_entry in enumerate(reversed(test_entries)):  # Reversed because entries are returned newest first
            self.assertEqual(retrieved_entries[i]["entry"], original_entry)
    
    def test_therapy_session(self):
        """Test adding and retrieving therapy sessions."""
        test_session = {
            "transcript": [
                "User: I've been feeling anxious lately.",
                "Therapist: Can you tell me more about that?"
            ],
            "notes": "Patient reports anxiety. Exploring triggers."
        }
        
        # Add a therapy session
        self.db.add_therapy_session(TherapyApproach.CBT, test_session)
        
        # Retrieve sessions
        sessions = self.db.get_therapy_sessions()
        
        # Check that we have one session
        self.assertEqual(len(sessions), 1)
        
        # Check session content
        self.assertEqual(sessions[0]["approach"], TherapyApproach.CBT.value)
        self.assertEqual(sessions[0]["session_data"], test_session)
    
    def test_therapist_notes(self):
        """Test adding and retrieving therapist notes."""
        test_note = "Patient shows progress in managing anxiety. Continue to work on breathing exercises."
        
        # Add a note
        self.db.add_therapist_note(test_note)
        
        # Retrieve notes
        notes = self.db.get_therapist_notes()
        
        # Check that we have one note
        self.assertEqual(len(notes), 1)
        
        # Check note content
        self.assertEqual(notes[0]["note"], test_note)
    
    def test_condense_journal_entries(self):
        """Test condensing journal entries."""
        # Add several entries with dates in a specific month
        test_month = 5  # May
        test_year = 2023
        
        # Create date objects for the test month
        base_date = datetime.datetime(test_year, test_month, 1)
        
        # Add 5 entries for the test month
        for day in range(1, 6):
            entry_date = base_date.replace(day=day).isoformat()
            self.db.add_journal_entry(f"Test entry for day {day}", entry_date)
        
        # Check that we have 5 entries
        entries_before = self.db.get_journal_entries()
        self.assertEqual(len(entries_before), 5)
        
        # Condense the entries
        self.db.condense_journal_entries(test_month, test_year)
        
        # Check that we now have 1 condensed entry instead of 5 individual entries
        entries_after = self.db.get_journal_entries()
        self.assertEqual(len(entries_after), 1)
        self.assertTrue(entries_after[0]["is_condensed"])
        
        # Check that the condensed entry contains information from all original entries
        for day in range(1, 6):
            self.assertIn(f"Test entry for day {day}", entries_after[0]["entry"])

if __name__ == "__main__":
    unittest.main()