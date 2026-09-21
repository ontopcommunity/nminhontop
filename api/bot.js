/**
 * Zalo Bot Platform helpers
 */

const BOT_TOKEN = process.env.ZALO_BOT_TOKEN || "3415615569922217583:GOsmyGCVFMUxhXvOQXQKGNAKYYvpwovhxCwtCWlzMNpLqDJcdYfgOSSQqLaNUpQc";
const API_BASE = `https://bot-api.zaloplatforms.com/bot${BOT_TOKEN}`;
const MAX_PHOTO_BYTES = 5 * 1024 * 1024;

async function callApi(method, body = {}) {
  const res = await fetch(`${API_BASE}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  console.log(`[API ${method}]`, JSON.stringify(data).slice(0, 400));
  return data;
}

async function getUrlFileSize(url) {
  try {
    const head = await fetch(url, { method: "HEAD", redirect: "follow" });
    const len = head.headers.get("content-length");
    if (len) return parseInt(len, 10);
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
    return null;
  } catch (err) {
    return null;
  }
}

async function sendMessage(chatId, text, options = {}) {
  const payload = { chat_id: chatId, text };
  if (options.parse_mode) payload.parse_mode = options.parse_mode;
  if (options.text_styles) payload.text_styles = options.text_styles;
  return callApi("sendMessage", payload);
}

async function sendPhoto(chatId, photoUrl, caption) {
  if (!photoUrl || typeof photoUrl !== "string") {
    return { ok: false, error: "URL ảnh không hợp lệ" };
  }
  const size = await getUrlFileSize(photoUrl);
  if (size !== null && size > MAX_PHOTO_BYTES) {
    const mb = (size / (1024 * 1024)).toFixed(2);
    return {
      ok: false,
      error: `Ảnh vượt quá 5MB (~${mb} MB)`,
      size_bytes: size,
    };
  }
  const payload = { chat_id: chatId, photo: photoUrl };
  if (caption) payload.caption = caption.slice(0, 2000);
  return callApi("sendPhoto", payload);
}

async function sendChatAction(chatId, action = "typing") {
  return callApi("sendChatAction", { chat_id: chatId, action });
}

async function deleteMessage(chatId, messageId) {
  if (!messageId) return { ok: false };
  return callApi("deleteMessage", { chat_id: chatId, message_id: messageId });
}

function extractMessageId(apiResult) {
  if (!apiResult) return null;
  return (
    apiResult.result?.message_id ||
    apiResult.result?.message?.message_id ||
    apiResult.message_id ||
    apiResult.message?.message_id ||
    null
  );
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

module.exports = {
  sendMessage,
  sendPhoto,
  sendChatAction,
  deleteMessage,
  extractMessageId,
  setChatKeyboard,
  deleteChatKeyboard,
  MAX_PHOTO_BYTES,
  callApi,
};
