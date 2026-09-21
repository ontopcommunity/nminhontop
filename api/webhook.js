// Zalo Bot Webhook - TikTok /tiktok + /video (không search, không proxy)
const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN || "5-r-FcilN7xnTfZm0n";
const {
  sendMessage,
  sendPhoto,
  sendChatAction,
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
    console.log("Event:", JSON.stringify(body).slice(0, 800));

    const event = body.result || body;
    const message = event.message || body.message;

    if (!message?.chat?.id) {
      return res.status(200).json({ ok: true, note: "no message" });
    }

    const chatId = message.chat.id;
    const text = (message.text || "").trim();
    const lower = text.toLowerCase();

    await sendChatAction(chatId, "typing").catch(() => {});

    // ===== /tiktok {username} =====
    if (lower.startsWith("/tiktok") || lower.startsWith("tiktok ")) {
      const parts = text.split(/\s+/);
      const username = parts[1]?.replace(/^@/, "");
      if (!username) {
        await sendMessage(chatId, "Cú pháp: /tiktok {username}\nVí dụ: /tiktok ontopcommunity");
        return res.status(200).json({ ok: true });
      }
      try {
        await sendMessage(chatId, `⏳ Đang lấy thông tin @${username}...`);
        const data = await getUser(username);
        const caption = formatUserCaption(data);
        const avatar = data.author?.avatar;
        if (avatar) {
          const photoRes = await sendPhoto(chatId, avatar, caption);
          if (photoRes && photoRes.ok === false) {
            await sendMessage(chatId, caption);
            if (photoRes.error) await sendMessage(chatId, `⚠️ Avatar: ${photoRes.error}`);
          }
        } else {
          await sendMessage(chatId, caption);
        }
      } catch (e) {
        await sendMessage(chatId, `❌ Lỗi: ${e.message}`);
      }
      return res.status(200).json({ ok: true });
    }

    // ===== /video {link} =====
    if (lower.startsWith("/video") || lower.startsWith("video ")) {
      const linkMatch = text.match(/https?:\/\/[^\s]+/);
      const link = linkMatch ? linkMatch[0] : null;
      if (!link) {
        await sendMessage(
          chatId,
          "Cú pháp: /video {link TikTok}\nVí dụ: /video https://vm.tiktok.com/ZSVvFHtAg/"
        );
        return res.status(200).json({ ok: true });
      }
      try {
        await sendMessage(chatId, "⏳ Đang lấy thông tin video...");
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
        if (data.urls?.no_watermark) {
          await sendMessage(chatId, `⬇️ Link tải không logo:\n${data.urls.no_watermark}`);
        }
      } catch (e) {
        await sendMessage(chatId, `❌ Lỗi: ${e.message}`);
      }
      return res.status(200).json({ ok: true });
    }

    // ===== Basic =====
    if (lower === "/start" || lower === "start" || lower === "menu") {
      await sendMessage(
        chatId,
        "🤖 Bot Ontopcommunity\n\n" +
          "📌 TikTok:\n" +
          "/tiktok {username} — thông tin acc + avatar\n" +
          "/video {link} — thông tin video + link tải\n\n" +
          "Khác:\n/photo /help"
      );
    } else if (lower === "/photo" || lower === "photo" || lower === "ảnh") {
      const result = await sendPhoto(chatId, DEMO_PHOTO, "Ảnh demo (≤ 5MB)");
      if (result?.ok === false) await sendMessage(chatId, `❌ ${result.error}`);
    } else if (lower === "/help" || lower === "help") {
      await sendMessage(
        chatId,
        "📖 Lệnh:\n" +
          "/tiktok ontopcommunity\n" +
          "/video https://vm.tiktok.com/...\n" +
          "/photo — ảnh demo\n" +
          "Ảnh gửi qua bot tối đa 5MB."
      );
    } else if (lower === "/keyboard" || lower === "keyboard") {
      const kb = {
        keyboard: [
          [{ text: "/tiktok ontopcommunity" }, { text: "/help" }],
          [{ text: "Ẩn bàn phím" }],
        ],
        resize_keyboard: true,
      };
      const r = await setChatKeyboard(chatId, kb);
      if (r?.ok === false) {
        await sendMessage(chatId, "Keyboard API chưa hỗ trợ. Dùng lệnh text.");
      } else {
        await sendMessage(chatId, "Đã hiện bàn phím 👇");
      }
    } else if (lower === "/hidekb" || lower === "ẩn bàn phím" || lower === "ẩn") {
      await deleteChatKeyboard(chatId);
      await sendMessage(chatId, "Đã ẩn bàn phím.");
    } else if (text) {
      await sendMessage(chatId, `Bot nhận: ${text}\nGõ /help để xem lệnh.`);
    } else {
      await sendMessage(chatId, "Bot đã nhận tin nhắn.");
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(200).json({ ok: true, error: String(err.message || err) });
  }
};
