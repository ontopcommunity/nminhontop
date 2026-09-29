/**
 * Cron: tự gửi báo cáo khi không ai nhắn
 * Env: REPORT_CHAT_ID (bắt buộc để gửi Zalo), ZALO_BOT_TOKEN / secret như bot
 * Vercel cron gọi GET/POST /api/cron
 */
const { sendMessage } = require("./bot");
const { statusReport } = require("./grok");

module.exports = async function handler(req, res) {
  // Bảo vệ nhẹ: Vercel Cron header hoặc CRON_SECRET
  const secret = (process.env.CRON_SECRET || "").trim();
  if (secret) {
    const h = req.headers["authorization"] || "";
    if (h !== `Bearer ${secret}`) {
      return res.status(401).json({ error: "unauthorized" });
    }
  }

  const report = statusReport();
  const chatId = (process.env.REPORT_CHAT_ID || "").trim();

  if (!chatId) {
    console.log("[cron] no REPORT_CHAT_ID, skip send:", report.replace(/\n/g, " | "));
    return res.status(200).json({
      ok: true,
      sent: false,
      note: "Set REPORT_CHAT_ID để nhận báo cáo trên Zalo",
      report,
    });
  }

  try {
    await sendMessage(chatId, report);
    return res.status(200).json({ ok: true, sent: true, chatId });
  } catch (e) {
    console.error("[cron]", e);
    return res.status(200).json({ ok: false, error: String(e.message || e) });
  }
};
