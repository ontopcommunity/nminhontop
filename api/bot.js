/**
 * Zalo Bot Platform helpers
 * Official: sendMessage, sendPhoto, sendSticker, sendChatAction, setWebhook...
 * Extended (SDK / experimental): setChatKeyboard, uploadFile
 */

const BOT_TOKEN = process.env.ZALO_BOT_TOKEN || "3415615569922217583:GOsmyGCVFMUxhXvOQXQKGNAKYYvpwovhxCwtCWlzMNpLqDJcdYfgOSSQqLaNUpQc";
const API_BASE = `https://bot-api.zaloplatforms.com/bot${BOT_TOKEN}`;

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

/** Gửi tin nhắn text (max 2000 ký tự) */
async function sendMessage(chatId, text, options = {}) {
  const payload = { chat_id: chatId, text };
  if (options.parse_mode) payload.parse_mode = options.parse_mode;
  if (options.text_styles) payload.text_styles = options.text_styles;
  return callApi("sendMessage", payload);
}

/** Gửi ảnh qua URL công khai + caption tùy chọn */
async function sendPhoto(chatId, photoUrl, caption) {
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

/**
 * Keyboard (reply keyboard) - theo zalo-bot-js SDK
 * keyboardJson ví dụ:
 * {
 *   "keyboard": [
 *     [{ "text": "Nút 1" }, { "text": "Nút 2" }],
 *     [{ "text": "Nút 3" }]
 *   ],
 *   "resize_keyboard": true,
 *   "one_time_keyboard": true
 * }
 */
async function setChatKeyboard(chatId, keyboardJson) {
  return callApi("setChatKeyboard", {
    chat_id: chatId,
    keyboard: typeof keyboardJson === "string" ? keyboardJson : JSON.stringify(keyboardJson),
  });
}

async function deleteChatKeyboard(chatId) {
  return callApi("deleteChatKeyboard", { chat_id: chatId });
}

/**
 * Upload file từ URL (experimental - tùy platform hỗ trợ)
 * Sau đó có thể dùng file_id để gửi nếu API có sendDocument/sendFile
 */
async function uploadFile(fileUrl) {
  return callApi("uploadFile", { file_url: fileUrl });
}

async function getFileInfo(fileId) {
  return callApi("getFileInfo", { file_id: fileId });
}

async function getFileDownloadUrl(fileId) {
  return callApi("getFileDownloadUrl", { file_id: fileId });
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
  getFileInfo,
  getFileDownloadUrl,
  callApi,
};
