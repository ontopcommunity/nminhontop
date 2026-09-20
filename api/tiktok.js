/**
 * TikTok helper - gọi API tiktokvippro.vercel.app
 */
const TIKTOK_API = process.env.TIKTOK_API_BASE || "https://tiktokvippro.vercel.app";

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
    throw new Error("API trả về không phải JSON (có thể bị chặn)");
  }
}

/** Lấy thông tin user TikTok */
async function getUser(username) {
  const clean = String(username || "")
    .replace(/^@/, "")
    .trim();
  if (!clean) throw new Error("Thiếu username");
  const data = await fetchJson(`${TIKTOK_API}/api?username=${encodeURIComponent(clean)}`);
  if (data.status === "Die" || data.error) {
    throw new Error(data.error || "Không tìm thấy tài khoản");
  }
  return data;
}

/** Lấy thông tin video */
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

/** Tìm kiếm video */
async function searchVideos(keywords, count = 10) {
  count = Math.min(Math.max(parseInt(count, 10) || 10, 1), 20);
  const data = await fetchJson(
    `${TIKTOK_API}/api/search?keywords=${encodeURIComponent(keywords)}&count=${count}`
  );
  if (data.code === -1) throw new Error(data.error || "Lỗi search");
  const videos = data.data?.videos || data.data || [];
  if (!Array.isArray(videos) || videos.length === 0) {
    throw new Error("Không tìm thấy video (API search có thể bị giới hạn)");
  }
  return videos.slice(0, count);
}

/** Format caption thông tin user */
function formatUserCaption(data) {
  const a = data.author || {};
  const sf = data.stats_formatted || {};
  const sr = data.stats_raw || {};
  const videos = data.videos || {};
  const newest = videos.newest;
  const oldest = videos.oldest_fetched;

  let lines = [
    "📱 Thông Tin Tiktok",
    "",
    `👤 Tên: ${a.nickname || "N/A"}`,
    `🆔 Username: @${a.uniqueId || "N/A"}`,
    `🔢 ID: ${a.id || "N/A"}`,
    `👥 Followers: ${sf.follower || formatNumber(sr.follower)}`,
    `➡️ Following: ${sf.following || formatNumber(sr.following)}`,
    `❤️ Tổng tim: ${sf.heart || formatNumber(sr.heart)}`,
    `🎬 Số video: ${sf.video || formatNumber(sr.video)}`,
    `📅 Tạo acc: ${formatDate(a.createTime)}`,
  ];

  if (newest?.link) {
    lines.push(`🆕 Video mới nhất: ${newest.link}`);
  } else {
    lines.push(`🆕 Video mới nhất: N/A`);
  }
  if (oldest?.link) {
    lines.push(`📼 Video cũ (trong batch): ${oldest.link}`);
  } else {
    lines.push(`📼 Video cũ nhất: N/A`);
  }

  if (a.signature) {
    lines.push(`📝 Bio: ${String(a.signature).slice(0, 120)}`);
  }
  if (a.bioLink) {
    lines.push(`🔗 Bio link: ${a.bioLink}`);
  }
  if (videos.note) {
    lines.push(`⚠️ ${videos.note}`);
  }

  return lines.join("\n");
}

/** Format caption thông tin video */
function formatVideoCaption(data) {
  const a = data.author || {};
  const v = data.video_data || {};
  const s = data.stats || {};
  const urls = data.urls || {};

  const lines = [
    "🎬 Thông Tin Video TikTok",
    "",
    `👤 Chủ kênh: ${a.nickname || "N/A"} (@${a.uniqueId || "N/A"})`,
    `🔢 ID video: ${v.id || "N/A"}`,
    `📝 Caption: ${String(v.description || "N/A").slice(0, 300)}`,
    `📅 Ngày đăng: ${formatDate(v.create_time)}`,
    `👁 View: ${formatNumber(s.play)}`,
    `❤️ Tim: ${formatNumber(s.like)}`,
    `💬 Bình luận: ${formatNumber(s.comment)}`,
    `🔄 Chia sẻ: ${formatNumber(s.share)}`,
  ];

  if (urls.no_watermark) {
    lines.push(`⬇️ Tải không logo: ${urls.no_watermark}`);
  }
  if (a.uniqueId && v.id) {
    lines.push(`🔗 Link: https://www.tiktok.com/@${a.uniqueId}/video/${v.id}`);
  }

  return lines.join("\n");
}

/** Format danh sách search */
function formatSearchList(videos, keyword) {
  const lines = [`🔍 Kết quả tìm "${keyword}" (${videos.length} video):\n`];
  videos.forEach((v, i) => {
    const id = v.id || v.video_id || "?";
    const author = v.author?.unique_id || v.author?.uniqueId || "?";
    const title = String(v.title || v.desc || "").slice(0, 50);
    const link =
      v.link || `https://www.tiktok.com/@${author}/video/${id}`;
    lines.push(`${i + 1}. @${author} — ${title || id}`);
    lines.push(`   ${link}`);
  });
  lines.push("\n👉 Nhắn số (1, 2, 3...) để xem chi tiết video.");
  return lines.join("\n");
}

module.exports = {
  getUser,
  getVideo,
  searchVideos,
  formatUserCaption,
  formatVideoCaption,
  formatSearchList,
  formatNumber,
  formatDate,
  TIKTOK_API,
};
