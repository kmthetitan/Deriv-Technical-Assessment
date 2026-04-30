import os
import json
import hashlib
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set in .env file")
        
        genai.configure(api_key=self.api_key)
        self.model = "gemini-3.1-flash-lite-preview"
        self.client = genai.GenerativeModel(self.model)
        self.llm_calls = []

    def call_llm(self, prompt: str, stage: str, query_id: Optional[str] = None,
                 input_artifacts: Optional[list] = None, output_artifact: Optional[str] = None) -> str:
        """Make an LLM call via Google Generative AI API and log it."""
        try:
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=4000,
                    temperature=0.7
                )
            )
            
            result = response.text
            
            # Log the call
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            call_record = {
                "stage": stage,
                "query_id": query_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "provider": "google",
                "model": self.model,
                "prompt_hash": prompt_hash,
                "input_artifacts": input_artifacts or [],
                "output_artifact": output_artifact
            }
            self.llm_calls.append(call_record)
            
            return result
        except Exception as e:
            raise RuntimeError(f"Google Generative AI API call failed at stage {stage}: {str(e)}")

    def save_llm_log(self, filepath: str):
        """Save LLM call log to JSONL file."""
        with open(filepath, 'w') as f:
            for call in self.llm_calls:
                f.write(json.dumps(call) + '\n')

    def get_call_count(self) -> int:
        """Get total number of LLM calls made."""
        return len(self.llm_calls)
