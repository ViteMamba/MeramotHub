# AI Chatbot System — Status

## ✅ Done

- **`POST /chat/bot`** — Accepts user message, returns chatbot reply. Rate-limited to 10 req/min per user.
- **`POST /chat/whatsapp`** — Generates a `wa.me` click-to-chat URL for contacting providers.
- **Rate limiter** — In-memory sliding window (`app/utils/rate_limiter.py`).
- **WhatsApp URL helper** — Normalises BD numbers to international format (`app/utils/whatsapp.py`).
- **Keyword-based fallback** — Placeholder responses for: booking, payment, complaint, provider, greeting queries.

## 📋 Remaining

- [ ] **Real AI integration** — Replace placeholder responses with actual OpenAI/Anthropic API call (keys not yet configured).
- [ ] **Chat history** — Persist conversation history in the database so the bot is context-aware across requests.
- [ ] **Session management** — Track active user sessions with conversation context.
- [ ] **Bengali language support** — Detect and respond in Bangla for local users.
- [ ] **Redis rate limiter** — Move from in-memory to Redis so limits survive server restarts.
- [ ] **Admin analytics** — View chatbot usage stats (top queries, user satisfaction, etc.).
