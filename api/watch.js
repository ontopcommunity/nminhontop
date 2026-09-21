/**
 * Trang xem / tải video TikTok — /tiktok?video=ID&user=username
 * Dark UI + custom player
 */
const TIKTOK_API = process.env.TIKTOK_API_BASE || "https://tiktokvippro.vercel.app";

function escapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatNumber(n) {
  n = Number(n) || 0;
  if (n < 1000) return String(n);
  if (n < 1e6) return (Math.floor(n / 100) / 10).toString().replace(".", ",") + "K";
  if (n < 1e9) return (Math.floor(n / 1e5) / 10).toString().replace(".", ",") + "M";
  return (Math.floor(n / 1e8) / 10).toString().replace(".", ",") + "B";
}

function formatDate(ts) {
  if (!ts) return "—";
  const d = new Date(Number(ts) * 1000);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" });
}

async function loadVideo(videoId, user) {
  let url = videoId;
  if (/^\d{10,}$/.test(String(videoId))) {
    url = user
      ? `https://www.tiktok.com/@${user}/video/${videoId}`
      : `https://www.tiktok.com/video/${videoId}`;
  }
  const res = await fetch(
    `${TIKTOK_API}/api/video?video=${encodeURIComponent(url)}`,
    { headers: { Accept: "application/json" } }
  );
  const text = await res.text();
  if (!text.trim().startsWith("{")) throw new Error("Không lấy được dữ liệu video");
  const data = JSON.parse(text);
  if (data.error) throw new Error(data.error);
  return data;
}

function renderPage(data, errMsg) {
  if (errMsg) {
    return `<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><title>Lỗi</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0a0f;color:#eee;font-family:system-ui,sans-serif}p{opacity:.7}</style>
</head><body><div style="text-align:center"><h1>Không tải được</h1><p>${escapeHtml(errMsg)}</p></div></body></html>`;
  }

  const a = data.author || {};
  const v = data.video_data || {};
  const s = data.stats || {};
  const urls = data.urls || {};
  const music = data.music || {};
  const videoSrc = urls.no_watermark || "";
  const audioSrc = music.playUrl || "";
  const cover = urls.coverHD || urls.cover || "";
  const profile = a.uniqueId ? `https://www.tiktok.com/@${a.uniqueId}` : "#";
  const verified = a.verified
    ? `<span class="badge" title="Đã xác minh"><svg viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="12" fill="#20d5ec"/><path d="M10.2 15.6l-3.4-3.4 1.4-1.4 2 2 4.6-4.6 1.4 1.4z" fill="#0a0a0f"/></svg></span>`
    : "";

  return `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#0a0a0f"/>
<title>${escapeHtml(a.nickname || "TikTok")} · Ontop</title>
<style>
  :root {
    --bg: #0a0a0f;
    --card: #12121a;
    --line: #1e1e2a;
    --text: #f2f2f7;
    --muted: #8b8b9e;
    --accent: #fe2c55;
    --accent2: #25f4ee;
    --ok: #20d5ec;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    background: radial-gradient(1200px 600px at 10% -10%, #1a1020 0%, transparent 50%),
                radial-gradient(900px 500px at 100% 0%, #0d1a22 0%, transparent 45%),
                var(--bg);
    color: var(--text);
    min-height: 100vh;
    line-height: 1.45;
  }
  .wrap {
    max-width: 480px;
    margin: 0 auto;
    padding: 20px 16px 48px;
  }
  .brand {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 18px; opacity: .9;
  }
  .brand .logo {
    width: 32px; height: 32px; border-radius: 10px;
    background: linear-gradient(135deg, var(--accent), #ff6b35);
    display: grid; place-items: center; font-weight: 800; font-size: 14px;
  }
  .brand span { font-weight: 700; letter-spacing: .02em; font-size: 15px; }
  .player-shell {
    position: relative;
    border-radius: 18px;
    overflow: hidden;
    background: #000;
    border: 1px solid var(--line);
    box-shadow: 0 20px 50px rgba(0,0,0,.45);
    aspect-ratio: 9/16;
    max-height: 70vh;
  }
  .player-shell video {
    width: 100%; height: 100%; object-fit: contain; display: block;
    background: #000;
  }
  .player-ui {
    position: absolute; inset: 0;
    display: flex; flex-direction: column; justify-content: flex-end;
    pointer-events: none;
  }
  .player-ui .top-grad {
    position: absolute; inset: 0;
    background: linear-gradient(transparent 50%, rgba(0,0,0,.75) 100%);
    pointer-events: none;
  }
  .controls {
    position: relative; z-index: 2;
    padding: 12px 14px 14px;
    display: flex; flex-direction: column; gap: 10px;
    pointer-events: auto;
  }
  .progress {
    height: 4px; background: rgba(255,255,255,.2); border-radius: 99px;
    cursor: pointer; position: relative;
  }
  .progress .bar {
    height: 100%; width: 0%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
    border-radius: 99px;
  }
  .row {
    display: flex; align-items: center; gap: 12px;
  }
  .btn-play {
    width: 44px; height: 44px; border-radius: 50%;
    border: none; cursor: pointer;
    background: rgba(255,255,255,.12);
    backdrop-filter: blur(8px);
    color: #fff; display: grid; place-items: center;
    transition: transform .15s, background .15s;
  }
  .btn-play:hover { background: rgba(255,255,255,.22); transform: scale(1.05); }
  .time { font-size: 12px; color: rgba(255,255,255,.75); font-variant-numeric: tabular-nums; }
  .center-play {
    position: absolute; inset: 0; display: grid; place-items: center;
    z-index: 3; pointer-events: none;
  }
  .center-play button {
    pointer-events: auto;
    width: 72px; height: 72px; border-radius: 50%;
    border: none; cursor: pointer;
    background: rgba(254,44,85,.9);
    color: #fff; display: grid; place-items: center;
    box-shadow: 0 8px 32px rgba(254,44,85,.4);
    transition: transform .15s, opacity .2s;
  }
  .center-play button.hidden { opacity: 0; pointer-events: none; transform: scale(.8); }
  .actions {
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
    margin-top: 16px;
  }
  .dl {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 14px 12px; border-radius: 14px;
    text-decoration: none; font-weight: 700; font-size: 14px;
    border: 1px solid var(--line);
    transition: transform .15s, border-color .15s, background .15s;
  }
  .dl:hover { transform: translateY(-1px); }
  .dl-video {
    background: linear-gradient(135deg, #fe2c55, #ff5a36);
    color: #fff; border-color: transparent;
  }
  .dl-audio {
    background: var(--card); color: var(--text);
  }
  .dl-audio:hover { border-color: var(--accent2); }
  .card {
    margin-top: 18px;
    background: var(--card);
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 16px;
  }
  .author {
    display: flex; align-items: center; gap: 12px;
    text-decoration: none; color: inherit;
  }
  .author img {
    width: 48px; height: 48px; border-radius: 50%;
    object-fit: cover; border: 2px solid var(--line);
  }
  .author .name {
    font-weight: 700; font-size: 16px;
    display: flex; align-items: center; gap: 6px;
  }
  .author .user { color: var(--muted); font-size: 13px; margin-top: 2px; }
  .badge { display: inline-flex; vertical-align: middle; }
  .caption {
    margin-top: 14px; font-size: 14px; color: #d8d8e4;
    white-space: pre-wrap; word-break: break-word;
  }
  .stats {
    margin-top: 16px;
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  }
  .stat {
    background: #0e0e16;
    border-radius: 12px; padding: 10px 6px; text-align: center;
    border: 1px solid var(--line);
  }
  .stat b { display: block; font-size: 14px; }
  .stat span { font-size: 11px; color: var(--muted); }
  .meta {
    margin-top: 14px; font-size: 12px; color: var(--muted);
    display: flex; flex-wrap: wrap; gap: 10px 16px;
  }
  .foot {
    margin-top: 24px; text-align: center;
    font-size: 12px; color: var(--muted);
  }
  @media (min-width: 520px) {
    .player-shell { aspect-ratio: 9/14; }
  }
</style>
</head>
<body>
  <div class="wrap">
    <div class="brand"><div class="logo">OT</div><span>Ontop · TikTok</span></div>

    <div class="player-shell" id="shell">
      <video id="vid" playsinline preload="metadata" poster="${escapeHtml(cover)}" src="${escapeHtml(videoSrc)}"></video>
      <div class="player-ui">
        <div class="top-grad"></div>
        <div class="center-play"><button type="button" id="bigPlay" aria-label="Play">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </button></div>
        <div class="controls">
          <div class="progress" id="seek"><div class="bar" id="bar"></div></div>
          <div class="row">
            <button type="button" class="btn-play" id="playBtn" aria-label="Play/Pause">
              <svg id="iconPlay" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
              <svg id="iconPause" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style="display:none"><path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>
            </button>
            <span class="time"><span id="cur">0:00</span> / <span id="dur">0:00</span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="actions">
      <a class="dl dl-video" id="dlVideo" href="${escapeHtml(videoSrc)}" download="tiktok-${escapeHtml(v.id || "video")}.mp4" target="_blank" rel="noopener">⬇ Tải video</a>
      <a class="dl dl-audio" id="dlAudio" href="${escapeHtml(audioSrc || "#")}" ${audioSrc ? `download="tiktok-audio.mp3" target="_blank" rel="noopener"` : `onclick="alert('Không có link âm thanh');return false;"`}>♪ Tải âm thanh</a>
    </div>

    <div class="card">
      <a class="author" href="${escapeHtml(profile)}" target="_blank" rel="noopener">
        <img src="${escapeHtml(a.avatar || a.avatarHD || cover)}" alt="" onerror="this.style.display='none'"/>
        <div>
          <div class="name">${escapeHtml(a.nickname || "Unknown")} ${verified}</div>
          <div class="user">@${escapeHtml(a.uniqueId || "—")}</div>
        </div>
      </a>
      <div class="caption">${escapeHtml(v.description || "")}</div>
      <div class="stats">
        <div class="stat"><b>${formatNumber(s.play)}</b><span>View</span></div>
        <div class="stat"><b>${formatNumber(s.like)}</b><span>Tim</span></div>
        <div class="stat"><b>${formatNumber(s.comment)}</b><span>BL</span></div>
        <div class="stat"><b>${formatNumber(s.share)}</b><span>Share</span></div>
      </div>
      <div class="meta">
        <span>◷ ${escapeHtml(formatDate(v.create_time))}</span>
        <span>ID ${escapeHtml(v.id || "—")}</span>
        ${s.download ? `<span>⬇ ${formatNumber(s.download)} lưu</span>` : ""}
      </div>
    </div>

    <p class="foot">Ontopcommunity · không logo từ API</p>
  </div>
<script>
(function(){
  const vid = document.getElementById('vid');
  const playBtn = document.getElementById('playBtn');
  const bigPlay = document.getElementById('bigPlay');
  const iconPlay = document.getElementById('iconPlay');
  const iconPause = document.getElementById('iconPause');
  const bar = document.getElementById('bar');
  const seek = document.getElementById('seek');
  const cur = document.getElementById('cur');
  const dur = document.getElementById('dur');

  function fmt(t){
    if (!isFinite(t)) return '0:00';
    t = Math.floor(t);
    const m = Math.floor(t/60), s = t%60;
    return m + ':' + String(s).padStart(2,'0');
  }
  function syncIcons(playing){
    iconPlay.style.display = playing ? 'none' : 'block';
    iconPause.style.display = playing ? 'block' : 'none';
    bigPlay.classList.toggle('hidden', playing);
  }
  function toggle(){
    if (vid.paused) vid.play(); else vid.pause();
  }
  playBtn.addEventListener('click', toggle);
  bigPlay.addEventListener('click', toggle);
  vid.addEventListener('click', toggle);
  vid.addEventListener('play', () => syncIcons(true));
  vid.addEventListener('pause', () => syncIcons(false));
  vid.addEventListener('timeupdate', () => {
    const p = vid.duration ? (vid.currentTime / vid.duration) * 100 : 0;
    bar.style.width = p + '%';
    cur.textContent = fmt(vid.currentTime);
  });
  vid.addEventListener('loadedmetadata', () => { dur.textContent = fmt(vid.duration); });
  seek.addEventListener('click', (e) => {
    const r = seek.getBoundingClientRect();
    const ratio = (e.clientX - r.left) / r.width;
    if (vid.duration) vid.currentTime = ratio * vid.duration;
  });
})();
</script>
</body>
</html>`;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const video = req.query.video || req.query.v || req.query.id;
  const user = req.query.user || req.query.u || "";

  if (!video) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.status(400).send(renderPage(null, "Thiếu tham số ?video=ID"));
  }

  try {
    const data = await loadVideo(video, user);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("Cache-Control", "public, s-maxage=60, stale-while-revalidate=300");
    return res.status(200).send(renderPage(data, null));
  } catch (e) {
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.status(500).send(renderPage(null, e.message || "Lỗi server"));
  }
};
