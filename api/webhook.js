// Zalo Bot Webhook - TikTok commands + media
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
  searchVideos,
  formatUserCaption,
  formatVideoCaption,
  formatSearchList,
} = require("./tiktok");

const DEMO_PHOTO = "https://placehold.co/600x400/png?text=Zalo+Bot+Ontop";

// Lưu kết quả search theo chat_id (memory - reset khi cold start)
const searchCache = globalThis.__zaloSearchCache || (globalThis.__zaloSearchCache = new Map());

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
            // Avatar quá lớn hoặc lỗi → gửi text
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
        // Gửi link tải riêng nếu dài
        if (data.urls?.no_watermark) {
          await sendMessage(chatId, `⬇️ Link tải không logo:\n${data.urls.no_watermark}`);
        }
      } catch (e) {
        await sendMessage(chatId, `❌ Lỗi: ${e.message}`);
      }
      return res.status(200).json({ ok: true });
    }

    // ===== /search {keyword} {count?} =====
    if (lower.startsWith("/search") || lower.startsWith("search ")) {
      const parts = text.split(/\s+/);
      // /search keyword... count
      let count = 10;
      let keywordParts = parts.slice(1);
      if (keywordParts.length > 1 && /^\d+$/.test(keywordParts[keywordParts.length - 1])) {
        count = parseInt(keywordParts.pop(), 10);
      }
      const keyword = keywordParts.join(" ").trim();
      if (!keyword) {
        await sendMessage(
          chatId,
          "Cú pháp: /search {từ khóa} {số lượng}\nVí dụ: /search ontopcommunity 10\n(Mặc định 10 video)"
        );
        return res.status(200).json({ ok: true });
      }
      try {
        await sendMessage(chatId, `⏳ Đang tìm "${keyword}"...`);
        const videos = await searchVideos(keyword, count);
        searchCache.set(chatId, { videos, keyword, at: Date.now() });
        await sendMessage(chatId, formatSearchList(videos, keyword));
      } catch (e) {
        await sendMessage(
          chatId,
          `❌ Search lỗi: ${e.message}\n\nGợi ý: dùng /tiktok {user} hoặc /video {link}`
        );
      }
      return res.status(200).json({ ok: true });
    }

    // ===== Số sau search → chi tiết video =====
    if (/^\d{1,2}$/.test(text)) {
      const cached = searchCache.get(chatId);
      if (cached && Date.now() - cached.at < 30 * 60 * 1000) {
        const idx = parseInt(text, 10) - 1;
        const v = cached.videos[idx];
        if (!v) {
          await sendMessage(chatId, `Không có video số ${text}. Chọn 1–${cached.videos.length}`);
          return res.status(200).json({ ok: true });
        }
        const link =
          v.link ||
          `https://www.tiktok.com/@${v.author?.unique_id || v.author?.uniqueId || "user"}/video/${v.id || v.video_id}`;
        try {
          await sendMessage(chatId, `⏳ Lấy chi tiết video #${text}...`);
          const data = await getVideo(link);
          const caption = formatVideoCaption(data);
          const cover = data.urls?.cover || data.urls?.coverHD || v.cover;
          if (cover) {
            const photoRes = await sendPhoto(chatId, cover, caption.slice(0, 1900));
            if (photoRes && photoRes.ok === false) await sendMessage(chatId, caption);
          } else {
            await sendMessage(chatId, caption);
          }
          if (data.urls?.no_watermark) {
            await sendMessage(chatId, `⬇️ Tải không logo:\n${data.urls.no_watermark}`);
          }
        } catch (e) {
          await sendMessage(chatId, `❌ ${e.message}\nLink: ${link}`);
        }
        return res.status(200).json({ ok: true });
      }
    }

    // ===== Basic commands =====
    if (lower === "/start" || lower === "start" || lower === "menu") {
      await sendMessage(
        chatId,
        "🤖 Bot Ontopcommunity\n\n" +
          "📌 TikTok:\n" +
          "/tiktok {username} — thông tin acc + avatar\n" +
          "/video {link} — thông tin video + link tải\n" +
          "/search {từ khóa} {số} — tìm video (mặc định 10)\n" +
          "  → nhắn số để xem chi tiết\n\n" +
          "Khác:\n/photo /help /keyboard"
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
          "/search dance 5\n" +
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
