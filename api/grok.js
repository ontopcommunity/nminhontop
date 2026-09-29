/**
 * xAI Grok chat helper – chỉ gọi khi user wake "Bot ơi"
 * Env: XAI_API_KEY, optional XAI_MODEL (default grok-4-latest / grok-3)
 */

const XAI_URL = "https://api.x.ai/v1/chat/completions";
const DEFAULT_MODEL = process.env.XAI_MODEL || "grok-3";

// Best-effort history trên warm instance (serverless không đảm bảo)
const history = new Map();
const MAX_TURNS = 8;

const SYSTEM = `Bạn là Grok (xAI), đang chat qua Zalo bot ONTOP.
Trả lời tiếng Việt tự nhiên, ngắn gọn khi phù hợp, như chat thật.
Không giả lệnh bot (/tiktok, /login, …). Không tiết lộ API key hay secret.
Nếu user gửi ảnh, mô tả/trả lời dựa trên ảnh nếu có.`;

function getApiKey() {
  const k = (process.env.XAI_API_KEY || "").trim();
  if (!k) throw new Error("Thiếu XAI_API_KEY trên Vercel env");
  return k;
}

function isWake(text) {
  if (!text || typeof text !== "string") return false;
  return /^\s*bot\s*ơi\b/i.test(text) || /^\s*bot\s*oi\b/i.test(text);
}

function stripWake(text) {
  return String(text || "")
    .replace(/^\s*bot\s*ơi\b\s*[:，,.\-]?\s*/i, "")
    .replace(/^\s*bot\s*oi\b\s*[:，,.\-]?\s*/i, "")
    .trim();
}

function getHistory(chatId) {
  if (!history.has(chatId)) history.set(chatId, []);
  return history.get(chatId);
}

function pushHistory(chatId, role, content) {
  const h = getHistory(chatId);
  h.push({ role, content });
  while (h.length > MAX_TURNS * 2) h.shift();
}

/**
 * @param {string|number} chatId
 * @param {string} userText
 * @param {{ imageUrl?: string }} [opts]
 */
async function chatGrok(chatId, userText, opts = {}) {
  const key = getApiKey();
  const text = (userText || "").trim() || (opts.imageUrl ? "User gửi ảnh, hãy xem và trả lời." : "Xin chào");

  const userContent = opts.imageUrl
    ? [
        { type: "text", text },
        { type: "image_url", image_url: { url: opts.imageUrl } },
      ]
    : text;

  const messages = [
    { role: "system", content: SYSTEM },
    ...getHistory(chatId),
    { role: "user", content: userContent },
  ];

  const res = await fetch(XAI_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model: DEFAULT_MODEL,
      messages,
      temperature: 0.7,
      max_tokens: 1200,
    }),
  });

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(`Grok response không JSON: ${raw.slice(0, 200)}`);
  }
  if (!res.ok) {
    const msg = data?.error?.message || data?.error || raw.slice(0, 200);
    throw new Error(`Grok API ${res.status}: ${msg}`);
  }

  const reply =
    data?.choices?.[0]?.message?.content ||
    data?.choices?.[0]?.text ||
    "(không có nội dung)";

  // Lưu history dạng text (đơn giản)
  pushHistory(chatId, "user", text + (opts.imageUrl ? " [ảnh]" : ""));
  pushHistory(chatId, "assistant", reply);

  return String(reply).slice(0, 3500);
}

module.exports = {
  isWake,
  stripWake,
  chatGrok,
};
