import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import google.generativeai as genai
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AgentResponse:
    success: bool
    data: Dict[Any, Any]
    message: str
    agent_name: str
    timestamp: str

class BaseAgent(ABC):
    def __init__(self, name: str, llm_instance=None):
        self.name = name
        self.llm = llm_instance
        self.log_activity("✅ Agent initialized.")

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        pass

    async def _generate_content(self, prompt: str) -> str:
        """Uses the provided LLM instance to generate content."""
        if not self.llm:
            self.log_activity("❌ LLM instance not provided to agent.")
            raise ValueError("LLM instance is not available in the agent.")

        try:
            self.log_activity("🤖 Calling Gemini API in thread...")
            response = await asyncio.to_thread(self.llm.generate_content, prompt)
            self.log_activity("✅ Gemini API call successful")
            return response.text
        except Exception as e:
            error_msg = f"Gemini API error: {str(e)}"
            self.log_activity(f"❌ {error_msg}")
            # Re-raise the exception to be handled by the calling agent's try-except block
            raise e

    def log_activity(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.name}] {message}")

    def create_response(self, success: bool, data: Dict[Any, Any], message: str) -> AgentResponse:
        return AgentResponse(
            success=success,
            data=data,
            message=message,
            agent_name=self.name,
            timestamp=datetime.now().isoformat()
        )
