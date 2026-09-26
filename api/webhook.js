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
const {
  doConfig,
  doFetchTasks,
  doClaim,
  doServices,
  doAddOrder,
  doStatus,
  doBalance,
  doCancel,
  doBoost,
  loginSession,
} = require("./smm");

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

function fmtJson(obj, max = 1800) {
  try {
    const s = JSON.stringify(obj, null, 2);
    return s.length > max ? s.slice(0, max) + "\n… (cắt)" : s;
  } catch {
    return String(obj);
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
    const args = text.split(/\s+/).slice(1);

    await sendChatAction(chatId, "typing").catch(() => {});

    // ========== TIKTOK ==========
    if (lower.startsWith("/tiktok") || lower.startsWith("tiktok ")) {
      const username = args[0]?.replace(/^@/, "");
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
          if (photoRes && photoRes.ok === false) await sendMessage(chatId, caption);
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

    if (lower.startsWith("/video") || lower.startsWith("video ")) {
      const linkMatch = text.match(/https?:\/\/[^\s]+/);
      const link = linkMatch ? linkMatch[0] : null;
      if (!link) {
        await sendMessage(chatId, "✦ Cú pháp: /video {link TikTok}\nVí dụ: /video https://vm.tiktok.com/...");
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
          if (photoRes && photoRes.ok === false) await sendMessage(chatId, caption);
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

    // ========== TASK MODULE ==========
    // /login — kiểm tra session
    if (lower === "/login" || lower === "login") {
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Đang login session...");
        const cookie = await loginSession();
        await sendMessage(chatId, `✅ Login OK\nCookie: ${cookie.slice(0, 40)}...`);
      } catch (e) {
        await sendMessage(chatId, `✖ Login fail: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /config <loai> <id>
    if (lower.startsWith("/config") || lower.startsWith("config ")) {
      const loai = args[0];
      const id = args[1];
      if (!loai || !id) {
        await sendMessage(chatId, "✦ Cú pháp: /config {loai} {id}\nVí dụ: /config 1 123");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Config môi trường...");
        const data = await doConfig(loai, id);
        await sendMessage(chatId, `✅ Config\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Config lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /tasks <type> [nickchay]
    if (lower.startsWith("/tasks") || lower.startsWith("tasks ")) {
      const type = args[0];
      const nickchay = args[1] || "";
      const envCode = args[2] || type;
      if (!type) {
        await sendMessage(chatId, "✦ Cú pháp: /tasks {type} [nickchay] [envCode]\nVí dụ: /tasks like nick1 env_01");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, `⏳ Lấy nhiệm vụ type=${type} env=${envCode}...`);
        const data = await doFetchTasks(type, nickchay, envCode);
        await sendMessage(chatId, `📋 Tasks\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Tasks lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /claim <id|id1,id2> [nickchay]
    if (lower.startsWith("/claim") || lower.startsWith("claim ")) {
      const ids = args[0];
      const type = args[1] || "";
      const nickchay = args[2] || "";
      const envCode = args[3] || type;
      if (!ids) {
        await sendMessage(chatId, "✦ Cú pháp: /claim {id} {type} [nickchay] [envCode]\nVí dụ: /claim 889900 like nick1 env_01");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Claim nhiệm vụ...");
        const data = await doClaim(ids, type, nickchay, envCode);
        await sendMessage(chatId, `✅ Claim\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Claim lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // ========== PROCUREMENT MODULE ==========
    // /services
    if (lower === "/services" || lower === "services") {
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Lấy danh mục dịch vụ...");
        const data = await doServices();
        // nếu là mảng thì format ngắn
        let msg;
        if (Array.isArray(data)) {
          const lines = data.slice(0, 30).map(
            (s) => `#${s.service} ${s.name || "?"} | rate ${s.rate} | ${s.min}-${s.max}`
          );
          msg = `📦 Services (${data.length})\n${lines.join("\n")}${data.length > 30 ? "\n… còn nữa" : ""}`;
        } else {
          msg = `📦 Services\n\`\`\`\n${fmtJson(data)}\n\`\`\``;
        }
        await sendMessage(chatId, msg);
      } catch (e) {
        await sendMessage(chatId, `✖ Services lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /order <service> <link> <quantity> [comments...]
    if (lower.startsWith("/order") || lower.startsWith("order ")) {
      const service = args[0];
      const link = args[1];
      const quantity = args[2];
      const comments = args.slice(3).join(" ") || "";
      if (!service || !link || !quantity) {
        await sendMessage(
          chatId,
          "✦ Cú pháp: /order {service} {link} {quantity} [comments]\nVí dụ: /order 123 https://tiktok.com/@x 1000"
        );
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Tạo đơn hàng...");
        const data = await doAddOrder(service, link, quantity, comments);
        await sendMessage(chatId, `🛒 Order\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Order lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /status <order|order1,order2>
    if (lower.startsWith("/status") || lower.startsWith("status ")) {
      const order = args[0];
      if (!order) {
        await sendMessage(chatId, "✦ Cú pháp: /status {order}\nVí dụ: /status 98765 hoặc /status 1,2,3");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Kiểm tra trạng thái...");
        const data = await doStatus(order);
        await sendMessage(chatId, `📊 Status\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Status lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /balance
    if (lower === "/balance" || lower === "balance" || lower === "/sodu") {
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Kiểm tra số dư...");
        const data = await doBalance();
        await sendMessage(chatId, `💰 Balance\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Balance lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /cancel <order>
    if (lower.startsWith("/cancel") || lower.startsWith("cancel ")) {
      const order = args[0];
      if (!order) {
        await sendMessage(chatId, "✦ Cú pháp: /cancel {order}");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Hủy đơn...");
        const data = await doCancel(order);
        await sendMessage(chatId, `🗑 Cancel\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Cancel lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // /boost <order>
    if (lower.startsWith("/boost") || lower.startsWith("boost ")) {
      const order = args[0];
      if (!order) {
        await sendMessage(chatId, "✦ Cú pháp: /boost {order}");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Boost đơn...");
        const data = await doBoost(order);
        await sendMessage(chatId, `🚀 Boost\n\`\`\`\n${fmtJson(data)}\n\`\`\``);
      } catch (e) {
        await sendMessage(chatId, `✖ Boost lỗi: ${e.message}`);
      } finally {
        await clearWaiting(chatId, waitId);
      }
      return res.status(200).json({ ok: true });
    }

    // ========== MENU / HELP ==========
    if (lower === "/start" || lower === "start" || lower === "menu") {
      await sendMessage(
        chatId,
        "━━━━━━━━━━━━━━━━\n⚡ BOT ONTOP\n━━━━━━━━━━━━━━━━\n\n" +
          "▸ /tiktok {user}\n" +
          "▸ /video {link}\n\n" +
          "── Nhiệm vụ ──\n" +
          "▸ /login\n" +
          "▸ /config {loai} {id}\n" +
          "▸ /tasks {type} [nick] [env]\n" +
          "▸ /claim {id} {type} [nick] [env]\n\n" +
          "── Đơn hàng ──\n" +
          "▸ /services\n" +
          "▸ /order {svc} {link} {qty}\n" +
          "▸ /status {order}\n" +
          "▸ /balance\n" +
          "▸ /cancel {order}\n" +
          "▸ /boost {order}\n\n" +
          "▸ /help\n" +
          "━━━━━━━━━━━━━━━━"
      );
    } else if (lower === "/photo" || lower === "photo") {
      const result = await sendPhoto(chatId, DEMO_PHOTO, "✦ Ảnh demo (≤ 5MB)");
      if (result?.ok === false) await sendMessage(chatId, `✖ ${result.error}`);
    } else if (lower === "/help" || lower === "help") {
      await sendMessage(
        chatId,
        "━━━━━━━━━━━━━━━━\n📖 LỆNH CHI TIẾT\n━━━━━━━━━━━━━━━━\n\n" +
          "TIKTOK\n" +
          "/tiktok username\n" +
          "/video https://vm.tiktok.com/...\n\n" +
          "NHIỆM VỤ (session)\n" +
          "/login — test PHPSESSID\n" +
          "/config loai id\n" +
          "/tasks type [nickchay] [envCode]\n" +
          "/claim id type [nickchay] [envCode]\n\n" +
          "ĐƠN HÀNG (API key)\n" +
          "/services — danh mục\n" +
          "/order service link qty [cmt]\n" +
          "/status order hoặc order1,2\n" +
          "/balance\n" +
          "/cancel order\n" +
          "/boost order\n\n" +
          "Env cần set trên Vercel:\n" +
          "API_BASE   (1 link duy nhất)\n" +
          "ACCESS_TOKEN\n" +
          "API_KEY\n" +
          "━━━━━━━━━━━━━━━━"
      );
    } else if (lower === "/keyboard") {
      const r = await setChatKeyboard(chatId, {
        keyboard: [
          [{ text: "/help" }, { text: "/balance" }],
          [{ text: "/services" }, { text: "/login" }],
          [{ text: "Ẩn bàn phím" }],
        ],
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
