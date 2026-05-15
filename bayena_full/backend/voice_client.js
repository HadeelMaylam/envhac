/**
 * Bayena Voice Client
 * يُضاف للفرونت إيند لتشغيل المحادثة الصوتية مع الباك إيند
 */

const BACKEND_URL = "http://localhost:8000"; // غيّريه لرابط السيرفر عند النشر

class BayenaVoiceClient {
  constructor(sessionId = null) {
    this.sessionId    = sessionId || "session-" + Date.now();
    this.mediaRecorder = null;
    this.audioChunks  = [];
    this.isRecording  = false;
    this.isProcessing = false;
  }

  // ── بدء التسجيل ──
  async startRecording() {
    if (this.isRecording || this.isProcessing) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioChunks  = [];
    this.mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    };

    this.mediaRecorder.start();
    this.isRecording = true;
    console.log("🎙️ بدأ التسجيل...");
  }

  // ── إيقاف التسجيل وإرسال الصوت ──
  async stopAndSend(onResult) {
    if (!this.isRecording) return;

    return new Promise((resolve) => {
      this.mediaRecorder.onstop = async () => {
        this.isRecording  = false;
        this.isProcessing = true;

        const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
        console.log("📤 إرسال الصوت...");

        try {
          const result = await this._sendToBackend(audioBlob);
          onResult?.(result);
          resolve(result);
        } catch (err) {
          console.error("❌ خطأ:", err);
          resolve(null);
        } finally {
          this.isProcessing = false;
          // إيقاف الميكروفون
          this.mediaRecorder.stream.getTracks().forEach(t => t.stop());
        }
      };

      this.mediaRecorder.stop();
    });
  }

  // ── الإرسال للباك إيند ──
  async _sendToBackend(audioBlob) {
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");
    formData.append("session_id", this.sessionId);

    const res = await fetch(`${BACKEND_URL}/api/voice/chat`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "خطأ في الخادم");
    }

    // النصوص من الهيدر
    const userText   = decodeURIComponent(res.headers.get("X-User-Text")   || "");
    const agentReply = decodeURIComponent(res.headers.get("X-Agent-Reply") || "");

    // تشغيل الصوت
    const blob    = await res.blob();
    const audioUrl = URL.createObjectURL(blob);
    const audio   = new Audio(audioUrl);
    await audio.play();

    console.log("👤 المستخدم:", userText);
    console.log("🤖 الوكيل:", agentReply);

    return { userText, agentReply };
  }

  // ── مسح تاريخ المحادثة ──
  async clearHistory() {
    await fetch(`${BACKEND_URL}/api/session/${this.sessionId}`, {
      method: "DELETE",
    });
    console.log("🗑️ تم مسح تاريخ المحادثة");
  }
}


// ══════════════════════════════════════════
//  مثال الاستخدام مع زر في الـ HTML
// ══════════════════════════════════════════

const voiceClient = new BayenaVoiceClient();
let   holding     = false;

// زر الميكروفون - اضغط واحتفظ للتحدث
document.addEventListener("DOMContentLoaded", () => {
  const micBtn       = document.getElementById("micButton");
  const statusText   = document.getElementById("statusText");
  const chatMessages = document.getElementById("chatMessages");

  if (!micBtn) return; // إذا لم يكن الزر موجوداً في الصفحة

  // ─── اضغط للتحدث ───
  micBtn.addEventListener("mousedown",  startVoice);
  micBtn.addEventListener("touchstart", startVoice, { passive: true });

  // ─── ارفع للإرسال ───
  micBtn.addEventListener("mouseup",  stopVoice);
  micBtn.addEventListener("touchend", stopVoice);
  document.addEventListener("mouseup", () => { if (holding) stopVoice(); });

  async function startVoice() {
    if (holding) return;
    holding = true;
    micBtn.classList.add("recording");
    statusText.textContent = "🎙️ جاري التسجيل... ارفع للإرسال";
    await voiceClient.startRecording();
  }

  async function stopVoice() {
    if (!holding) return;
    holding = false;
    micBtn.classList.remove("recording");
    statusText.textContent = "⏳ جاري المعالجة...";

    await voiceClient.stopAndSend(({ userText, agentReply }) => {
      // إضافة الرسائل للمحادثة
      appendMessage("user",  userText);
      appendMessage("agent", agentReply);
      statusText.textContent = "اضغط واحتفظ للتحدث";
    });
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.innerHTML = `<div class="message-content">${text}</div>`;
    chatMessages?.prepend(div);
  }
});
