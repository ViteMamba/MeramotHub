"""
AI Chatbot service — placeholder integration for OpenAI/Anthropic.
Replace the placeholder logic with real API calls when keys are available.
"""
from typing import Optional


async def get_chatbot_response(user_message: str, user_name: Optional[str] = None) -> str:
    """
    Generate a chatbot response.
    
    TODO: Replace with actual OpenAI/Anthropic API call:
        import openai
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful MeramotHub customer support assistant..."},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    """
    greeting = f"Hi {user_name}! " if user_name else "Hi! "
    
    # Simple keyword-based placeholder responses
    msg_lower = user_message.lower()
    
    if any(word in msg_lower for word in ["book", "service", "hire"]):
        return f"{greeting}To book a service, go to our services page, pick a category, and create a booking. A provider will accept it shortly!"
    
    elif any(word in msg_lower for word in ["payment", "pay", "cost", "price"]):
        return f"{greeting}Payments are held in escrow until your service is completed. You can pay via bKash, Nagad, or other MFS options."
    
    elif any(word in msg_lower for word in ["complaint", "problem", "issue", "refund"]):
        return f"{greeting}Sorry to hear about the issue. You can file a complaint from your booking page, and our area manager will investigate within 24 hours."
    
    elif any(word in msg_lower for word in ["provider", "mechanic", "electrician", "plumber"]):
        return f"{greeting}All our providers are NID-verified and rated by customers. You can search nearby providers or filter by skill category."
    
    elif any(word in msg_lower for word in ["hello", "hi", "hey", "salam", "assalamu"]):
        return f"{greeting}Welcome to MeramotHub! 🛠️ How can I help you today? You can ask about bookings, payments, services, or complaints."
    
    else:
        return f"{greeting}Thanks for reaching out! I'm the MeramotHub assistant. I can help with bookings, payments, providers, and complaints. What do you need?"
