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
    def __init__(self, name: str):
        self.name = name
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel('gemini-1.5-pro')
            self.log_activity("✅ Agent initialized successfully")
        else:
            self.llm = None
            self.log_activity("⚠️ No Gemini API key")

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> AgentResponse:
        pass

    async def _generate_content(self, prompt: str) -> str:
        """Fixed Gemini API call - using asyncio.to_thread"""
        if not self.llm:
            return "Error: Gemini API not available"

        try:
            self.log_activity("🤖 Calling Gemini API in thread...")
            response = await asyncio.to_thread(self.llm.generate_content, prompt)
            self.log_activity("✅ Gemini API call successful")
            return response.text
        except Exception as e:
            error_msg = f"Gemini API error: {str(e)}"
            self.log_activity(f"❌ {error_msg}")
            return error_msg

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
