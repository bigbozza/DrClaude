"""LLM integration for Dr. Claude application."""

import json
from typing import Dict, List, Optional, Any
import os
import datetime
import anthropic
import openai
from enum import Enum
import ollama

class ModelProvider(Enum):
    """Available LLM providers."""
    ANTHROPIC = "Anthropic"
    OPENAI = "OpenAI"
    OLLAMA = "Ollama"

class ModelConfig:
    """Configuration for LLM models."""
    
    def __init__(self, provider: ModelProvider, model_name: str, api_key: Optional[str] = None):
        """Initialize model configuration."""
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key
        
        if provider != ModelProvider.OLLAMA and not api_key:
            raise ValueError(f"API key is required for {provider.value} models")
    
    @staticmethod
    def get_available_models(provider: ModelProvider, api_key: Optional[str] = None) -> List[str]:
        """Get available models for the specified provider."""
        if provider == ModelProvider.ANTHROPIC:
            return ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3.5-sonnet-20240620", "claude-3-7-sonnet-20250219"]
        elif provider == ModelProvider.OPENAI:
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"]
        elif provider == ModelProvider.OLLAMA:
            try:
                # Try to get available models from Ollama
                models = ollama.list()
                return [model["name"] for model in models["models"]]
            except Exception:
                # Return some default Ollama models
                return ["llama2", "mistral", "gemma", "llama3"]
        return []

class TherapistLLM:
    """LLM-based therapist for Dr. Claude application."""
    
    # System prompts for different therapeutic approaches
    APPROACH_PROMPTS = {
        "Freudian": """You are a Freudian psychoanalyst therapist. Focus on unconscious processes, 
        dream analysis, and childhood experiences. Use concepts like id, ego, superego, defense mechanisms, 
        and psychosexual development. Interpret statements in terms of repressed desires and conflicts. 
        Look for patterns related to early childhood development and parental relationships.""",
        
        "Jungian": """You are a Jungian analytical psychologist therapist. Focus on archetypes, 
        the collective unconscious, and the process of individuation. Look for symbolic content and meaning 
        in dreams and experiences. Use concepts like shadow, anima/animus, persona, and the Self. 
        Help the person integrate unconscious contents to achieve wholeness.""",
        
        "Cognitive Behavioral Therapy": """You are a CBT therapist. Focus on identifying and changing 
        unhelpful thinking patterns and behaviors. Use techniques like cognitive restructuring, behavioral 
        activation, and exposure. Look for cognitive distortions like catastrophizing, black-and-white thinking, 
        and overgeneralization. Help develop more balanced thoughts and adaptive behaviors.""",
        
        "Humanistic": """You are a humanistic therapist. Focus on the person's innate capacity for growth 
        and self-actualization. Create a warm, empathetic, and non-judgmental environment. Use reflective 
        listening and unconditional positive regard. Encourage authentic expression and help the person discover 
        their own solutions and meaning.""",
        
        "Existential": """You are an existential therapist. Focus on questions of existence, meaning, freedom, 
        and responsibility. Help the person confront existential givens like mortality, isolation, freedom, 
        and meaninglessness. Explore how they create meaning in their lives and take responsibility for their choices.""",
        
        "Psychodynamic": """You are a psychodynamic therapist. Focus on unconscious processes, past experiences, 
        and their impact on current behavior. Explore patterns in relationships and emotional responses. 
        Use concepts like transference, attachment styles, and defense mechanisms. Help the person gain insight 
        into recurring patterns and develop new ways of relating."""
    }
    
    def __init__(self, config: ModelConfig):
        """Initialize LLM therapist with specified configuration."""
        self.config = config
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize appropriate client based on provider."""
        if self.config.provider == ModelProvider.ANTHROPIC:
            return anthropic.Anthropic(api_key=self.config.api_key)
        elif self.config.provider == ModelProvider.OPENAI:
            return openai.OpenAI(api_key=self.config.api_key)
        elif self.config.provider == ModelProvider.OLLAMA:
            return None  # Ollama uses direct function calls, no client object needed
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def _build_prompt(self, 
                    approach: str, 
                    user_profile: Dict[str, Any], 
                    journal_entries: List[Dict[str, Any]], 
                    therapist_notes: List[Dict[str, Any]],
                    current_query: str) -> Dict[str, Any]:
        """Build prompt for the therapy session based on approach and available data."""
        
        # Get the appropriate system prompt for the selected approach
        system_prompt = self.APPROACH_PROMPTS.get(approach, self.APPROACH_PROMPTS["Cognitive Behavioral Therapy"])
        
        # Add specific instructions for the AI therapist
        system_prompt += """\n\nAs an AI therapist:
        1. Maintain strict confidentiality and ethical standards
        2. Do not give prescriptive medical advice
        3. Recognize when issues might require referral to a human professional
        4. Provide supportive, non-judgmental responses
        5. Ask clarifying questions when needed
        6. Focus on helping the person develop insights and coping strategies
        7. Maintain appropriate therapeutic boundaries
        8. Your goal is to help the person understand themselves better and make positive changes
        9. IMPORTANT: Do not say "thank you" after every response or greet the user repeatedly during a session.
           Only use appropriate greetings at the beginning of a session and closing remarks at the end.
           Focus on providing substantive therapeutic responses without unnecessary pleasantries.

        After each session, you should generate clinical notes that include:
        1. Key themes and topics discussed
        2. Observed patterns, behaviors, or thinking styles
        3. Therapeutic strategies used and their effectiveness
        4. Progress toward stated goals
        5. Areas for future exploration
        6. Any risk factors or concerns
        
        These notes will be used to maintain continuity between sessions."""
        
        # Compile user profile information
        profile_text = "USER PROFILE:\n"
        if user_profile:
            for key, value in user_profile.items():
                profile_text += f"{key}: {value}\n"
        else:
            profile_text += "No profile information available yet.\n"
        
        # Compile therapist notes
        notes_text = "PREVIOUS THERAPY NOTES:\n"
        if therapist_notes:
            for note in therapist_notes[:5]:  # Limit to most recent 5 notes to manage context
                notes_text += f"Date: {note['date']}\n{note['note']}\n\n"
        else:
            notes_text += "No previous therapy notes available.\n"
        
        # Compile journal entries
        journal_text = "RECENT JOURNAL ENTRIES:\n"
        if journal_entries:
            for entry in journal_entries[:10]:  # Limit to most recent 10 entries to manage context
                journal_text += f"Date: {entry['date']}\n{entry['entry']}\n\n"
        else:
            journal_text += "No journal entries available.\n"
        
        # Combine all context
        context = f"{profile_text}\n\n{notes_text}\n\n{journal_text}"
        
        # Create the appropriate message structure based on the provider
        if self.config.provider == ModelProvider.ANTHROPIC:
            return {
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER QUERY: {current_query}"}
                ]
            }
        
        elif self.config.provider == ModelProvider.OPENAI:
            return {
                "system": system_prompt,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"CONTEXT:\n{context}\n\nUSER QUERY: {current_query}"}
                ]
            }
        
        elif self.config.provider == ModelProvider.OLLAMA:
            return {
                "system": system_prompt,
                "prompt": f"CONTEXT:\n{context}\n\nUSER QUERY: {current_query}"
            }
        
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    def _clean_response(self, response_text: str) -> str:
        """Clean the response by removing redundant greetings and thank yous."""
        import re
        
        # Remove common greeting patterns at the beginning of responses
        patterns = [
            r'^(Hello|Hi|Hey|Greetings|Good morning|Good afternoon|Good evening)[,\.\s!]*\s*',
            r'^Thank you.*?for (sharing|your|this).*?\.\s*',
            r'^I appreciate.*?(sharing|your message|your thoughts).*?\.\s*',
            r'(Thank you|Thanks)(\s|\.|,|!)*$',
        ]
        
        cleaned = response_text
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove excess whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def generate_response(self, 
                        approach: str, 
                        user_profile: Dict[str, Any], 
                        journal_entries: List[Dict[str, Any]], 
                        therapist_notes: List[Dict[str, Any]],
                        current_query: str) -> Dict[str, str]:
        """Generate a therapeutic response based on the approach and available data."""
        
        prompt_data = self._build_prompt(
            approach, user_profile, journal_entries, therapist_notes, current_query
        )
        
        try:
            if self.config.provider == ModelProvider.ANTHROPIC:
                response = self.client.messages.create(
                    model=self.config.model_name,
                    system=prompt_data["system"],
                    messages=prompt_data["messages"],
                    max_tokens=4000
                )
                response_text = self._clean_response(response.content[0].text)
                return {
                    "response": response_text,
                    "model": self.config.model_name,
                    "provider": self.config.provider.value
                }
            
            elif self.config.provider == ModelProvider.OPENAI:
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": prompt_data["system"]},
                        {"role": "user", "content": prompt_data["messages"][0]["content"]}
                    ],
                    max_tokens=4000
                )
                response_text = self._clean_response(response.choices[0].message.content)
                return {
                    "response": response_text,
                    "model": self.config.model_name,
                    "provider": self.config.provider.value
                }
            
            elif self.config.provider == ModelProvider.OLLAMA:
                response = ollama.chat(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": prompt_data["system"]},
                        {"role": "user", "content": prompt_data["prompt"]}
                    ]
                )
                response_text = self._clean_response(response["message"]["content"])
                return {
                    "response": response_text,
                    "model": self.config.model_name,
                    "provider": self.config.provider.value
                }
            
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
        
        except Exception as e:
            return {
                "response": f"Error generating response: {str(e)}",
                "error": str(e),
                "model": self.config.model_name,
                "provider": self.config.provider.value
            }
    
    def generate_therapist_notes(self, 
                              approach: str, 
                              user_profile: Dict[str, Any], 
                              journal_entries: List[Dict[str, Any]], 
                              therapist_notes: List[Dict[str, Any]],
                              session_transcript: str) -> str:
        """Generate therapist notes based on the session transcript."""
        
        system_prompt = f"""You are an experienced {approach} therapist. 
        Generate clinical notes for the following therapy session.
        Focus on key themes, patterns, progress, and areas for future exploration.
        Be concise, professional, and objective.
        Do not include unnecessary pleasantries or formalities in your notes."""
        
        user_prompt = f"""CONTEXT:
        User Profile: {json.dumps(user_profile, indent=2)}
        
        Previous Notes: {json.dumps(therapist_notes[:3] if therapist_notes else [], indent=2)}
        
        SESSION TRANSCRIPT:
        {session_transcript}
        
        Based on this session, generate comprehensive clinical notes that include:
        1. Key themes and topics discussed
        2. Observed patterns, behaviors, or thinking styles
        3. Progress toward stated goals
        4. Areas for future exploration
        5. Any risk factors or concerns
        
        Format your notes professionally in a clear structure."""
        
        try:
            if self.config.provider == ModelProvider.ANTHROPIC:
                response = self.client.messages.create(
                    model=self.config.model_name,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=2000
                )
                return self._clean_response(response.content[0].text)
            
            elif self.config.provider == ModelProvider.OPENAI:
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2000
                )
                return self._clean_response(response.choices[0].message.content)
            
            elif self.config.provider == ModelProvider.OLLAMA:
                response = ollama.chat(
                    model=self.config.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return self._clean_response(response["message"]["content"])
            
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
        
        except Exception as e:
            return f"Error generating therapist notes: {str(e)}"