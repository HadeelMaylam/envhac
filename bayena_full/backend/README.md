# 🌿 Bayena Voice Backend

باك إيند محادثة صوتية كاملة لوكيل بينه.

## كيف يشتغل؟

```
المستخدم يتكلم
      ↓
  [Whisper STT]  →  نص عربي
      ↓
  [GPT-4o]       →  رد الوكيل
      ↓
  [OpenAI TTS]   →  صوت MP3
      ↓
  الفرونت إيند يشغّل الصوت
```

## التثبيت

```bash
# 1. نسخ ملف البيئة
cp .env.example .env

# 2. أضف مفتاح OpenAI في .env
OPENAI_API_KEY=sk-...

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. تشغيل الخادم
uvicorn main:app --reload --port 8000
```

## المسارات (Endpoints)

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/api/voice/chat` | **الرئيسي** - صوت → رد صوتي |
| `POST` | `/api/voice/stt` | صوت → نص فقط |
| `POST` | `/api/voice/tts` | نص → صوت فقط |
| `POST` | `/api/chat` | محادثة نصية (للاختبار) |
| `DELETE` | `/api/session/{id}` | مسح تاريخ المحادثة |
| `GET` | `/api/health` | فحص الخادم |

## استخدام من الفرونت إيند (JavaScript)

```javascript
// تسجيل صوت المستخدم وإرساله
async function sendVoiceMessage(audioBlob, sessionId = "user-123") {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");
  formData.append("session_id", sessionId);

  const res = await fetch("http://localhost:8000/api/voice/chat", {
    method: "POST",
    body: formData,
  });

  // النص في الهيدر
  const userText   = res.headers.get("X-User-Text");
  const agentReply = res.headers.get("X-Agent-Reply");

  // تشغيل الصوت
  const audioBlob2 = await res.blob();
  const audioUrl   = URL.createObjectURL(audioBlob2);
  new Audio(audioUrl).play();

  return { userText, agentReply };
}
```

## الأصوات المتاحة (TTS)

| الصوت | النوع |
|-------|-------|
| `nova` | نسائي - ناعم (افتراضي) |
| `alloy` | محايد |
| `echo` | ذكوري - هادئ |
| `onyx` | ذكوري - عميق |
| `shimmer` | نسائي - واضح |

## الملاحظات

- سياق المحادثة محفوظ في الذاكرة (يُمسح عند إعادة تشغيل الخادم)
- لحفظ دائم: استبدل `conversation_history` بـ Redis أو قاعدة بيانات
- Whisper مضبوط على العربية `language="ar"` - تقدرين تحذفينه للكشف التلقائي
