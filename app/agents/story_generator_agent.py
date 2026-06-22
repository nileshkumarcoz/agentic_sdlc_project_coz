"""StoryGeneratorAgent — generates user stories from requirement documents.

Minimal proof-of-concept implementing Story 109061.
Supports TXT and MD files; PDF/DOCX stubs are present for extension.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage


@dataclass
class UserStory:
    title: str
    description: str  # "As a <role>, I want <goal>, so that <benefit>"
    acceptance_criteria: List[str] = field(default_factory=list)
    priority: str = "Medium"
    points: int = 3


class DocumentParserTool:
    """Extracts raw text from a file path or raw bytes."""

    SUPPORTED = {".txt", ".md"}

    def parse(self, content: str | bytes, filename: str = "file.txt") -> str:
        """Return extracted text.  For the PoC only TXT/MD are fully handled."""
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".txt"
        if ext not in self.SUPPORTED:
            raise ValueError(
                f"Unsupported file type '{ext}'. Supported: {self.SUPPORTED}"
            )
        return content.strip()


class StoryGeneratorAgent:
    """Orchestrates document parsing → user-story generation via an LLM."""

    SYSTEM_PROMPT = (
        "You are a senior product owner. "
        "Given a requirements document, extract user stories. "
        "Return ONLY a JSON array where each element has the keys: "
        "'title', 'description' (As a … I want … so that …), "
        "'acceptance_criteria' (list of strings), 'priority' (High/Medium/Low), "
        "'points' (Fibonacci integer 1-13). "
        "Do NOT include markdown fences or any extra text."
    )

    def __init__(self, llm: ChatOpenAI | None = None, model: str = "gpt-4o-mini"):
        self.llm = llm or ChatOpenAI(
            model=model,
            temperature=0.2,
        )
        self.parser = DocumentParserTool()

    def run(self, content: str | bytes, filename: str = "requirements.txt") -> List[UserStory]:
        """Parse document and return a list of UserStory objects."""
        raw_text = self.parser.parse(content, filename)
        stories_json = self._call_llm(raw_text)
        return self._parse_response(stories_json)

    def _call_llm(self, text: str) -> str:
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=f"Requirements Document:\n\n{text}"),
        ]
        response = self.llm(messages)
        return response.content

    def _parse_response(self, raw: str) -> List[UserStory]:
        import json

        # Strip accidental markdown fences
        cleaned = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip())
        data = json.loads(cleaned)
        stories: List[UserStory] = []
        for item in data:
            stories.append(
                UserStory(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    acceptance_criteria=item.get("acceptance_criteria", []),
                    priority=item.get("priority", "Medium"),
                    points=int(item.get("points", 3)),
                )
            )
        return stories
