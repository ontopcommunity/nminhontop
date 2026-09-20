// Zalo Bot Webhook - ảnh ≤ 5MB, vượt quá báo lỗi
const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN || "5-r-FcilN7xnTfZm0n";
const {
  sendMessage,
  sendPhoto,
  sendChatAction,
  setChatKeyboard,
  deleteChatKeyboard,
} = require("./bot");

// Ảnh demo nhỏ (placehold.co thường < 100KB)
const DEMO_PHOTO = "https://placehold.co/600x400/png?text=Zalo+Bot+Ontop";

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const receivedToken = req.headers["x-bot-api-secret-token"];
  if (receivedToken !== SECRET_TOKEN) {
    console.warn("Invalid secret token");
    return res.status(403).json({ error: "Forbidden" });
  }

  try {
    const body = req.body;
    console.log("Received event:", JSON.stringify(body, null, 2));

    const event = body.result || body;
    const message = event.message || body.message;

    if (!message || !message.chat || !message.chat.id) {
      return res.status(200).json({ ok: true, note: "no message" });
    }

    const chatId = message.chat.id;
    const text = (message.text || "").trim();
    const lower = text.toLowerCase();

    await sendChatAction(chatId, "typing").catch(() => {});

    // ===== Commands =====
    if (lower === "/start" || lower === "start" || lower === "menu") {
      await sendMessage(
        chatId,
        "🤖 Bot Ontopcommunity sẵn sàng!\n\n" +
          "Lệnh thử:\n" +
          "/photo - Gửi ảnh demo (≤ 5MB)\n" +
          "/keyboard - Hiện nút bàn phím\n" +
          "/hidekb - Ẩn bàn phím\n" +
          "/help - Trợ giúp\n\n" +
          "Gửi link ảnh → bot sẽ gửi lại nếu ≤ 5MB\n" +
          "Ảnh > 5MB sẽ bị từ chối và báo lỗi."
      );
    } else if (lower === "/photo" || lower === "photo" || lower === "ảnh") {
      const result = await sendPhoto(chatId, DEMO_PHOTO, "Ảnh demo từ Bot Ontop 📸 (≤ 5MB)");
      if (result && result.ok === false) {
        await sendMessage(chatId, `❌ ${result.error}`);
      }
    } else if (lower === "/keyboard" || lower === "keyboard" || lower === "nút") {
      const kb = {
        keyboard: [
          [{ text: "📷 Gửi ảnh" }, { text: "ℹ️ Help" }],
          [{ text: "Ẩn bàn phím" }],
        ],
        resize_keyboard: true,
        one_time_keyboard: false,
      };
      const kbResult = await setChatKeyboard(chatId, kb);
      if (kbResult && kbResult.ok === false) {
        await sendMessage(
          chatId,
          "⚠️ setChatKeyboard chưa được hỗ trợ trên API chính thức.\nDùng lệnh: /photo  /help"
        );
      } else {
        await sendMessage(chatId, "Đã hiện bàn phím nhanh bên dưới 👇");
      }
    } else if (lower === "/hidekb" || lower === "ẩn bàn phím" || lower === "ẩn") {
      await deleteChatKeyboard(chatId);
      await sendMessage(chatId, "Đã ẩn bàn phím.");
    } else if (lower === "/help" || lower === "help" || lower === "ℹ️ help") {
      await sendMessage(
        chatId,
        "📖 Hướng dẫn\n\n" +
          "• Gửi text → bot echo lại\n" +
          "• /photo → gửi ảnh demo (≤ 5MB)\n" +
          "• Gửi link ảnh (https://...) → bot gửi lại nếu ≤ 5MB\n" +
          "• Ảnh > 5MB → báo lỗi, không gửi\n" +
          "• /keyboard → thử hiện nút\n" +
          "• /hidekb → ẩn nút"
      );
    } else if (lower === "📷 gửi ảnh" || lower.includes("gửi ảnh")) {
      const result = await sendPhoto(chatId, DEMO_PHOTO, "Ảnh theo yêu cầu từ nút 📷");
      if (result && result.ok === false) {
        await sendMessage(chatId, `❌ ${result.error}`);
      }
    } else if (/^https?:\/\/.+\.(jpg|jpeg|png|gif|webp|bmp)(\?.*)?$/i.test(text) || /^https?:\/\/.+/i.test(text) && text.includes("http")) {
      // User gửi link ảnh → thử gửi lại với check 5MB
      const result = await sendPhoto(chatId, text, "Ảnh bạn gửi (đã kiểm tra ≤ 5MB)");
      if (result && result.ok === false) {
        await sendMessage(chatId, `❌ ${result.error}`);
      } else if (result && result.ok) {
        // đã gửi thành công
      } else {
        await sendMessage(chatId, "Không gửi được ảnh. Kiểm tra lại URL.");
      }
    } else if (text) {
      await sendMessage(chatId, `Bot nhận được: ${text}`);
    } else if (message.photo || event.event_name === "message.image.received") {
      await sendMessage(chatId, "Đã nhận ảnh của bạn 📸 (bot chưa lưu/ xử lý ảnh đầu vào).");
    } else {
      await sendMessage(chatId, "Bot đã nhận tin nhắn (loại khác text).");
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(200).json({ ok: true, error: String(err.message || err) });
  }
};
