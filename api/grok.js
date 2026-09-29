/**
 * AI chat cho Zalo – Gemini free (mặc định) / xAI nếu AI_PROVIDER=xai
 * Wake: "Bot ơi ..."
 * Env: GEMINI_API_KEY, GEMINI_MODEL, AI_PROVIDER, XAI_API_KEY (optional)
 */

const MAX_BYTES = 5 * 1024 * 1024;
const history = new Map();
const MAX_TURNS = 10;

const SYSTEM = `Bạn là trợ lý AI thông minh trên Zalo bot ONTOP (powered by Google Gemini).
Chat tiếng Việt tự nhiên như người thật. Phân tích link/ảnh/file khi có dữ liệu kèm.
Không tiết lộ API key. Không giả lệnh bot (/tiktok, /login...).
Nếu thiếu dữ liệu thì nói rõ.`;

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
  h.push({ role, content: String(content) });
  while (h.length > MAX_TURNS * 2) h.shift();
}

function extractUrls(text) {
  const re = /https?:\/\/[^\s<>"')\]]+/gi;
  return [...new Set(String(text).match(re) || [])].slice(0, 3);
}

async function fetchPageText(url) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12000);
    const res = await fetch(url, {
      signal: ctrl.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; ONTOP-Bot/1.0)",
        Accept: "text/html,application/json,text/plain;q=0.9,*/*;q=0.8",
      },
      redirect: "follow",
    });
    clearTimeout(t);
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length > MAX_BYTES) {
      return `[URL ${url}] quá lớn (${buf.length}B). HTTP ${res.status}`;
    }
    let text = buf.toString("utf8");
    if (ct.includes("html")) {
      text = text
        .replace(/<script[\s\S]*?<\/script>/gi, " ")
        .replace(/<style[\s\S]*?<\/style>/gi, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    }
    return `[Nội dung ${url}] HTTP ${res.status}\n${text.slice(0, 12000)}`;
  } catch (e) {
    return `[Không fetch ${url}: ${e.message}]`;
  }
}

async function bufferToBase64(url) {
  const res = await fetch(url, { headers: { "User-Agent": "ONTOP-Bot/1.0" } });
  const buf = Buffer.from(await res.arrayBuffer());
  if (buf.length > MAX_BYTES) throw new Error("File/ảnh vượt 5MB");
  const ct = (res.headers.get("content-type") || "image/jpeg").split(";")[0].trim();
  return { mime: ct, data: buf.toString("base64"), size: buf.length };
}

async function chatGemini(chatId, userText, opts = {}) {
  const key = (process.env.GEMINI_API_KEY || "").trim();
  if (!key) throw new Error("Thiếu GEMINI_API_KEY");

  const model = (process.env.GEMINI_MODEL || "gemini-3.5-flash").trim();
  let text = (userText || "").trim();
  if (!text && (opts.imageUrl || opts.fileUrl)) {
    text = opts.imageUrl ? "Hãy xem ảnh và phân tích." : "Hãy phân tích file này.";
  }
  if (!text) text = "Xin chào";

  const urls = extractUrls(text);
  let extra = "";
  for (const u of urls) extra += "\n\n" + (await fetchPageText(u));

  if (opts.fileUrl && !opts.imageUrl) {
    try {
      const r = await fetch(opts.fileUrl, { headers: { "User-Agent": "ONTOP-Bot/1.0" } });
      const buf = Buffer.from(await r.arrayBuffer());
      if (buf.length <= MAX_BYTES) {
        extra += `\n\n--- FILE ${opts.fileName || "file"} (${buf.length}B) ---\n${buf.toString("utf8").slice(0, 10000)}`;
      } else extra += "\n\n[File vượt 5MB]";
    } catch (e) {
      extra += `\n\n[Lỗi đọc file: ${e.message}]`;
    }
  }

  const parts = [{ text: text + extra }];
  if (opts.imageUrl) {
    try {
      const img = await bufferToBase64(opts.imageUrl);
      parts.push({ inline_data: { mime_type: img.mime, data: img.data } });
    } catch (e) {
      parts[0].text += `\n\n[Không tải ảnh: ${e.message}]`;
    }
  }

  // Gemini history: user/model alternating
  const contents = [];
  for (const m of getHistory(chatId)) {
    contents.push({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content }],
    });
  }
  contents.push({ role: "user", parts });

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(key)}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM }] },
      contents,
      generationConfig: { temperature: 0.7, maxOutputTokens: 2048 },
    }),
  });
  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error("Gemini non-JSON: " + raw.slice(0, 200));
  }
  if (!res.ok) {
    const msg = data?.error?.message || raw.slice(0, 240);
    throw new Error(`Gemini ${res.status}: ${msg}`);
  }

  const reply =
    data?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") ||
    "(không có nội dung)";

  pushHistory(chatId, "user", text + (opts.imageUrl ? " [ảnh]" : "") + (urls.length ? " [link]" : ""));
  pushHistory(chatId, "assistant", reply);
  return String(reply).slice(0, 3800);
}

async function chatXai(chatId, userText, opts = {}) {
  const key = (process.env.XAI_API_KEY || "").trim();
  if (!key) throw new Error("Thiếu XAI_API_KEY");
  const model = process.env.XAI_MODEL || "grok-3";
  let text = (userText || "").trim() || "Xin chào";
  const urls = extractUrls(text);
  let extra = "";
  for (const u of urls) extra += "\n\n" + (await fetchPageText(u));
  const full = text + extra;
  const userContent = opts.imageUrl
    ? [
        { type: "text", text: full },
        { type: "image_url", image_url: { url: opts.imageUrl } },
      ]
    : full;
  const messages = [
    { role: "system", content: SYSTEM },
    ...getHistory(chatId).map((m) => ({ role: m.role, content: m.content })),
    { role: "user", content: userContent },
  ];
  const res = await fetch("https://api.x.ai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({ model, messages, temperature: 0.7, max_tokens: 2000 }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || JSON.stringify(data).slice(0, 200));
  const reply = data?.choices?.[0]?.message?.content || "(empty)";
  pushHistory(chatId, "user", text);
  pushHistory(chatId, "assistant", reply);
  return String(reply).slice(0, 3800);
}

async function chatGrok(chatId, userText, opts = {}) {
  const provider = (process.env.AI_PROVIDER || "gemini").toLowerCase();
  if (provider === "xai" || provider === "grok") {
    return chatXai(chatId, userText, opts);
  }
  return chatGemini(chatId, userText, opts);
}

/** Báo cáo trạng thái bot (cron / health) */
function statusReport() {
  const provider = process.env.AI_PROVIDER || "gemini";
  const model =
    provider === "xai" || provider === "grok"
      ? process.env.XAI_MODEL || "grok-3"
      : process.env.GEMINI_MODEL || "gemini-3.5-flash";
  const hasKey =
    provider === "xai" || provider === "grok"
      ? !!(process.env.XAI_API_KEY || "").trim()
      : !!(process.env.GEMINI_API_KEY || "").trim();
  const now = new Date().toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
  return (
    `🤖 ONTOP Bot — báo cáo định kỳ\n` +
    `⏰ ${now}\n` +
    `🧠 AI: ${provider} / ${model}\n` +
    `🔑 Key: ${hasKey ? "OK" : "THIẾU"}\n` +
    `💬 Gọi AI: Bot ơi {câu hỏi}\n` +
    `📎 Ảnh/file ≤5MB · phân tích link tự động`
  );
}

module.exports = {
  isWake,
  stripWake,
  chatGrok,
  statusReport,
  MAX_PHOTO: MAX_BYTES,
};
