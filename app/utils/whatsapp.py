"""
WhatsApp redirect URL helper.
Generates a wa.me link for customers to contact providers directly.
"""
from urllib.parse import quote


def generate_whatsapp_url(phone_number: str, message: str = "") -> str:
    """
    Generate a WhatsApp click-to-chat URL.
    
    Args:
        phone_number: Bangladeshi phone number (e.g. '01712345678' or '+8801712345678')
        message: Optional pre-filled message
    
    Returns:
        WhatsApp URL string (e.g. 'https://wa.me/8801712345678?text=...')
    """
    # Normalize to international format without + sign
    cleaned = phone_number.strip().replace(" ", "").replace("-", "")
    if cleaned.startswith("0"):
        cleaned = "88" + cleaned  # Convert 01... to 8801...
    elif cleaned.startswith("+"):
        cleaned = cleaned[1:]  # Remove leading +
    
    url = f"https://wa.me/{cleaned}"
    if message:
        url += f"?text={quote(message)}"
    
    return url
