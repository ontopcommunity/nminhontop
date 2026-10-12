const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN;
const ADMIN_CHAT_ID = String(
  process.env.ADMIN_CHAT_ID ||
    process.env.REPORT_CHAT_ID ||
    process.env.ZALO_CHAT_ID ||
    "4e35fa606d3e8460dd2f"
).trim();
const RENT_BOT_URL = (
  process.env.RENT_BOT_URL || "https://apimbbankvip.vercel.app/api/rent-bot"
).replace(/\/$/, "");
const RENT_BOT_SECRET = process.env.RENT_BOT_SECRET || process.env.ZALO_SECRET_TOKEN || "";

if (!SECRET_TOKEN) throw new Error("Missing ZALO_SECRET_TOKEN env");

const {
  sendMessage,
  sendPhoto,
  sendChatAction,
  deleteMessage,
  extractMessageId,
} = require("./bot");
const { getUser, getVideo, formatUserCaption, formatVideoCaption } = require("./tiktok");

async function sendWaiting(chatId, text) {
  const r = await sendMessage(chatId, text);
  return extractMessageId(r);
}

async function clearWaiting(chatId, msgId) {
  if (!msgId) return;
  try {
    await deleteMessage(chatId, msgId);
  } catch (_) {}
}

function isRentRelated(text) {
  const t = String(text || "").trim().toLowerCase();
  if (!t) return false;
  const cmds = [
    "/thueapibank",
    "thueapibank",
    "/tkapi",
    "tkapi",
    "/mystatus",
    "mystatus",
    "/cancel",
    "cancel",
    "/help",
    "help",
    "/start",
  ];
  if (cmds.some((c) => t === c || t.startsWith(c + " "))) return true;
  // flow: số + đơn vị, MB, username, password
  if (
    /^(\d+\s*)?(ngay|ngày|thang|tháng|nam|năm|day|month|year|1|2|3|mb|mbbank)$/i.test(t)
  )
    return true;
  if (/^\d+\s*(ngay|ngày|thang|tháng|nam|năm)/i.test(t)) return true;
  // any non-slash text may be rent flow (qty / pass)
  if (!t.startsWith("/")) return true;
  return false;
}

async function callRentBot(chatId, text, isAdmin, extra = {}) {
  const r = await fetch(RENT_BOT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      secret: RENT_BOT_SECRET,
      chatId: String(chatId),
      text: String(text || ""),
      isAdmin: !!isAdmin,
      ...extra,
    }),
  });
  return r.json().catch(() => ({}));
}

async function deliverReplies(chatId, data) {
  for (const m of data.replies || []) {
    if (!m) continue;
    if (typeof m === "string") {
      await sendMessage(chatId, m);
      continue;
    }
    if (m.photo) {
      const pr = await sendPhoto(chatId, m.photo, (m.text || "").slice(0, 1900));
      if (pr && pr.ok === false && m.text) await sendMessage(chatId, m.text);
      else if (!m.photo && m.text) await sendMessage(chatId, m.text);
    } else if (m.text) {
      await sendMessage(chatId, m.text);
    }
  }
  if (data.notifyTarget?.chatId && data.notifyTarget?.text) {
    await sendMessage(data.notifyTarget.chatId, data.notifyTarget.text).catch(() => {});
  }
  if (data.broadcast?.chatIds?.length && data.broadcast?.text) {
    for (const id of data.broadcast.chatIds) {
      await sendMessage(id, "📣 " + data.broadcast.text).catch(() => {});
    }
  }
  if (data.sideEffects) {
    for (const se of data.sideEffects) {
      if (se.type === "admin_notify" && se.text && ADMIN_CHAT_ID) {
        await sendMessage(ADMIN_CHAT_ID, se.text).catch(() => {});
      }
    }
  }
  // auto check payment after QR
  if (data.autoCheckMs && data.autoCheckChatId) {
    const cid = data.autoCheckChatId;
    setTimeout(async () => {
      try {
        const d2 = await callRentBot(cid, "/__checkpay_internal", false, {
          action: "checkpay",
        });
        await deliverReplies(cid, d2);
        if (d2.sideEffects) {
          for (const se of d2.sideEffects) {
            if (se.type === "admin_notify" && se.text && ADMIN_CHAT_ID) {
              await sendMessage(ADMIN_CHAT_ID, se.text).catch(() => {});
            }
          }
        }
        // second pass
        if (!d2.paid) {
          setTimeout(async () => {
            try {
              const d3 = await callRentBot(cid, "/__checkpay_internal", false, {
                action: "checkpay",
              });
              await deliverReplies(cid, d3);
              if (d3.sideEffects) {
                for (const se of d3.sideEffects) {
                  if (se.type === "admin_notify" && se.text && ADMIN_CHAT_ID) {
                    await sendMessage(ADMIN_CHAT_ID, se.text).catch(() => {});
                  }
                }
              }
            } catch (_) {}
          }, 25000);
        }
      } catch (_) {}
    }, Number(data.autoCheckMs) || 18000);
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
    const event = body.result || body;
    const message = event.message || body.message;
    if (!message?.chat?.id) {
      return res.status(200).json({ ok: true, note: "no message" });
    }

    const chatId = message.chat.id;
    const text = (message.text || "").trim();
    const lower = text.toLowerCase();
    const args = text.split(/\s+/).slice(1);
    const isAdmin = !ADMIN_CHAT_ID || String(chatId) === String(ADMIN_CHAT_ID);

    const fromName =
      message.from?.name ||
      message.from?.display_name ||
      message.from?.full_name ||
      message.chat?.name ||
      "";
    const fromId = message.from?.id || "";

    // Lần đầu vào bot: chào + lưu DB + báo admin
    try {
      const reg = await callRentBot(chatId, "/__register_visitor", isAdmin, {
        action: "register_visitor",
        meta: { name: fromName, fromId: String(fromId) },
      });
      if (reg.isNew) {
        await deliverReplies(chatId, reg);
        // admin đã nhận qua sideEffects trong deliverReplies
        // user mới: nếu chỉ "vào" không gửi lệnh thì vẫn chào xong return
        if (!text || !String(text).trim()) {
          return res.status(200).json({ ok: true, note: "welcome_new" });
        }
      }
    } catch (e) {
      console.warn("register_visitor fail", e.message);
    }

    // ===== USER: chỉ thuê API =====
    if (!isAdmin) {
      if (!isRentRelated(text)) {
        await sendMessage(
          chatId,
          "🔒 Chỉ hỗ trợ thuê API Bank.\n\n" +
            "/thueapibank — thuê API\n" +
            "/tkapi — gắn TK ngân hàng\n" +
            "/mystatus — trạng thái\n" +
            "/help"
        ).catch(() => {});
        return res.status(200).json({ ok: true, note: "user_blocked" });
      }
      await sendChatAction(chatId, "typing").catch(() => {});
      try {
        const data = await callRentBot(chatId, text, false);
        await deliverReplies(chatId, data);
        if (!(data.replies || []).length && data.handled === false) {
          await sendMessage(chatId, "Gõ /thueapibank hoặc /help");
        }
      } catch (e) {
        await sendMessage(chatId, "✖ Lỗi: " + (e.message || e));
      }
      return res.status(200).json({ ok: true, note: "user_rent" });
    }

    // ===== ADMIN =====
    await sendChatAction(chatId, "typing").catch(() => {});

    // Admin rent / gift / manage
    const adminRent =
      lower.startsWith("/thueapibank") ||
      lower.startsWith("/tkapi") ||
      lower.startsWith("/mystatus") ||
      lower.startsWith("/giftapibank") ||
      lower.startsWith("/setprice") ||
      lower.startsWith("/setpay") ||
      lower.startsWith("/customers") ||
      lower.startsWith("/khach") ||
      lower.startsWith("/broadcast") ||
      lower.startsWith("/thongbao") ||
      lower === "/prices" ||
      lower === "prices" ||
      lower === "/cancel" ||
      lower === "cancel" ||
      lower === "/help" ||
      lower === "help" ||
      lower.startsWith("/start") ||
      // flow text when admin testing rent
      (!text.startsWith("/") && text.length > 0 && isRentRelated(text));

    if (adminRent && !lower.startsWith("/tiktok") && !lower.startsWith("/video") && !lower.startsWith("/giaodich") && lower !== "/gd") {
      // if clearly tiktok path skip - handled below
      try {
        const data = await callRentBot(chatId, text, true);
        if ((data.replies || []).length || data.broadcast || data.notifyTarget || data.handled !== false) {
          await deliverReplies(chatId, data);
          return res.status(200).json({ ok: true, note: "admin_rent" });
        }
      } catch (e) {
        await sendMessage(chatId, "✖ rent: " + (e.message || e));
        return res.status(200).json({ ok: true });
      }
    }

    // ========== TIKTOK ==========
    if (lower.startsWith("/tiktok") || lower.startsWith("tiktok ")) {
      const username = args[0]?.replace(/^@/, "");
      if (!username) {
        await sendMessage(chatId, "✦ Cú pháp: /tiktok {username}");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, `⏳ Đang soi @${username}...`);
        const user = await getUser(username);
        const caption = formatUserCaption(user);
        const avatar = user?.avatar || user?.avatarLarger || user?.avatarMedium;
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

    // ========== VIDEO ==========
    if (lower.startsWith("/video") || lower.startsWith("video ")) {
      const link = args[0];
      if (!link) {
        await sendMessage(chatId, "✦ Cú pháp: /video {link TikTok}");
        return res.status(200).json({ ok: true });
      }
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Đang lấy video...");
        const video = await getVideo(link);
        const caption = formatVideoCaption(video);
        const cover = video?.cover || video?.originCover;
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

    // ========== /id ==========
    if (lower === "/id" || lower === "id") {
      await sendMessage(
        chatId,
        [
          "Thông tin chat",
          `Chat ID: ${chatId}`,
          `User: ${message.from?.name || message.from?.display_name || "—"}`,
          `From ID: ${message.from?.id || "—"}`,
        ].join("\n")
      );
      return res.status(200).json({ ok: true });
    }

    // ========== /giaodich ==========
    if (
      lower === "/giaodich" ||
      lower === "giaodich" ||
      lower === "/gd" ||
      lower.startsWith("/giaodich ")
    ) {
      let waitId = null;
      try {
        waitId = await sendWaiting(chatId, "⏳ Đang lấy lịch sử MB...");
        const r = await fetch(
          "https://apimbbankvip.vercel.app/api/aduanhminh?rows=10&days=30",
          { headers: { Accept: "application/json" } }
        );
        const data = await r.json();
        await clearWaiting(chatId, waitId);
        if (data.status !== "success") {
          await sendMessage(chatId, "❌ Lỗi MB: " + (data.msg || "unknown"));
        } else {
          const bal = data.balance != null ? Number(data.balance).toLocaleString("vi-VN") + "đ" : "—";
          const txs = data.transactions || [];
          if (!txs.length) {
            await sendMessage(chatId, "📋 Không có giao dịch.\n💰 Số dư: " + bal);
          } else {
            const lines = txs.slice(0, 10).map((tx, i) => {
              const t = tx.type === "IN" ? "VÀO" : "RA";
              return `${i + 1}. [${t}] ${tx.line1 || tx.amount}\n${tx.line2 || tx.description || ""}\n${tx.line3 || ""}`;
            });
            await sendMessage(chatId, `💰 Số dư: ${bal}\n\n` + lines.join("\n\n"));
          }
        }
      } catch (e) {
        await clearWaiting(chatId, waitId);
        await sendMessage(chatId, "❌ Lỗi: " + (e.message || String(e)));
      }
      return res.status(200).json({ ok: true });
    }

    if (text && text.trim().startsWith("/")) {
      await sendMessage(
        chatId,
        `▸ Không rõ lệnh: ${text.split(/\s+/)[0]}\nGõ /help`
      );
      return res.status(200).json({ ok: true });
    }

    // no AI — ignore plain text unless rent flow already handled
    return res.status(200).json({ ok: true, note: "ignored" });
  } catch (e) {
    console.error("webhook error:", e);
    return res.status(200).json({ ok: true });
  }
};
