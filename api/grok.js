/**
 * xAI Grok agent qua Zalo – chỉ khi "Bot ơi"
 * Env: XAI_API_KEY, XAI_MODEL (mặc định grok-3)
 * Phân tích link (fetch text), ảnh/file ≤5MB
 */

const XAI_URL = "https://api.x.ai/v1/chat/completions";
const DEFAULT_MODEL = process.env.XAI_MODEL || "grok-3";
const MAX_PHOTO = 5 * 1024 * 1024;

const history = new Map();
const MAX_TURNS = 10;

const SYSTEM = `Bạn là Grok (xAI) — trợ lý thông minh trên Zalo bot ONTOP.
Phong cách: chat thật, tiếng Việt tự nhiên, rõ ràng. Có thể phân tích sâu khi cần.

Khả năng:
- Phân tích / tóm tắt link web (nội dung đã được hệ thống fetch kèm theo nếu có).
- Mô tả và phân tích ảnh user gửi.
- Giải thích file / nội dung text đính kèm.
- Lý luận, code, so sánh, lên kế hoạch như agent.

Không tiết lộ API key/secret. Không giả các lệnh bot (/tiktok, /login...).
Nếu thiếu dữ liệu (link không fetch được), nói rõ và hỏi thêm.`;

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
  h.push({ role, content: typeof content === "string" ? content : JSON.stringify(content) });
  while (h.length > MAX_TURNS * 2) h.shift();
}

function extractUrls(text) {
  const re = /https?:\/\/[^\s<>"')\]]+/gi;
  const found = text.match(re) || [];
  return [...new Set(found)].slice(0, 3);
}

async function fetchPageText(url) {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 12000);
    const res = await fetch(url, {
      signal: ctrl.signal,
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; ONTOP-GrokBot/1.0)",
        Accept: "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
      },
      redirect: "follow",
    });
    clearTimeout(t);
    const ct = (res.headers.get("content-type") || "").toLowerCase();
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length > MAX_PHOTO) {
      return `[URL ${url}] quá lớn (${buf.length} bytes), bỏ qua nội dung đầy đủ. HTTP ${res.status} ${ct}`;
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
    text = text.slice(0, 12000);
    return `[Nội dung từ ${url}] (HTTP ${res.status})\n${text}`;
  } catch (e) {
    return `[Không fetch được ${url}: ${e.message}]`;
  }
}

async function chatGrok(chatId, userText, opts = {}) {
  const key = getApiKey();
  let text = (userText || "").trim();
  if (!text && (opts.imageUrl || opts.fileUrl)) {
    text = opts.imageUrl ? "Hãy xem ảnh và phân tích giúp mình." : "Hãy phân tích file này.";
  }
  if (!text) text = "Xin chào";

  const urls = extractUrls(text);
  let linkContext = "";
  if (urls.length) {
    const parts = [];
    for (const u of urls) parts.push(await fetchPageText(u));
    linkContext = "\n\n--- DỮ LIỆU LINK (hệ thống đã tải) ---\n" + parts.join("\n\n");
  }

  let fileContext = "";
  if (opts.fileUrl && !opts.imageUrl) {
    try {
      const r = await fetch(opts.fileUrl, {
        headers: { "User-Agent": "ONTOP-GrokBot/1.0" },
      });
      const buf = Buffer.from(await r.arrayBuffer());
      if (buf.length <= MAX_PHOTO) {
        const name = opts.fileName || "file";
        fileContext = `\n\n--- FILE đính kèm: ${name} (${buf.length} bytes) ---\n${buf.toString("utf8").slice(0, 10000)}`;
      } else {
        fileContext = `\n\n[File ${opts.fileName || ""} vượt 5MB — không đọc được nội dung]`;
      }
    } catch (e) {
      fileContext = `\n\n[Không đọc file: ${e.message}]`;
    }
  }

  const fullText = text + linkContext + fileContext;
  const userContent = opts.imageUrl
    ? [
        { type: "text", text: fullText },
        { type: "image_url", image_url: { url: opts.imageUrl } },
      ]
    : fullText;

  const messages = [
    { role: "system", content: SYSTEM },
    ...getHistory(chatId).map((m) => ({ role: m.role, content: m.content })),
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
      max_tokens: 2000,
    }),
  });

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error(`Grok response không JSON: ${raw.slice(0, 240)}`);
  }
  if (!res.ok) {
    const msg = data?.error?.message || data?.error || raw.slice(0, 240);
    throw new Error(`Grok API ${res.status}: ${msg}`);
  }

  const reply =
    data?.choices?.[0]?.message?.content ||
    data?.choices?.[0]?.text ||
    "(không có nội dung)";

  pushHistory(chatId, "user", text + (opts.imageUrl ? " [ảnh]" : "") + (urls.length ? " [link]" : ""));
  pushHistory(chatId, "assistant", reply);
  return String(reply).slice(0, 3800);
}

module.exports = { isWake, stripWake, chatGrok, MAX_PHOTO };
