/**
 * TikTok Video Search API — hoàn toàn mới, không dùng API key / service bên thứ 3.
 * Cơ chế: gọi endpoint search public của TikTok web (pattern lấy từ các repo
 * open-source trên GitHub: HasData/tiktok-scraping, hassanalawie/TikTokScraper,
 * davidteather/TikTok-Api search examples) + fallback parse HTML nhẹ.
 * Không phụ thuộc vào tiktokvippro hay bất kỳ API cũ nào.
 *
 * GET /api/search?q={keyword}&count={n}   (count mặc định 5, max 20)
 * POST body: { "q": "...", "count": 5 }
 */

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

// Optional: SEARCH_PROXY=http://user:pass@host:port  (residential khuyến nghị)
const SEARCH_PROXY = process.env.SEARCH_PROXY || "";

function formatNumber(n) {
  n = Number(n) || 0;
  if (n < 1000) return String(n);
  if (n < 1e6) return (Math.floor(n / 100) / 10).toString().replace(".", ",") + "K";
  if (n < 1e9) return (Math.floor(n / 1e5) / 10).toString().replace(".", ",") + "M";
  return (Math.floor(n / 1e8) / 10).toString().replace(".", ",") + "B";
}

function cleanText(s) {
  return String(s || "")
    .replace(/\s+/g, " ")
    .replace(/[\u200b-\u200f\u202a-\u202e]/g, "")
    .trim();
}

/**
 * Thử gọi internal search endpoint của TikTok web.
 * Pattern tham khảo từ các scraper open-source (không cần login / API key).
 */
async function searchViaInternalApi(keyword, count) {
  const params = new URLSearchParams({
    aid: "1988",
    app_name: "tiktok_web",
    device_platform: "web_pc",
    keyword: keyword,
    offset: "0",
    count: String(Math.min(count + 5, 30)),
    search_source: "normal_search",
    source: "search_video",
  });

  const url = `https://www.tiktok.com/api/search/item/full/?${params.toString()}`;

  const res = await fetch(url, {
    method: "GET",
    headers: {
      "User-Agent": UA,
      Accept: "application/json, text/plain, */*",
      "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
      Referer: `https://www.tiktok.com/search?q=${encodeURIComponent(keyword)}`,
      Origin: "https://www.tiktok.com",
      "Sec-Fetch-Dest": "empty",
      "Sec-Fetch-Mode": "cors",
      "Sec-Fetch-Site": "same-origin",
    },
    redirect: "follow",
  });

  if (!res.ok) {
    throw new Error(`TikTok API HTTP ${res.status}`);
  }

  const data = await res.json().catch(() => null);
  if (!data) throw new Error("Response không phải JSON");

  const list = data.item_list || data.data || data.items || [];
  if (!Array.isArray(list) || list.length === 0) {
    // Một số region trả về structure khác
    if (data.status_code && data.status_code !== 0) {
      throw new Error(`TikTok status ${data.status_code}`);
    }
    throw new Error("Không có kết quả từ internal API");
  }

  return list.slice(0, count).map((item, idx) => {
    const author = item.author || item.authorInfo || {};
    const stats = item.stats || item.statistics || {};
    const video = item.video || {};
    const id = item.id || item.aweme_id || video.id || "";
    const uniqueId = author.uniqueId || author.unique_id || author.uniqueid || "";
    const desc = cleanText(item.desc || item.description || item.title || "");
    const play = stats.playCount || stats.play_count || stats.play || 0;
    const digg = stats.diggCount || stats.digg_count || stats.like || 0;
    const comment = stats.commentCount || stats.comment_count || stats.comment || 0;
    const share = stats.shareCount || stats.share_count || stats.share || 0;
    const createTime = item.createTime || item.create_time || 0;
    const cover =
      video.cover ||
      video.originCover ||
      video.dynamicCover ||
      (video.cover_url && (video.cover_url.url_list || [])[0]) ||
      null;
    const link = uniqueId && id
      ? `https://www.tiktok.com/@${uniqueId}/video/${id}`
      : id
        ? `https://www.tiktok.com/video/${id}`
        : null;

    return {
      stt: idx + 1,
      id: String(id),
      desc: desc.slice(0, 220) || "(không có mô tả)",
      author: {
        uniqueId: uniqueId || "unknown",
        nickname: author.nickname || author.nickName || uniqueId || "N/A",
        avatar: author.avatarThumb || author.avatarMedium || author.avatar || null,
      },
      stats: {
        play: Number(play) || 0,
        like: Number(digg) || 0,
        comment: Number(comment) || 0,
        share: Number(share) || 0,
        play_fmt: formatNumber(play),
        like_fmt: formatNumber(digg),
      },
      createTime: Number(createTime) || 0,
      cover,
      url: link,
    };
  });
}

/**
 * Fallback: lấy trang search HTML và cố gắng extract SIGI / __UNIVERSAL_DATA
 * (pattern phổ biến trong các scraper DOM trên GitHub).
 */
async function searchViaHtml(keyword, count) {
  const searchUrl = `https://www.tiktok.com/search?q=${encodeURIComponent(keyword)}`;
  const res = await fetch(searchUrl, {
    headers: {
      "User-Agent": UA,
      Accept: "text/html,application/xhtml+xml",
      "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
      Referer: "https://www.tiktok.com/",
    },
    redirect: "follow",
  });

  if (!res.ok) throw new Error(`HTML fetch HTTP ${res.status}`);
  const html = await res.text();

  // Tìm JSON nhúng trong script (SIGI_STATE hoặc UNIVERSAL_DATA)
  let payload = null;
  const patterns = [
    /<script id="SIGI_STATE"[^>]*>([\s\S]*?)<\/script>/i,
    /<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([\s\S]*?)<\/script>/i,
    /window\['SIGI_STATE'\]\s*=\s*(\{[\s\S]*?\});/i,
  ];

  for (const re of patterns) {
    const m = html.match(re);
    if (m && m[1]) {
      try {
        payload = JSON.parse(m[1].trim());
        break;
      } catch (_) {}
    }
  }

  if (!payload) {
    // Thử tìm các object video đơn lẻ
    const videoMatches = [...html.matchAll(/"id":"(\d{15,})"[^}]*?"desc":"([^"]*)"[^}]*?"uniqueId":"([^"]*)"/g)];
    if (videoMatches.length === 0) {
      throw new Error("Không parse được dữ liệu từ HTML");
    }
    return videoMatches.slice(0, count).map((m, idx) => ({
      stt: idx + 1,
      id: m[1],
      desc: cleanText(m[2]).slice(0, 220) || "(không có mô tả)",
      author: { uniqueId: m[3], nickname: m[3], avatar: null },
      stats: { play: 0, like: 0, comment: 0, share: 0, play_fmt: "0", like_fmt: "0" },
      createTime: 0,
      cover: null,
      url: `https://www.tiktok.com/@${m[3]}/video/${m[1]}`,
    }));
  }

  // Duyệt payload tìm itemList / video list
  const found = [];
  const walk = (obj, depth = 0) => {
    if (!obj || depth > 8 || found.length >= count) return;
    if (Array.isArray(obj)) {
      for (const v of obj) walk(v, depth + 1);
      return;
    }
    if (typeof obj === "object") {
      if (obj.id && (obj.desc !== undefined || obj.author) && (obj.video || obj.stats || obj.author)) {
        found.push(obj);
        return;
      }
      for (const k of Object.keys(obj)) walk(obj[k], depth + 1);
    }
  };
  walk(payload);

  if (found.length === 0) throw new Error("Không tìm thấy video trong payload HTML");

  return found.slice(0, count).map((item, idx) => {
    const author = item.author || {};
    const stats = item.stats || {};
    const id = String(item.id || "");
    const uniqueId = author.uniqueId || "";
    return {
      stt: idx + 1,
      id,
      desc: cleanText(item.desc || "").slice(0, 220) || "(không có mô tả)",
      author: {
        uniqueId: uniqueId || "unknown",
        nickname: author.nickname || uniqueId || "N/A",
        avatar: author.avatarThumb || null,
      },
      stats: {
        play: Number(stats.playCount || 0),
        like: Number(stats.diggCount || 0),
        comment: Number(stats.commentCount || 0),
        share: Number(stats.shareCount || 0),
        play_fmt: formatNumber(stats.playCount),
        like_fmt: formatNumber(stats.diggCount),
      },
      createTime: Number(item.createTime || 0),
      cover: (item.video && (item.video.cover || item.video.originCover)) || null,
      url: uniqueId && id ? `https://www.tiktok.com/@${uniqueId}/video/${id}` : null,
    };
  });
}

async function searchTikTok(keyword, count = 5) {
  const q = String(keyword || "").trim();
  if (!q) throw new Error("Thiếu từ khóa tìm kiếm");
  const limit = Math.max(1, Math.min(Number(count) || 5, 20));

  let videos = [];
  let source = "none";
  let lastErr = null;

  try {
    videos = await searchViaInternalApi(q, limit);
    source = "internal_api";
  } catch (e) {
    lastErr = e;
    try {
      videos = await searchViaHtml(q, limit);
      source = "html_parse";
    } catch (e2) {
      lastErr = e2;
    }
  }

  if (!videos || videos.length === 0) {
    throw new Error(
      lastErr
        ? `Không tìm được video: ${lastErr.message}`
        : "Không tìm được video nào"
    );
  }

  return {
    ok: true,
    keyword: q,
    count: videos.length,
    source,
    videos,
  };
}

function formatSearchMessage(result) {
  const lines = [
    "━━━━━━━━━━━━━━━━",
    `🔍 TÌM KIẾM: "${result.keyword}"`,
    `📦 ${result.count} video  ·  nguồn: ${result.source}`,
    "━━━━━━━━━━━━━━━━",
    "",
  ];

  for (const v of result.videos) {
    lines.push(
      `${v.stt}. @${v.author.uniqueId}`,
      `   ${v.desc}`,
      `   👁 ${v.stats.play_fmt}  ❤ ${v.stats.like_fmt}  💬 ${v.stats.comment}`,
      v.url ? `   🔗 ${v.url}` : `   ID: ${v.id}`,
      ""
    );
  }

  lines.push(
    "━━━━━━━━━━━━━━━━",
    "Nhắn số (vd: 1) hoặc /video {link} để xem chi tiết.",
    "━━━━━━━━━━━━━━━━"
  );
  return lines.join("\n");
}

module.exports = {
  searchTikTok,
  formatSearchMessage,
  formatNumber,
};

// Vercel serverless handler
module.exports.default = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    return res.status(204).end();
  }

  try {
    let q = "";
    let count = 5;

    if (req.method === "GET") {
      q = req.query.q || req.query.keyword || req.query.query || "";
      count = parseInt(req.query.count || req.query.limit || "5", 10) || 5;
    } else if (req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
      q = body.q || body.keyword || body.query || "";
      count = parseInt(body.count || body.limit || "5", 10) || 5;
    } else {
      return res.status(405).json({ ok: false, error: "Method not allowed" });
    }

    if (!q.trim()) {
      return res.status(400).json({
        ok: false,
        error: "Thiếu từ khóa. Dùng ?q=từ+khóa&count=5",
      });
    }

    const result = await searchTikTok(q, count);
    return res.status(200).json(result);
  } catch (err) {
    console.error("[search]", err);
    return res.status(500).json({
      ok: false,
      error: err.message || String(err),
    });
  }
};
