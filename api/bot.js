/**
 * Zalo Bot Platform helpers
 * Ảnh tối đa 5MB — vượt quá sẽ trả lỗi, không gửi
 */

const BOT_TOKEN = process.env.ZALO_BOT_TOKEN || "3415615569922217583:GOsmyGCVFMUxhXvOQXQKGNAKYYvpwovhxCwtCWlzMNpLqDJcdYfgOSSQqLaNUpQc";
const API_BASE = `https://bot-api.zaloplatforms.com/bot${BOT_TOKEN}`;
const MAX_PHOTO_BYTES = 5 * 1024 * 1024; // 5 MB

async function callApi(method, body = {}) {
  const res = await fetch(`${API_BASE}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  console.log(`[API ${method}]`, JSON.stringify(data).slice(0, 500));
  return data;
}

/** Kiểm tra dung lượng file từ URL (HEAD hoặc GET range) */
async function getUrlFileSize(url) {
  try {
    // Thử HEAD trước
    const head = await fetch(url, { method: "HEAD", redirect: "follow" });
    const len = head.headers.get("content-length");
    if (len) return parseInt(len, 10);

    // Fallback: GET với Range 0-0
    const range = await fetch(url, {
      method: "GET",
      headers: { Range: "bytes=0-0" },
      redirect: "follow",
    });
    const contentRange = range.headers.get("content-range");
    if (contentRange) {
      const match = contentRange.match(/\/(\d+)$/);
      if (match) return parseInt(match[1], 10);
    }
    const len2 = range.headers.get("content-length");
    if (len2) return parseInt(len2, 10);

    return null; // không xác định được
  } catch (err) {
    console.error("getUrlFileSize error:", err.message);
    return null;
  }
}

/** Gửi tin nhắn text (max 2000 ký tự) */
async function sendMessage(chatId, text, options = {}) {
  const payload = { chat_id: chatId, text };
  if (options.parse_mode) payload.parse_mode = options.parse_mode;
  if (options.text_styles) payload.text_styles = options.text_styles;
  return callApi("sendMessage", payload);
}

/**
 * Gửi ảnh qua URL công khai + caption
 * - Chỉ gửi nếu dung lượng ≤ 5MB
 * - Vượt 5MB → trả về { ok: false, error: "..." }
 */
async function sendPhoto(chatId, photoUrl, caption) {
  if (!photoUrl || typeof photoUrl !== "string") {
    return { ok: false, error: "URL ảnh không hợp lệ" };
  }

  const size = await getUrlFileSize(photoUrl);

  if (size === null) {
    // Không lấy được size → vẫn thử gửi (một số server không trả Content-Length)
    console.warn("Không xác định được dung lượng ảnh, vẫn thử gửi:", photoUrl);
  } else if (size > MAX_PHOTO_BYTES) {
    const mb = (size / (1024 * 1024)).toFixed(2);
    return {
      ok: false,
      error: `Ảnh vượt quá giới hạn 5MB (hiện tại ~${mb} MB). Vui lòng dùng ảnh nhỏ hơn.`,
      size_bytes: size,
      size_mb: parseFloat(mb),
    };
  }

  const payload = { chat_id: chatId, photo: photoUrl };
  if (caption) payload.caption = caption;
  return callApi("sendPhoto", payload);
}

/** Gửi sticker theo ID */
async function sendSticker(chatId, stickerId) {
  return callApi("sendSticker", { chat_id: chatId, sticker: stickerId });
}

/** Gửi voice (.aac URL) - chỉ 1-1 */
async function sendVoice(chatId, voiceUrl) {
  return callApi("sendVoice", { chat_id: chatId, voice: voiceUrl });
}

/** Hiển thị typing / upload_photo */
async function sendChatAction(chatId, action = "typing") {
  return callApi("sendChatAction", { chat_id: chatId, action });
}

async function setChatKeyboard(chatId, keyboardJson) {
  return callApi("setChatKeyboard", {
    chat_id: chatId,
    keyboard: typeof keyboardJson === "string" ? keyboardJson : JSON.stringify(keyboardJson),
  });
}

async function deleteChatKeyboard(chatId) {
  return callApi("deleteChatKeyboard", { chat_id: chatId });
}

async function uploadFile(fileUrl) {
  return callApi("uploadFile", { file_url: fileUrl });
}

module.exports = {
  sendMessage,
  sendPhoto,
  sendSticker,
  sendVoice,
  sendChatAction,
  setChatKeyboard,
  deleteChatKeyboard,
  uploadFile,
  getUrlFileSize,
  MAX_PHOTO_BYTES,
  callApi,
};
