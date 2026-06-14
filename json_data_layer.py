import os
import json
from typing import Dict, List, Optional
from datetime import datetime

from chainlit.data.base import BaseDataLayer
from chainlit.types import (
    Feedback,
    PaginatedResponse,
    Pagination,
    ThreadDict,
    ThreadFilter,
)
from chainlit.element import Element, ElementDict
from chainlit.step import StepDict
from chainlit.user import PersistedUser, User

DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), ".chainlit_history"))

class JsonDataLayer(BaseDataLayer):
    """Custom Data Layer to store Chainlit chat threads locally as JSON files."""
    
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "threads"), exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, "users"), exist_ok=True)

    # --- Users ---
    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        # Return a dummy persisted user so Chainlit considers the user logged in
        return PersistedUser(id=identifier, identifier=identifier, createdAt=datetime.utcnow().isoformat())

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        return PersistedUser(id=user.identifier, identifier=user.identifier, createdAt=datetime.utcnow().isoformat())

    # --- Feedback ---
    async def upsert_feedback(self, feedback: Feedback) -> str:
        return feedback.id or "feedback_id"

    async def delete_feedback(self, feedback_id: str) -> bool:
        return True

    # --- Elements ---
    async def create_element(self, element: Element):
        pass

    async def get_element(self, thread_id: str, element_id: str) -> Optional[ElementDict]:
        return None

    async def delete_element(self, element_id: str, thread_id: Optional[str] = None):
        pass

    # --- Steps ---
    async def create_step(self, step_dict: StepDict):
        # Steps are part of a thread. We will load the thread, append the step, and save.
        thread_id = step_dict.get("threadId")
        if not thread_id:
            return
        thread = await self.get_thread(thread_id)
        if thread:
            # Avoid duplicates
            existing = [s for s in thread.get("steps", []) if s.get("id") == step_dict["id"]]
            if not existing:
                thread["steps"].append(step_dict)
                await self._save_thread(thread_id, thread)

    async def update_step(self, step_dict: StepDict):
        thread_id = step_dict.get("threadId")
        if not thread_id:
            return
        thread = await self.get_thread(thread_id)
        if thread:
            for i, step in enumerate(thread.get("steps", [])):
                if step.get("id") == step_dict["id"]:
                    thread["steps"][i] = step_dict
                    break
            await self._save_thread(thread_id, thread)

    async def delete_step(self, step_id: str):
        pass

    # --- Threads ---
    async def get_thread_author(self, thread_id: str) -> str:
        thread = await self.get_thread(thread_id)
        return thread.get("userIdentifier", "") if thread else ""

    async def _save_thread(self, thread_id: str, thread_dict: ThreadDict):
        path = os.path.join(DATA_DIR, "threads", f"{thread_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(thread_dict, f, default=str)

    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        path = os.path.join(DATA_DIR, "threads", f"{thread_id}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return None
        # Auto-create empty thread if requested but doesn't exist
        empty_thread: ThreadDict = {
            "id": thread_id,
            "createdAt": datetime.utcnow().isoformat(),
            "name": "New Chat",
            "userId": "local_user",
            "userIdentifier": "local_user",
            "tags": [],
            "metadata": {},
            "steps": [],
            "elements": []
        }
        await self._save_thread(thread_id, empty_thread)
        return empty_thread

    async def update_thread(self, thread_id: str, name: Optional[str] = None, user_id: Optional[str] = None, metadata: Optional[Dict] = None, tags: Optional[List[str]] = None):
        thread = await self.get_thread(thread_id)
        if thread:
            if name is not None:
                thread["name"] = name
            if user_id is not None:
                thread["userId"] = user_id
                thread["userIdentifier"] = user_id
            if metadata is not None:
                thread["metadata"] = metadata
            if tags is not None:
                thread["tags"] = tags
            await self._save_thread(thread_id, thread)

    async def delete_thread(self, thread_id: str):
        path = os.path.join(DATA_DIR, "threads", f"{thread_id}.json")
        if os.path.exists(path):
            os.remove(path)

    async def list_threads(self, pagination: Pagination, filters: ThreadFilter) -> PaginatedResponse[ThreadDict]:
        threads = []
        threads_dir = os.path.join(DATA_DIR, "threads")
        for filename in os.listdir(threads_dir):
            if filename.endswith(".json"):
                path = os.path.join(threads_dir, filename)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        threads.append(data)
                except:
                    continue
                    
        # Sort by createdAt descending
        threads.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        
        return PaginatedResponse(
            data=threads,
            pageInfo={
                "hasNextPage": False,
                "endCursor": None
            }
        )

    async def build_debug_url(self) -> str:
        return ""
