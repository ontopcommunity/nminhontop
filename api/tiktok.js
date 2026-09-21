const TIKTOK_API = process.env.TIKTOK_API_BASE || "https://tiktokvippro.vercel.app";
const SITE_BASE = process.env.SITE_BASE || "https://nminhontop.vercel.app";

function formatNumber(n) {
  n = Number(n) || 0;
  if (n < 1000) return String(n);
  if (n < 1e6) return (Math.floor(n / 100) / 10).toString().replace(".", ",") + "K";
  if (n < 1e9) return (Math.floor(n / 1e5) / 10).toString().replace(".", ",") + "M";
  return (Math.floor(n / 1e8) / 10).toString().replace(".", ",") + "B";
}

function formatDate(ts) {
  if (!ts) return "N/A";
  const d = new Date(Number(ts) * 1000);
  if (isNaN(d.getTime())) return "N/A";
  return d.toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
}

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { Accept: "application/json", "User-Agent": "ZaloBot/1.0" },
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("API trả về không phải JSON");
  }
}

async function getUser(username) {
  const clean = String(username || "").replace(/^@/, "").trim();
  if (!clean) throw new Error("Thiếu username");
  const data = await fetchJson(`${TIKTOK_API}/api?username=${encodeURIComponent(clean)}`);
  if (data.status === "Die" || data.error) {
    throw new Error(data.error || "Không tìm thấy tài khoản");
  }
  return data;
}

async function getVideo(videoUrl) {
  if (!videoUrl || !String(videoUrl).includes("tiktok")) {
    throw new Error("Link video TikTok không hợp lệ");
  }
  const data = await fetchJson(
    `${TIKTOK_API}/api/video?video=${encodeURIComponent(videoUrl)}`
  );
  if (data.error || (!data.video_data && !data.status)) {
    throw new Error(data.error || "Không lấy được video");
  }
  return data;
}

function watchUrl(videoId, uniqueId) {
  const q = new URLSearchParams();
  q.set("video", String(videoId || ""));
  if (uniqueId) q.set("user", String(uniqueId));
  return `${SITE_BASE}/tiktok?${q.toString()}`;
}

function formatUserCaption(data) {
  const a = data.author || {};
  const sf = data.stats_formatted || {};
  const sr = data.stats_raw || {};
  const ver = a.verified ? " ✓" : "";

  return [
    "━━━━━━━━━━━━━━━━",
    "⚡ THÔNG TIN TIKTOK",
    "━━━━━━━━━━━━━━━━",
    "",
    `✦ Tên: ${a.nickname || "N/A"}${ver}`,
    `✦ Username: @${a.uniqueId || "N/A"}`,
    `✦ ID: ${a.id || "N/A"}`,
    "",
    `◉ Followers  ${sf.follower || formatNumber(sr.follower)}`,
    `◉ Following  ${sf.following || formatNumber(sr.following)}`,
    `◉ Tổng tim   ${sf.heart || formatNumber(sr.heart)}`,
    `◉ Video      ${sf.video || formatNumber(sr.video)}`,
    "",
    `◷ Tạo acc: ${formatDate(a.createTime)}`,
    a.signature ? `\n◈ Bio: ${String(a.signature).replace(/\n/g, " ").slice(0, 100)}` : "",
    a.bioLink ? `◈ Link: ${a.bioLink}` : "",
    "",
    "━━━━━━━━━━━━━━━━",
  ]
    .filter((l) => l !== "")
    .join("\n");
}

function formatVideoCaption(data) {
  const a = data.author || {};
  const v = data.video_data || {};
  const s = data.stats || {};
  const ver = a.verified ? " ✓" : "";
  const page = watchUrl(v.id, a.uniqueId);

  return [
    "━━━━━━━━━━━━━━━━",
    "▶ VIDEO TIKTOK",
    "━━━━━━━━━━━━━━━━",
    "",
    `✦ Chủ kênh: ${a.nickname || "N/A"}${ver}`,
    `✦ @${a.uniqueId || "N/A"}`,
    `✦ ID: ${v.id || "N/A"}`,
    "",
    `◉ View     ${formatNumber(s.play)}`,
    `◉ Tim      ${formatNumber(s.like)}`,
    `◉ Comment  ${formatNumber(s.comment)}`,
    `◉ Share    ${formatNumber(s.share)}`,
    "",
    `◷ Đăng: ${formatDate(v.create_time)}`,
    "",
    `◈ ${String(v.description || "").replace(/\n/g, " ").slice(0, 160) || "—"}`,
    "",
    "━━━━━━━━━━━━━━━━",
    "⬇ Xem & tải tại:",
    page,
    "━━━━━━━━━━━━━━━━",
  ].join("\n");
}

module.exports = {
  getUser,
  getVideo,
  formatUserCaption,
  formatVideoCaption,
  watchUrl,
  formatNumber,
  formatDate,
  TIKTOK_API,
  SITE_BASE,
};
