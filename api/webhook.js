// Zalo Bot Webhook Handler
// Secret Token must match the one set in Zalo Bot settings

const SECRET_TOKEN = process.env.ZALO_SECRET_TOKEN || "abc-xyz-123";

module.exports = async function handler(req, res) {
  // Only accept POST
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Verify Secret Token from header
  const receivedToken = req.headers["x-bot-api-secret-token"];
  if (receivedToken !== SECRET_TOKEN) {
    console.warn("Invalid secret token received");
    return res.status(403).json({ error: "Forbidden" });
  }

  try {
    const body = req.body;
    console.log("Received Zalo webhook event:", JSON.stringify(body, null, 2));

    // TODO: Handle different event types here
    // e.g. message received, etc.

    // Always return 200 quickly so Zalo knows we received it
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("Webhook error:", err);
    return res.status(500).json({ error: "Internal error" });
  }
};
