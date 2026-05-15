# 🌿 بينه - Bayena
### منصة البيانات البيئية الموحدة

---

## 📁 هيكل المشروع

```
bayena/
├── frontend/                  ← صفحات الموقع
│   ├── index.html             ← الصفحة الرئيسية (Landing Page)
│   ├── agent.html             ← الوكيل الذكي (محادثة)
│   ├── dashboard.html         ← لوحة التحليل
│   ├── data-upload.html       ← رفع البيانات
│   └── api.html               ← توثيق الـ API
│
├── backend/                   ← الخادم (FastAPI)
│   ├── main.py                ← الكود الرئيسي
│   ├── voice_client.js        ← كود الصوت للفرونت إيند
│   ├── requirements.txt       ← المكتبات المطلوبة
│   └── README.md              ← توثيق الباك إيند
│
└── README.md                  ← هذا الملف
```

---

## 🚀 تشغيل المشروع

### الفرونت إيند
افتح `frontend/index.html` مباشرة في المتصفح، أو استخدم:
```bash
cd frontend
npx serve .
```

### الباك إيند
```bash
cd backend

# 1. أنشئ ملف البيئة
echo "OPENAI_API_KEY=sk-..." > .env

# 2. ثبّت المكتبات
pip install -r requirements.txt

# 3. شغّل الخادم
uvicorn main:app --reload --port 8000
```

---

## ✨ المحاور الأربعة

| # | المحور | الملف | الوصف |
|---|--------|-------|-------|
| 1 | 🤖 الوكيل الذكي | `agent.html` + `main.py` | محادثة صوتية ونصية مع بيانات البيئة |
| 2 | 📊 لوحة التحليل | `dashboard.html` | تصورات بيانية تفاعلية |
| 3 | ✅ رفع البيانات | `data-upload.html` | رفع والتحقق من جودة البيانات |
| 4 | ⚙️ API | `api.html` + `main.py` | واجهة برمجية للمطورين |

---

## 🔑 المتطلبات

- **OpenAI API Key** — للوكيل + Whisper STT + TTS
- Python 3.10+
- متصفح حديث يدعم MediaRecorder API
