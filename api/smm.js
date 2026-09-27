/**
 * SMM / Task Execution + Procurement API helpers
 * Hỗ trợ bypass Cloudflare qua FlareSolverr
 *
 * Env cần có:
 *   API_BASE, ACCESS_TOKEN, API_KEY, PHPSESSID (optional)
 *   FLARESOLVERR_URL (ví dụ: http://your-vps:8191/v1)  ← để bypass CF
 */

const API_BASE = (process.env.API_BASE || "").replace(/\/+$/, "");
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || "";
const API_KEY = process.env.API_KEY || "";
const STORED_PHPSESSID = process.env.PHPSESSID || "";
const FLARESOLVERR_URL = (process.env.FLARESOLVERR_URL || "").replace(/\/+$/, "");

// ========== PATHS ==========
const PATHS = {
  login: "/logintoken.php",
  profileSetup: "/chon_nick.php",          // thử tên gốc trước
  gateway: "/api/v2",
};

function ensureBase() {
  if (!API_BASE) throw new Error("Thiếu env API_BASE");
}

function url(path) {
  ensureBase();
  return API_BASE + path;
}

/**
 * Gọi request bình thường hoặc qua FlareSolverr nếu được cấu hình
 */
async function rawRequest(targetUrl, method = "GET", params = {}, cookie = null) {
  // Nếu có FlareSolverr thì ưu tiên dùng để bypass CF
  if (FLARESOLVERR_URL) {
    return flareRequest(targetUrl, method, params, cookie);
  }

  // Request thường
  let finalUrl = targetUrl;
  const opts = {
    method,
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      Accept: "application/json, text/javascript, */*; q=0.01",
      "X-Requested-With": "XMLHttpRequest",
      Referer: API_BASE + "/",
      Origin: API_BASE,
    },
  };
  if (cookie) opts.headers.Cookie = cookie;

  if (method === "GET") {
    const q = new URLSearchParams(params).toString();
    if (q) finalUrl += (finalUrl.includes("?") ? "&" : "?") + q;
  } else {
    opts.headers["Content-Type"] = "application/x-www-form-urlencoded";
    opts.body = new URLSearchParams(params).toString();
  }

  const res = await fetch(finalUrl, opts);
  const text = await res.text();
  return { status: res.status, body: text, headers: res.headers };
}

/**
 * Bypass Cloudflare bằng FlareSolverr
 * Docs: https://github.com/FlareSolverr/FlareSolverr
 */
async function flareRequest(targetUrl, method = "GET", params = {}, cookie = null) {
  let finalUrl = targetUrl;
  if (method === "GET" && Object.keys(params).length) {
    const q = new URLSearchParams(params).toString();
    finalUrl += (finalUrl.includes("?") ? "&" : "?") + q;
  }

  const payload = {
    cmd: method === "GET" ? "request.get" : "request.post",
    url: finalUrl,
    maxTimeout: 60000,
  };

  if (method === "POST") {
    payload.postData = new URLSearchParams(params).toString();
  }

  // Gửi cookie hiện có (PHPSESSID)
  if (cookie) {
    const match = cookie.match(/PHPSESSID=([^;]+)/i);
    if (match) {
      payload.cookies = [
        {
          name: "PHPSESSID",
          value: match[1],
          domain: new URL(API_BASE).hostname,
        },
      ];
    }
  }

  const res = await fetch(FLARESOLVERR_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();

  if (data.status !== "ok") {
    throw new Error(`FlareSolverr lỗi: ${data.message || JSON.stringify(data).slice(0, 200)}`);
  }

  const solution = data.solution || {};
  return {
    status: solution.status || 200,
    body: solution.response || "",
    headers: solution.headers || {},
    cookies: solution.cookies || [],
  };
}

async function parseJsonOrThrow(result) {
  const text = result.body || "";
  // Nếu vẫn là trang CF
  if (text.includes("Just a moment") || text.includes("cf-browser-verification")) {
    throw new Error("Vẫn bị Cloudflare chặn. Hãy kiểm tra FLARESOLVERR_URL hoặc tăng timeout.");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Không phải JSON (${result.status}): ${text.slice(0, 250)}`);
  }
}

// ========== LOGIN ==========
async function loginSession(force = false) {
  if (!force && STORED_PHPSESSID) {
    return `PHPSESSID=${STORED_PHPSESSID}`;
  }

  ensureBase();
  if (!ACCESS_TOKEN) throw new Error("Thiếu env ACCESS_TOKEN");

  const result = await rawRequest(url(PATHS.login), "POST", {
    access_token: ACCESS_TOKEN,
  });

  // Ưu tiên lấy từ Set-Cookie của response thường
  let phpsessid = null;
  if (result.headers && result.headers.get) {
    const sc = result.headers.get("set-cookie") || "";
    const m = sc.match(/PHPSESSID=([^;,\s]+)/i);
    if (m) phpsessid = m[1];
  }
  // Nếu đi qua FlareSolverr
  if (!phpsessid && result.cookies) {
    const c = result.cookies.find((x) => x.name === "PHPSESSID");
    if (c) phpsessid = c.value;
  }

  if (!phpsessid) {
    // Thử parse body xem có thông tin không
    try {
      const j = JSON.parse(result.body);
      if (j.status === "success") {
        // Login thành công nhưng không lấy được cookie → dùng stored nếu có
        if (STORED_PHPSESSID) return `PHPSESSID=${STORED_PHPSESSID}`;
      }
    } catch {}
    throw new Error(`Login fail – không lấy được PHPSESSID. Body: ${result.body.slice(0, 200)}`);
  }

  return `PHPSESSID=${phpsessid}`;
}

// ========== TASK MODULE ==========
async function doConfig(loai, id) {
  const cookie = await loginSession();
  // Thử cả 2 path phổ biến
  const pathsToTry = [PATHS.profileSetup, "/api/profile-setup.php", "/api/chon_nick.php"];
  let lastErr;
  for (const p of pathsToTry) {
    try {
      const result = await rawRequest(url(p), "GET", { loai, id, nickchay: id }, cookie);
      return await parseJsonOrThrow(result);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Không gọi được profile-setup");
}

async function doFetchTasks(type, nickchay = "", envCode = "") {
  if (!envCode) envCode = type || "1";
  const cookie = await loginSession();

  const pathsToTry = [
    `/api/${envCode}/fetch-tasks.php`,
    `/getpost.php`,
    `/api/getpost.php`,
    `/api/fetch-tasks.php`,
  ];

  let lastErr;
  for (const p of pathsToTry) {
    try {
      const params = { type };
      if (nickchay) params.nickchay = nickchay;
      const result = await rawRequest(url(p), "GET", params, cookie);
      return await parseJsonOrThrow(result);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Không lấy được nhiệm vụ");
}

async function doClaim(ids, type = "", nickchay = "", envCode = "") {
  if (!envCode) envCode = type || "1";
  const cookie = await loginSession();

  const pathsToTry = [
    `/api/${envCode}/report-completion.php`,
    `/nhantien.php`,
    `/api/nhantien.php`,
  ];

  const params = {
    id: Array.isArray(ids) ? ids.join(",") : String(ids),
  };
  if (type) params.type = type;
  if (nickchay) params.nickchay = nickchay;

  let lastErr;
  for (const p of pathsToTry) {
    try {
      const result = await rawRequest(url(p), "POST", params, cookie);
      return await parseJsonOrThrow(result);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Claim thất bại");
}

// ========== PROCUREMENT (không cần bypass) ==========
async function procurement(action, params = {}) {
  ensureBase();
  if (!API_KEY) throw new Error("Thiếu env API_KEY");

  const body = new URLSearchParams({ key: API_KEY, action, ...params });
  const res = await fetch(url(PATHS.gateway), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      Accept: "application/json",
    },
    body: body.toString(),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Gateway lỗi (${res.status}): ${text.slice(0, 200)}`);
  }
}

async function doServices() {
  return procurement("services");
}
async function doAddOrder(service, link, quantity, comments = "") {
  const p = { service, link, quantity: String(quantity) };
  if (comments) p.comments = comments;
  return procurement("add", p);
}
async function doStatus(orderOrOrders) {
  const p = {};
  if (String(orderOrOrders).includes(",")) p.orders = orderOrOrders;
  else p.order = orderOrOrders;
  return procurement("status", p);
}
async function doBalance() {
  return procurement("balance");
}
async function doCancel(order) {
  return procurement("cancel", { order });
}
async function doBoost(order) {
  return procurement("boost", { order });
}

module.exports = {
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
  PATHS,
};
