// Zalo Bot Webhook Handler
const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN || "5-r-FcilN7xnTfZm0n";
const BOT_TOKEN = process.env.ZALO_BOT_TOKEN || "3415615569922217583:GOsmyGCVFMUxhXvOQXQKGNAKYYvpwovhxCwtCWlzMNpLqDJcdYfgOSSQqLaNUpQc";
const API_BASE = `https://bot-api.zaloplatforms.com/bot${BOT_TOKEN}`;

async function sendMessage(chatId, text) {
  try {
    const res = await fetch(`${API_BASE}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    const data = await res.json();
    console.log("sendMessage result:", JSON.stringify(data));
    return data;
  } catch (err) {
    console.error("sendMessage error:", err);
    return null;
  }
}

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

    // Payload có thể là { ok, result: { event_name, message } } hoặc trực tiếp event
    const event = body.result || body;
    const eventName = event.event_name || body.event_name;
    const message = event.message || body.message;

    if (message && message.chat && message.chat.id) {
      const chatId = message.chat.id;
      const text = message.text || "";

      console.log(`Message from chat ${chatId}: ${text}`);

      // Auto reply
      if (text) {
        await sendMessage(chatId, `Bot nhận được: ${text}`);
      } else {
        await sendMessage(chatId, "Bot đã nhận tin nhắn của bạn (không phải text).");
      }
    }

    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    // Vẫn trả 200 để Zalo không retry liên tục
    return res.status(200).json({ ok: true, error: String(err.message) });
  }
};
