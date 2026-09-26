const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN;
if (!SECRET_TOKEN) throw new Error("Missing ZALO_SECRET_TOKEN env");
const {
  sendMessage,
  sendPhoto,
  sendChatAction,
  deleteMessage,
  extractMessageId,
  setChatKeyboard,
  deleteChatKeyboard,
} = require("./bot");
const {
  getUser,
  getVideo,
  formatUserCaption,
  formatVideoCaption,
} = require("./tiktok");

const DEMO_PHOTO = "https://placehold.co/600x400/png?text=Zalo+Bot+Ontop";

async function sendWaiting(chatId, text) {
  const r = await sendMessage(chatId, text);
  return extractMessageId(r);
}

async function clearWaiting(chatId, msgId) {
  if (!msgId) return;
  try {
    await deleteMessage(chatId, msgId);
  } catch (e) {
    console.warn("deleteMessage fail:", e.message);
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const receivedToken = req.headers["x-bot-api-secret-token"];
  if (receivedToken !== SECRET_TOKEN) {
    return res.status(403).json({ error: "Forbidden" });
  }

  try {
    const body = req.body;
    console.log("Event:", JSON.stringify(body).slice(0, 600));

    const event = body.result || body;
    const message = event.message || body.message;
    if (!message?.chat?.id) {
      return res.status(200).json({ ok: true, note: "no message" });
    }

    const chatId = message.chat.id;
    const text = (message.text || "").trim();
    const lower = text.toLowerCase();

    await sendChatAction(chatId, "typing").catch(() => {});

    // /tiktok
    if (lower.startsWith("/tiktok") || lower.startsWith("tiktok ")) {
      const username = text.split(/\s+/)[1]?.replace(/^@/, "");
      if (!username) {
        await sendMessage(chatId, "✦ Cú pháp: /tiktok {username}\nVí dụ: /tiktok ontopcommunity");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, `⏳ Đang soi @${username}...`);
        const data = await getUser(username);
        const caption = formatUserCaption(data);
        const avatar = data.author?.avatar;
        if (avatar) {
          const photoRes = await sendPhoto(chatId, avatar, caption);
          if (photoRes && photoRes.ok === false) {
            await sendMessage(chatId, caption);
          }
        } else {
          await sendMessage(chatId, caption);
        }
      } catch (e) {
        await sendMessage(chatId, `✖ Lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /video — 1 tin kết quả (có link trang tải), không spam link mp4
    if (lower.startsWith("/video") || lower.startsWith("video ")) {
      const linkMatch = text.match(/https?:\/\/[^\s]+/);
      const link = linkMatch ? linkMatch[0] : null;
      if (!link) {
        await sendMessage(
          chatId,
          "✦ Cú pháp: /video {link TikTok}\nVí dụ: /video https://vm.tiktok.com/..."
        );
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Đang lấy video...");
        const data = await getVideo(link);
        const caption = formatVideoCaption(data);
        const cover = data.urls?.cover || data.urls?.coverHD;
        if (cover) {
          const photoRes = await sendPhoto(chatId, cover, caption.slice(0, 1900));
          if (photoRes && photoRes.ok === false) {
            await sendMessage(chatId, caption);
          }
        } else {
          await sendMessage(chatId, caption);
        }
      } catch (e) {
        await sendMessage(chatId, `✖ Lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    if (lower === "/start" || lower === "start" || lower === "menu") {
      await sendMessage(
        chatId,
        "━━━━━━━━━━━━━━━━\n⚡ BOT ONTOP\n━━━━━━━━━━━━━━━━\n\n" +
          "▸ /tiktok {user} — profile + avatar\n" +
          "▸ /video {link} — info + trang tải\n" +
          "▸ /help — trợ giúp\n\n" +
          "━━━━━━━━━━━━━━━━"
      );
    } else if (lower === "/photo" || lower === "photo") {
      const result = await sendPhoto(chatId, DEMO_PHOTO, "✦ Ảnh demo (≤ 5MB)");
      if (result?.ok === false) await sendMessage(chatId, `✖ ${result.error}`);
    } else if (lower === "/help" || lower === "help") {
      await sendMessage(
        chatId,
        "━━━━━━━━━━━━━━━━\n📖 LỆNH\n━━━━━━━━━━━━━━━━\n\n" +
          "/tiktok ontopcommunity\n" +
          "/video https://vm.tiktok.com/...\n\n" +
          "Trang tải: nminhontop.vercel.app/tiktok\n" +
          "━━━━━━━━━━━━━━━━"
      );
    } else if (lower === "/keyboard") {
      const r = await setChatKeyboard(chatId, {
        keyboard: [[{ text: "/help" }], [{ text: "Ẩn bàn phím" }]],
        resize_keyboard: true,
      });
      if (r?.ok === false) await sendMessage(chatId, "Keyboard chưa hỗ trợ.");
      else await sendMessage(chatId, "✦ Đã hiện bàn phím");
    } else if (lower === "/hidekb" || lower === "ẩn bàn phím" || lower === "ẩn") {
      await deleteChatKeyboard(chatId);
      await sendMessage(chatId, "✦ Đã ẩn bàn phím");
    } else if (text) {
      await sendMessage(chatId, `▸ ${text}\nGõ /help để xem lệnh.`);
    } else {
      await sendMessage(chatId, "✦ Đã nhận tin nhắn.");
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(200).json({ ok: true, error: String(err.message || err) });
  }
};
