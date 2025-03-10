"""Main application for Dr. Claude therapeutic journaling application."""

import os
import datetime
import sys
import getpass
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from colorama import Fore, Back, Style, init

from models import Database, TherapyApproach
from llm import TherapistLLM, ModelProvider, ModelConfig

# Initialize colorama for cross-platform colored terminal output
init(autoreset=True)

def get_multiline_input(prompt_text="", end_with_ctrl_d=True, history=None):
    """
    Get multiline input from the user, with proper handling of backspace across lines.
    
    Args:
        prompt_text: The prompt text to display
        end_with_ctrl_d: If True, input ends with Ctrl+D or /send, otherwise Enter on empty line
        history: Optional history instance for input history
        
    Returns:
        The entered text as a string
    """
    # Create a prompt session
    session = PromptSession(history=history or InMemoryHistory())
    
    if prompt_text:
        print(f"{prompt_text}")
    
    if end_with_ctrl_d:
        print("(Type '/send' on a new line or press Ctrl+D when finished)")
        lines = []
        while True:
            try:
                line = session.prompt("> ")
                if line.strip() == "/send":
                    break
                # Check if it's a command (starts with /)
                elif line.strip().startswith('/') and line.strip() != '/':
                    # Return the command prefixed with special marker
                    return f"__COMMAND__{line.strip()}"
                lines.append(line)
            except EOFError:
                # User pressed Ctrl+D
                break
        
        return "\n".join(lines)
    else:
        print("(Enter an empty line to finish)")
        lines = []
        while True:
            try:
                line = session.prompt("> ")
                if not line and lines:  # Empty line and we have previous content
                    break
                lines.append(line)
            except EOFError:
                break  # Allow Ctrl+D as an alternative exit
        
        return "\n".join(lines)


class DrClaude:
    """Main Dr. Claude application class."""
    
    DEFAULT_DATA_DIR = os.path.expanduser("~/.dr-claude")
    DEFAULT_DB_FILE = "journal_data.db"
    CONFIG_FILE = "config.json"
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the application."""
        self.data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.db_path = os.path.join(self.data_dir, self.DEFAULT_DB_FILE)
        self.config_path = os.path.join(self.data_dir, self.CONFIG_FILE)
        self.db = None
        self.config = self._load_config()
        self.llm = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        os.makedirs(self.data_dir, exist_ok=True)
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration."""
        config = {
            "llm_provider": "Anthropic",
            "llm_model": "claude-3-7-sonnet-20250219",
            "default_therapy_approach": "Cognitive Behavioral Therapy",
            "api_keys": {}
        }
        
        # Save the default config
        self._save_config(config)
        return config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def unlock_vault(self, password: str) -> bool:
        """Unlock the encrypted database."""
        try:
            self.db = Database(self.db_path, password)
            return True
        except Exception as e:
            print(f"Error unlocking vault: {e}")
            return False
    
    def configure_llm(self) -> bool:
        """Configure LLM settings interactively."""
        print("\nConfigure LLM Settings")
        print("=====================")
        
        # Select provider
        providers = [provider.value for provider in ModelProvider]
        print("\nAvailable LLM providers:")
        for i, provider in enumerate(providers):
            print(f"{i+1}. {provider}")
        
        provider_choice = input(f"Select provider (1-{len(providers)}, default: {self.config['llm_provider']}): ")
        if provider_choice.strip():
            try:
                provider_idx = int(provider_choice) - 1
                if 0 <= provider_idx < len(providers):
                    self.config['llm_provider'] = providers[provider_idx]
                else:
                    print("Invalid choice, keeping current setting")
            except ValueError:
                print("Invalid input, keeping current setting")
        
        # Get API key if needed
        provider_enum = ModelProvider(self.config['llm_provider'])
        if provider_enum != ModelProvider.OLLAMA:
            current_key = self.config.get('api_keys', {}).get(self.config['llm_provider'], '')
            masked_key = '*' * 8 + current_key[-4:] if current_key else ''
            
            print(f"\nCurrent API key for {self.config['llm_provider']}: {masked_key if current_key else 'Not set'}")
            key_prompt = "Enter new API key (leave empty to keep current): " if current_key else f"Enter {self.config['llm_provider']} API key: "
            
            api_key = getpass.getpass(key_prompt)
            if api_key:
                if 'api_keys' not in self.config:
                    self.config['api_keys'] = {}
                self.config['api_keys'][self.config['llm_provider']] = api_key
        
        # Get available models
        try:
            api_key = self.config.get('api_keys', {}).get(self.config['llm_provider'])
            available_models = ModelConfig.get_available_models(provider_enum, api_key)
            
            print("\nAvailable models:")
            for i, model in enumerate(available_models):
                print(f"{i+1}. {model}")
            
            model_choice = input(f"Select model (1-{len(available_models)}, default: {self.config['llm_model']}): ")
            if model_choice.strip():
                try:
                    model_idx = int(model_choice) - 1
                    if 0 <= model_idx < len(available_models):
                        self.config['llm_model'] = available_models[model_idx]
                    else:
                        print("Invalid choice, keeping current setting")
                except ValueError:
                    print("Invalid input, keeping current setting")
        except Exception as e:
            print(f"Error getting available models: {e}")
        
        # Select default therapy approach
        approaches = [approach.value for approach in TherapyApproach]
        print("\nAvailable therapy approaches:")
        for i, approach in enumerate(approaches):
            print(f"{i+1}. {approach}")
        
        approach_choice = input(f"Select default approach (1-{len(approaches)}, default: {self.config['default_therapy_approach']}): ")
        if approach_choice.strip():
            try:
                approach_idx = int(approach_choice) - 1
                if 0 <= approach_idx < len(approaches):
                    self.config['default_therapy_approach'] = approaches[approach_idx]
                else:
                    print("Invalid choice, keeping current setting")
            except ValueError:
                print("Invalid input, keeping current setting")
        
        # Save the updated config
        self._save_config(self.config)
        print("\nConfiguration saved successfully")
        return True
    
    def initialize_llm(self) -> bool:
        """Initialize LLM with current configuration."""
        try:
            provider = ModelProvider(self.config['llm_provider'])
            model = self.config['llm_model']
            api_key = self.config.get('api_keys', {}).get(self.config['llm_provider'])
            
            model_config = ModelConfig(provider, model, api_key)
            self.llm = TherapistLLM(model_config)
            return True
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            return False
    
    def add_journal_entry(self):
        """Add a new journal entry."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        print("\nNew Journal Entry")
        print("=================")
        
        # Use our improved input handler
        entry = get_multiline_input(prompt_text="Enter your journal entry below:", end_with_ctrl_d=True)
        
        if not entry.strip():
            print("Journal entry cannot be empty")
            return
        
        date = datetime.datetime.now().isoformat()
        self.db.add_journal_entry(entry, date)
        print("\nJournal entry saved successfully")
    
    def view_journal_entries(self):
        """View recent journal entries."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        entries = self.db.get_journal_entries()
        if not entries:
            print("No journal entries found")
            return
        
        print("\nRecent Journal Entries")
        print("=====================")
        for i, entry in enumerate(entries[:10]):  # Show most recent 10 entries
            date_obj = datetime.datetime.fromisoformat(entry['date'])
            formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
            condensed_tag = " [Condensed]" if entry['is_condensed'] else ""
            
            print(f"\n{i+1}. {formatted_date}{condensed_tag}")
            print("-" * len(formatted_date))
            print(entry['entry'])
            print()
    
    def _select_therapy_approach(self) -> str:
        """Select a therapy approach interactively."""
        approaches = [approach.value for approach in TherapyApproach]
        default_approach = self.config['default_therapy_approach']
        
        print("\nSelect Therapy Approach")
        print("======================")
        for i, approach in enumerate(approaches):
            default_tag = " (default)" if approach == default_approach else ""
            print(f"{i+1}. {approach}{default_tag}")
        
        choice = input(f"Select approach (1-{len(approaches)}, Enter for default): ")
        if not choice.strip():
            return default_approach
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(approaches):
                return approaches[idx]
            else:
                print("Invalid choice, using default")
                return default_approach
        except ValueError:
            print("Invalid input, using default")
            return default_approach
    
    def _show_session_commands(self):
        """Display available commands for the therapy session."""
        print(f"\n{Fore.YELLOW}Available Commands:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}/help{Style.RESET_ALL} - Show these commands")
        print(f"{Fore.YELLOW}/notes{Style.RESET_ALL} - View therapist's notes for this session")
        print(f"{Fore.YELLOW}/all_notes{Style.RESET_ALL} - View all previous therapist notes")
        print(f"{Fore.YELLOW}/save{Style.RESET_ALL} - Save notes but continue the session")
        print(f"{Fore.YELLOW}/send{Style.RESET_ALL} - Finish typing your message and send it to the therapist")
        print(f"{Fore.YELLOW}/end{Style.RESET_ALL} or {Fore.YELLOW}exit{Style.RESET_ALL} or {Fore.YELLOW}quit{Style.RESET_ALL} - End the session and save notes")
    
    def _generate_interim_notes(self, approach, user_profile, journal_entries, therapist_notes, session_transcript):
        """Generate interim therapist notes during a session."""
        print(f"\n{Style.DIM}Generating interim therapy notes...{Style.RESET_ALL}")
        session_data = "\n".join(session_transcript)
        
        # Generate therapist notes
        notes = self.llm.generate_therapist_notes(
            approach, user_profile, journal_entries, therapist_notes, session_data
        )
        
        return notes
    
    def _display_notes(self, notes, title="Therapist Notes"):
        """Display therapist notes with formatting."""
        print(f"\n{title}")
        print("=" * len(title))
        # Display notes in blue for differentiation
        print(f"{Fore.BLUE}{notes}{Style.RESET_ALL}")
        
    def start_therapy_session(self):
        """Start a therapy session with the LLM."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        if not self.llm:
            success = self.initialize_llm()
            if not success:
                return
        
        # Select therapy approach
        approach = self._select_therapy_approach()
        
        # Get user profile, journal entries, and therapist notes
        user_profile = self.db.get_user_profile()
        journal_entries = self.db.get_journal_entries()
        therapist_notes = self.db.get_therapist_notes()
        
        print(f"\nStarting {approach} therapy session")
        print("=" * (22 + len(approach)))
        
        # Show available commands
        self._show_session_commands()
        print("\nStart typing to talk to the therapist. Use commands (like /help) to access other features.")
        
        # Create a session history for this conversation
        conversation_history = InMemoryHistory()
        session_transcript = []
        current_notes = ""
        
        # For periodic note saving (every 10 messages)
        message_count = 0
        auto_save_threshold = 10
        last_save_time = datetime.datetime.now()
        
        while True:
            # Start in chat mode by default
            user_input = get_multiline_input(
                prompt_text=f"\n{Style.BRIGHT}You:",
                end_with_ctrl_d=True,
                history=conversation_history
            )
            
            # Check if this is a command (special marker from get_multiline_input)
            if user_input.startswith("__COMMAND__"):
                command = user_input[11:].lower()  # Remove the special marker
                
                # Handle commands that start with slash
                if command.startswith('/'):
                    command = command[1:]  # Remove the leading slash
                
                # Handle commands
                if command in ['end', 'exit', 'quit']:
                    print(f"\n{Fore.YELLOW}Ending session...{Style.RESET_ALL}")
                    break
                    
                elif command == 'help':
                    self._show_session_commands()
                    
                elif command == 'notes':
                    if not current_notes:
                        # Generate notes if we don't have any yet
                        current_notes = self._generate_interim_notes(
                            approach, user_profile, journal_entries, therapist_notes, session_transcript
                        )
                    
                    self._display_notes(current_notes, "Current Session Notes")
                    
                elif command == 'all_notes':
                    if therapist_notes:
                        print(f"\n{Fore.YELLOW}Previous Therapy Notes:{Style.RESET_ALL}")
                        for i, note in enumerate(therapist_notes[:5]):  # Show last 5 notes
                            date_obj = datetime.datetime.fromisoformat(note['date'])
                            formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
                            print(f"\n{Fore.CYAN}Session {i+1}: {formatted_date}{Style.RESET_ALL}")
                            print(f"{Fore.BLUE}{note['note']}{Style.RESET_ALL}")
                            print("-" * 50)
                    else:
                        print(f"\n{Fore.YELLOW}No previous therapy notes available.{Style.RESET_ALL}")
                    
                elif command == 'save':
                    # Generate interim notes and save them
                    current_notes = self._generate_interim_notes(
                        approach, user_profile, journal_entries, therapist_notes, session_transcript
                    )
                    
                    date = datetime.datetime.now().isoformat()
                    self.db.add_therapist_note(current_notes, date)
                    
                    print(f"\n{Fore.GREEN}Notes saved. Session continuing.{Style.RESET_ALL}")
                    self._display_notes(current_notes, "Current Session Notes")
                    
                    # Add the notes to the available context for future responses
                    therapist_notes = self.db.get_therapist_notes()
                    
                    # Reset message counter
                    message_count = 0
                    last_save_time = datetime.datetime.now()
                
                else:
                    print(f"\n{Fore.RED}Unknown command: {command}{Style.RESET_ALL}")
                    self._show_session_commands()
                
                continue
            
            # Skip empty messages
            if not user_input.strip():
                continue
            
            # Process regular message
            session_transcript.append(f"User: {user_input}")
            
            print(f"\n{Style.DIM}Therapist is thinking...{Style.RESET_ALL}")
            response = self.llm.generate_response(
                approach, user_profile, journal_entries, therapist_notes, user_input
            )
            
            # Check for error
            if 'error' in response:
                print(f"{Fore.RED}Error: {response['error']}{Style.RESET_ALL}")
                continue
            
            therapist_response = response['response']
            
            # Format therapist response with green text for better readability
            print(f"\n{Style.BRIGHT}Therapist: {Fore.GREEN}{therapist_response}{Style.RESET_ALL}")
            
            session_transcript.append(f"Therapist: {therapist_response}")
            
            # Increment message counter
            message_count += 1
            
            # Check if we should auto-save notes (every 10 messages or 15 minutes)
            current_time = datetime.datetime.now()
            time_diff = (current_time - last_save_time).total_seconds() / 60
            
            if message_count >= auto_save_threshold or time_diff >= 15:
                # Auto-generate and save notes
                current_notes = self._generate_interim_notes(
                    approach, user_profile, journal_entries, therapist_notes, session_transcript
                )
                
                date = current_time.isoformat()
                self.db.add_therapist_note(current_notes, date)
                
                print(f"\n{Fore.YELLOW}Auto-saving session notes...{Style.RESET_ALL}")
                
                # Add the notes to the available context for future responses
                therapist_notes = self.db.get_therapist_notes()
                
                # Reset message counter and timer
                message_count = 0
                last_save_time = current_time
        
        # End of session - generate final notes if we haven't just saved
        if message_count > 0:
            print(f"\n{Style.DIM}Generating final therapy notes...{Style.RESET_ALL}")
            session_data = "\n".join(session_transcript)
            
            # Generate therapist notes
            current_notes = self.llm.generate_therapist_notes(
                approach, user_profile, journal_entries, therapist_notes, session_data
            )
            
            date = datetime.datetime.now().isoformat()
            self.db.add_therapist_note(current_notes, date)
        
        # Save session data
        session_record = {
            "transcript": session_transcript,
            "notes": current_notes
        }
        self.db.add_therapy_session(TherapyApproach(approach), session_record, date)
        
        print(f"\n{Fore.GREEN}Therapy session completed and notes saved{Style.RESET_ALL}")
        
        # Ask to view the notes
        view_notes = input("Would you like to view the therapist's notes? (y/n): ")
        if view_notes.lower() in ['y', 'yes']:
            self._display_notes(current_notes)
    
    def update_user_profile(self):
        """Update user profile information."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        # Get current profile
        profile = self.db.get_user_profile()
        
        print("\nUpdate User Profile")
        print("==================")
        print("(Leave fields empty to keep current values)")
        
        fields = [
            ("name", "Full name"),
            ("age", "Age"),
            ("gender", "Gender"),
            ("marital_status", "Marital status"),
            ("children", "Children"),
            ("occupation", "Occupation"),
            ("therapy_goal", "Goal for therapy"),
            ("medical_history", "Medical history (relevant to therapy)"),
            ("medication", "Current medications"),
            ("previous_therapy", "Previous therapy experience"),
            ("trauma_history", "Trauma history"),
            ("substance_use", "Substance use history"),
            ("family_history", "Family mental health history"),
            ("support_system", "Current support system")
        ]
        
        # Create a dedicated prompt session for profile updates
        session = PromptSession()
        
        for field_key, field_name in fields:
            current = profile.get(field_key, "")
            current_display = f" {Style.DIM}(current: {current}){Style.RESET_ALL}" if current else ""
            
            # For multi-line fields, use our special input handler
            if field_key in ["therapy_goal", "medical_history", "trauma_history", "support_system"]:
                print(f"\n{field_name}{current_display}:")
                value = get_multiline_input(end_with_ctrl_d=True)
            else:
                # For single line fields, use standard prompt
                value = session.prompt(f"{field_name}{current_display}: ")
            
            if value.strip():
                profile[field_key] = value
        
        self.db.save_user_profile(profile)
        print(f"\n{Fore.GREEN}User profile updated successfully{Style.RESET_ALL}")
    
    def view_user_profile(self):
        """View user profile information."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        profile = self.db.get_user_profile()
        if not profile:
            print("No user profile information found")
            return
        
        print("\nUser Profile")
        print("============")
        
        # Define field display order and names
        fields = [
            ("name", "Name"),
            ("age", "Age"),
            ("gender", "Gender"),
            ("marital_status", "Marital Status"),
            ("children", "Children"),
            ("occupation", "Occupation"),
            ("therapy_goal", "Therapy Goal"),
            ("medical_history", "Medical History"),
            ("medication", "Medications"),
            ("previous_therapy", "Previous Therapy"),
            ("trauma_history", "Trauma History"),
            ("substance_use", "Substance Use"),
            ("family_history", "Family History"),
            ("support_system", "Support System")
        ]
        
        for field_key, field_name in fields:
            if field_key in profile and profile[field_key]:
                # Format field name in cyan and value in normal text
                print(f"{Fore.CYAN}{field_name}{Style.RESET_ALL}: {profile[field_key]}")
    
    def view_all_therapist_notes(self):
        """View all therapist notes."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        therapist_notes = self.db.get_therapist_notes()
        if not therapist_notes:
            print("No therapist notes found")
            return
        
        print("\nAll Therapist Notes")
        print("==================")
        
        # Display notes from newest to oldest
        total_notes = len(therapist_notes)
        page_size = 3  # Show 3 notes per page for better readability
        current_page = 0
        total_pages = (total_notes + page_size - 1) // page_size  # Ceiling division
        
        while current_page < total_pages:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, total_notes)
            
            # Show page info
            if total_pages > 1:
                print(f"\n{Fore.YELLOW}Showing page {current_page + 1} of {total_pages}{Style.RESET_ALL}")
            
            # Display notes for current page
            for i in range(start_idx, end_idx):
                note = therapist_notes[i]
                date_obj = datetime.datetime.fromisoformat(note['date'])
                formatted_date = date_obj.strftime("%A, %B %d, %Y at %I:%M %p")
                
                print(f"\n{Fore.CYAN}Session {i+1}: {formatted_date}{Style.RESET_ALL}")
                print("-" * (len(formatted_date) + 10))
                print(f"{Fore.BLUE}{note['note']}{Style.RESET_ALL}")
                
                # Add a separator between notes
                if i < end_idx - 1:
                    print("\n" + "-" * 50)
            
            # Show navigation options if there are multiple pages
            if total_pages > 1:
                print(f"\n{Fore.YELLOW}Navigation:{Style.RESET_ALL}")
                if current_page > 0:
                    print(f"{Fore.YELLOW}p{Style.RESET_ALL} - Previous page")
                if current_page < total_pages - 1:
                    print(f"{Fore.YELLOW}n{Style.RESET_ALL} - Next page")
                print(f"{Fore.YELLOW}q{Style.RESET_ALL} - Return to main menu")
                
                choice = input("\nEnter choice: ").lower()
                if choice == 'p' and current_page > 0:
                    current_page -= 1
                elif choice == 'n' and current_page < total_pages - 1:
                    current_page += 1
                elif choice == 'q':
                    break
            else:
                # If there's only one page, just ask to press Enter
                input(f"\n{Fore.YELLOW}Press Enter to return to the main menu...{Style.RESET_ALL}")
                break
    
    def condense_old_entries(self):
        """Condense old journal entries."""
        if not self.db:
            print("Please unlock the vault first")
            return
        
        print("\nCondensing old journal entries...")
        
        # Calculate months to condense (entries older than 2 months)
        today = datetime.datetime.now()
        two_months_ago = today.replace(day=1) - datetime.timedelta(days=1)  # Last day of month before last
        
        # Condense each month older than 2 months ago
        current_month = two_months_ago.replace(day=1)
        
        # Go back up to 12 months
        months_condensed = 0
        for _ in range(12):
            current_month = (current_month.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
            self.db.condense_journal_entries(current_month.month, current_month.year)
            months_condensed += 1
        
        print(f"Condensed entries from {months_condensed} months")
    
    def main_menu(self):
        """Display the main menu and handle user interaction."""
        while True:
            print("\nDr. Claude - Therapeutic Journaling")
            print("===================================")
            
            if not self.db:
                password = getpass.getpass("Enter your vault password: ")
                if not self.unlock_vault(password):
                    print("Failed to unlock vault. Incorrect password or database error.")
                    retry = input("Try again? (y/n): ")
                    if retry.lower() not in ['y', 'yes']:
                        return
                    continue
            
            print("\nMain Menu:")
            print("1. Add Journal Entry")
            print("2. View Recent Journal Entries")
            print(f"3. Start Therapy Session {Fore.CYAN}(use /help during session for commands){Style.RESET_ALL}")
            print("4. Update User Profile")
            print("5. View User Profile")
            print("6. View All Therapist Notes")
            print("7. Configure LLM Settings")
            print("8. Condense Old Journal Entries")
            print("9. Exit")
            
            choice = input("\nEnter your choice (1-9): ")
            
            if choice == '1':
                self.add_journal_entry()
            elif choice == '2':
                self.view_journal_entries()
            elif choice == '3':
                self.start_therapy_session()
            elif choice == '4':
                self.update_user_profile()
            elif choice == '5':
                self.view_user_profile()
            elif choice == '6':
                self.view_all_therapist_notes()
            elif choice == '7':
                self.configure_llm()
            elif choice == '8':
                self.condense_old_entries()
            elif choice == '9':
                if self.db:
                    self.db.close()
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
    
    def run(self):
        """Run the application."""
        try:
            self.main_menu()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            if self.db:
                self.db.close()
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            if self.db:
                self.db.close()

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description="Dr. Claude - Therapeutic Journaling with AI")
    parser.add_argument("--data-dir", help="Directory for storing data")
    
    args = parser.parse_args()
    
    app = DrClaude(data_dir=args.data_dir)
    app.run()

if __name__ == "__main__":
    main()