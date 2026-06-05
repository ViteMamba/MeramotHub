import asyncio
import logging
from typing import Optional
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MeramotHub Assistant — a helpful, friendly service booking assistant for MeramotHub, a local home service platform in Bangladesh.

Your job:
1. Understand the user's problem description
2. Identify the correct service category from this list:
   - electrician (fan, wiring, socket, switch, lights, MCB)
   - plumber (pipe leak, commode, tap, water supply, drainage)
   - ac_mechanic (AC not cooling, AC gas refill, AC cleaning, AC installation)
   - carpenter (door, window, furniture, wood repair)
   - painter (wall paint, waterproofing, surface finishing)
   - welder (gate, grill, iron works)
   - mason (wall crack, cement work, tile fixing)
3. Ask 1-2 short clarifying questions if needed
4. Recommend booking a verified provider on MeramotHub
5. Always end with a clear next step for the user

Rules:
- Keep replies short (3-5 lines max)
- Respond in the same language the user writes in (English or Bangla mix is totally fine)
- Never quote prices yourself — tell them prices are shown on the booking page
- If the question is completely unrelated to home services, politely redirect
- Be warm and helpful, like a knowledgeable neighbor
- Never make up provider names or booking IDs"""

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
    return _client


async def get_chatbot_response(user_message: str, user_name: Optional[str] = None) -> str:
    prefix = f"The user's name is {user_name}. " if user_name else ""
    full_message = f"{prefix}{user_message}"

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_message},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API error: {e}", exc_info=True)
        return "Sorry, I'm having trouble connecting right now. Please try again in a moment."
