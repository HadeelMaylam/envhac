"""
Bayena Voice Backend
====================
POST /api/voice/chat   ← صوت المستخدم → نص → رد الوكيل → صوت
POST /api/voice/stt    ← صوت فقط → نص (Whisper)
POST /api/voice/tts    ← نص فقط → صوت (OpenAI TTS)
GET  /api/health       ← فحص الخادم
"""

import os
import io
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

app = FastAPI(
    title="Bayena Voice API",
    description="واجهة برمجية للمحادثة الصوتية مع وكيل بينه",
    version="1.0.0",
)

# ─── CORS ─── السماح للفرونت إيند بالتواصل مع الباك إيند
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج: ضع دومين موقعك فقط
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── OpenAI Client ───
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── System Prompt للوكيل ───
AGENT_SYSTEM_PROMPT = """
أنت وكيل بينه الذكي، مساعد متخصص في البيانات البيئية في المملكة العربية السعودية.
تعمل لصالح منصة بينه التي تجمع بيانات صندوق البيئة وتحللها.

مهماتك:
- الإجابة على أسئلة جودة الهواء، المياه، الانبعاثات، ودرجات الحرارة
- تقديم إحصائيات وتقارير من قاعدة بيانات بينه
- المساعدة في تفسير البيانات البيئية

قواعد:
- تكلم بالعربية دائماً
- ردودك موجزة وواضحة (2-4 جمل)
- إذا سُئلت عن بيانات محددة غير متوفرة، اعتذر بأدب واقترح بديلاً
"""

# ─── تخزين سياق المحادثة في الذاكرة (يمكن استبداله بـ Redis لاحقاً) ───
conversation_history: dict[str, list] = {}


# ══════════════════════════════════════════
#  1. المسار الرئيسي: صوت → نص → رد → صوت
# ══════════════════════════════════════════
@app.post(
    "/api/voice/chat",
    summary="محادثة صوتية كاملة",
    response_description="ملف صوتي MP3 برد الوكيل",
)
async def voice_chat(
    audio: UploadFile = File(..., description="ملف صوت المستخدم (webm/mp3/wav/m4a)"),
    session_id: str = Form(default="default", description="معرّف الجلسة للحفاظ على السياق"),
):
    """
    الخطوات:
    1. استقبال الصوت
    2. Whisper → تحويله نصاً
    3. GPT-4o → رد الوكيل
    4. OpenAI TTS → تحويل الرد صوتاً
    5. إرجاع الصوت للفرونت إيند
    """
    # ── خطوة 1: قراءة الملف ──
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="الملف الصوتي فارغ")

    # ── خطوة 2: Speech-to-Text عبر Whisper ──
    user_text = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")

    if not user_text.strip():
        raise HTTPException(status_code=422, detail="لم يتم التعرف على كلام في التسجيل")

    # ── خطوة 3: رد الوكيل عبر GPT ──
    agent_reply = await get_agent_reply(session_id, user_text)

    # ── خطوة 4: Text-to-Speech ──
    audio_stream = await synthesize_speech(agent_reply)

    # ── خطوة 5: إرجاع الصوت + النص في الهيدر ──
    headers = {
        "X-User-Text": user_text[:200],       # النص اللي قاله المستخدم
        "X-Agent-Reply": agent_reply[:500],    # رد الوكيل (نص)
        "Access-Control-Expose-Headers": "X-User-Text, X-Agent-Reply",
    }

    return StreamingResponse(
        io.BytesIO(audio_stream),
        media_type="audio/mpeg",
        headers=headers,
    )


# ══════════════════════════════════════════
#  2. Speech-to-Text فقط
# ══════════════════════════════════════════
@app.post("/api/voice/stt", summary="تحويل صوت إلى نص")
async def speech_to_text(
    audio: UploadFile = File(...),
):
    audio_bytes = await audio.read()
    text = await transcribe_audio(audio_bytes, audio.filename or "audio.webm")
    return JSONResponse({"text": text})


# ══════════════════════════════════════════
#  3. Text-to-Speech فقط
# ══════════════════════════════════════════
class TTSRequest(BaseModel):
    text: str
    voice: str = "nova"  # alloy | echo | fable | onyx | nova | shimmer


@app.post("/api/voice/tts", summary="تحويل نص إلى صوت")
async def text_to_speech(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="النص فارغ")

    audio_bytes = await synthesize_speech(req.text, voice=req.voice)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")


# ══════════════════════════════════════════
#  4. Chat نصي (بدون صوت) - للاختبار
# ══════════════════════════════════════════
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


@app.post("/api/chat", summary="محادثة نصية مع الوكيل")
async def text_chat(req: ChatRequest):
    reply = await get_agent_reply(req.session_id, req.message)
    return JSONResponse({"reply": reply, "session_id": req.session_id})


# ══════════════════════════════════════════
#  5. مسح سياق الجلسة
# ══════════════════════════════════════════
@app.delete("/api/session/{session_id}", summary="مسح تاريخ المحادثة")
async def clear_session(session_id: str):
    if session_id in conversation_history:
        del conversation_history[session_id]
    return JSONResponse({"message": f"تم مسح جلسة {session_id}"})


# ══════════════════════════════════════════
#  6. فحص الصحة
# ══════════════════════════════════════════
@app.get("/api/health", summary="فحص حالة الخادم")
async def health():
    return JSONResponse({
        "status": "ok",
        "service": "Bayena Voice API",
        "version": "1.0.0",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    })


# ══════════════════════════════════════════
#  دوال مساعدة
# ══════════════════════════════════════════

async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """Whisper STT - يحوّل الصوت إلى نص"""
    try:
        # Whisper يحتاج file-like object باسم صحيح
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        transcription = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ar",  # عربي بشكل افتراضي
        )
        return transcription.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تحويل الصوت: {str(e)}")


async def get_agent_reply(session_id: str, user_message: str) -> str:
    """GPT-4o - يرد على المستخدم مع الحفاظ على سياق المحادثة"""
    # تهيئة سياق الجلسة إن لم يكن موجوداً
    if session_id not in conversation_history:
        conversation_history[session_id] = []

    # إضافة رسالة المستخدم للتاريخ
    conversation_history[session_id].append({
        "role": "user",
        "content": user_message,
    })

    # الحفاظ على آخر 10 رسائل فقط لتجنب تجاوز الـ context window
    recent_history = conversation_history[session_id][-10:]

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                *recent_history,
            ],
            max_tokens=300,
            temperature=0.7,
        )

        reply = response.choices[0].message.content

        # إضافة رد الوكيل للتاريخ
        conversation_history[session_id].append({
            "role": "assistant",
            "content": reply,
        })

        return reply

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في الوكيل: {str(e)}")


async def synthesize_speech(text: str, voice: str = "nova") -> bytes:
    """OpenAI TTS - يحوّل النص إلى صوت MP3"""
    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice,       # nova = صوت نسائي ناعم
            input=text,
            response_format="mp3",
            speed=1.0,
        )
        return response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في تحويل النص لصوت: {str(e)}")


# ── تشغيل محلي ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
