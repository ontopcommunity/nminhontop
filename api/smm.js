/**
 * SMM / Task Execution + Procurement API helpers
 * API_BASE = https://tuongtaccheo.com
 * Ưu tiên dùng PHPSESSID từ env, chỉ login lại khi cần
 */

const API_BASE = (process.env.API_BASE || "").replace(/\/+$/, "");
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || "";
const API_KEY = process.env.API_KEY || "";
const STORED_PHPSESSID = process.env.PHPSESSID || "";

// ========== PATHS (đã xác thực thực tế) ==========
const PATHS = {
  login: "/logintoken.php",                        // POST access_token → PHPSESSID + JSON
  profileSetup: "/api/profile-setup.php",          // loai, id
  gateway: "/api/v2",                               // action=services|add|status|balance (đã test OK)
};

function ensureBase() {
  if (!API_BASE) throw new Error("Thiếu env API_BASE");
}

function url(path) {
  ensureBase();
  return API_BASE + path;
}

/**
 * Ưu tiên dùng PHPSESSID đã lưu trong env.
 * Nếu không có hoặc force=true thì login mới.
 */
async function loginSession(force = false) {
  if (!force && STORED_PHPSESSID) {
    return `PHPSESSID=${STORED_PHPSESSID}`;
  }

  ensureBase();
  if (!ACCESS_TOKEN) throw new Error("Thiếu env ACCESS_TOKEN");

  const res = await fetch(url(PATHS.login), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      Accept: "application/json",
    },
    body: new URLSearchParams({ access_token: ACCESS_TOKEN }).toString(),
    redirect: "manual",
  });

  const setCookie = res.headers.getSetCookie
    ? res.headers.getSetCookie().join(";")
    : res.headers.get("set-cookie") || "";

  const match = setCookie.match(/PHPSESSID=([^;,\s]+)/i);
  if (!match) {
    const text = await res.text().catch(() => "");
    throw new Error(`Login fail – không nhận PHPSESSID. Status ${res.status}. Body: ${text.slice(0, 250)}`);
  }
  return `PHPSESSID=${match[1]}`;
}

async function taskRequest(path, method = "GET", params = {}, cookie = null) {
  let finalUrl = url(path);
  const opts = {
    method,
    headers: {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      Accept: "application/json, text/plain, */*",
      "X-Requested-With": "XMLHttpRequest",
      Referer: API_BASE + "/",
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
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`API không phải JSON (${res.status}): ${text.slice(0, 200)}`);
  }
}

async function procurement(action, params = {}) {
  ensureBase();
  if (!API_KEY) throw new Error("Thiếu env API_KEY");

  const body = new URLSearchParams({ key: API_KEY, action, ...params });
  const res = await fetch(url(PATHS.gateway), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

// ========== TASK MODULE ==========

async function doConfig(loai, id) {
  const cookie = await loginSession();
  return taskRequest(PATHS.profileSetup, "GET", { loai, id }, cookie);
}

async function doFetchTasks(type, nickchay = "", envCode = "") {
  if (!envCode) envCode = type;
  const path = `/api/${envCode}/fetch-tasks.php`;
  const cookie = await loginSession();
  const params = { type };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(path, "GET", params, cookie);
}

async function doClaim(ids, type = "", nickchay = "", envCode = "") {
  if (!envCode) envCode = type;
  const path = `/api/${envCode}/report-completion.php`;
  const cookie = await loginSession();
  const params = {
    id: Array.isArray(ids) ? ids.join(",") : String(ids),
  };
  if (type) params.type = type;
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(path, "POST", params, cookie);
}

// ========== PROCUREMENT MODULE ==========

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
