# Dr. Claude - Therapeutic Journaling with AI

Dr. Claude is a privacy-focused therapeutic journaling application that integrates with large language models (LLMs) to provide AI-assisted therapy sessions. All your data is stored locally and encrypted for maximum privacy.

## Features

- **Daily Journaling**: Record your thoughts, feelings, and experiences in a private digital journal
- **AI-Assisted Therapy**: Have therapeutic conversations with an AI that adapts to your needs
- **Multiple Therapeutic Approaches**: Choose from Freudian, Jungian, CBT, Humanistic, Existential, or Psychodynamic frameworks
- **Private and Secure**: All data is stored locally and encrypted with a vault password
- **Intelligent Context Management**: The app condenses older entries to maintain a balance between historical context and recency
- **Comprehensive User Profile**: Optionally provide background information to improve the therapeutic experience

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/dr-claude.git
   cd dr-claude
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python src/main.py
   ```

## API Keys

Dr. Claude supports the following LLM providers:

- **Anthropic Claude** (default): Requires an Anthropic API key
- **OpenAI**: Requires an OpenAI API key
- **Ollama**: No API key required, but needs Ollama running locally

You will be prompted to enter your API key when configuring the application.

## Usage

1. When you first run the application, you'll be asked to create a vault password.
2. After setting up, you can:
   - Add journal entries
   - Start therapy sessions
   - Update your user profile
   - Configure LLM settings
   - View past journal entries
   - View or update your profile

## Privacy and Security

- All your data is stored locally on your device
- The database is encrypted with your vault password
- No data is sent to external servers except during therapy sessions with remote LLMs
- Only the current session content is sent to the LLM, not your entire history

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

Dr. Claude is not a replacement for professional mental health services. If you are experiencing severe mental health issues, please consult with a qualified healthcare provider.