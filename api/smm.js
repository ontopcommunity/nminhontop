/**
 * SMM / Task Execution + Procurement API helpers
 * API_BASE = https://tuongtaccheo.com
 * Paths lấy đúng từ tài liệu kỹ thuật
 */

const API_BASE = (process.env.API_BASE || "").replace(/\/+$/, "");
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || "";
const API_KEY = process.env.API_KEY || "";

// ========== PATHS đúng theo tài liệu ==========
const PATHS = {
  // Auth
  login: "/auth/logintoken.php",

  // Module Vận hành Nhiệm vụ
  profileSetup: "/api/profile-setup.php",          // loai, id
  // Task fetch & claim có env_code động → xây trong hàm

  // Module Cung ứng V2
  gateway: "/api/v2/gateway.php",                  // action=services|add|status|balance
};

function ensureBase() {
  if (!API_BASE) throw new Error("Thiếu env API_BASE");
}

function url(path) {
  ensureBase();
  return API_BASE + path;
}

async function loginSession() {
  ensureBase();
  if (!ACCESS_TOKEN) throw new Error("Thiếu env ACCESS_TOKEN");

  const res = await fetch(url(PATHS.login), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": "OntopBot/1.0",
      Accept: "application/json",
    },
    body: new URLSearchParams({ access_token: ACCESS_TOKEN }).toString(),
    redirect: "manual",
  });

  // Lấy PHPSESSID từ Set-Cookie
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
      "User-Agent": "OntopBot/1.0",
      Accept: "application/json",
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
      "User-Agent": "OntopBot/1.0",
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

/** Thiết lập hồ sơ vận hành */
async function doConfig(loai, id) {
  const cookie = await loginSession();
  return taskRequest(PATHS.profileSetup, "GET", { loai, id }, cookie);
}

/**
 * Lấy nhiệm vụ
 * env_code lấy từ loai (hoặc truyền riêng)
 * Path: /api/[env_code]/fetch-tasks.php
 */
async function doFetchTasks(type, nickchay = "", envCode = "") {
  if (!envCode) envCode = type; // fallback: dùng type làm env_code nếu không truyền
  const path = `/api/${envCode}/fetch-tasks.php`;
  const cookie = await loginSession();
  const params = { type };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(path, "GET", params, cookie);
}

/**
 * Báo cáo hoàn tất & nhận thưởng
 * Path: /api/[env_code]/report-completion.php
 */
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

// ========== PROCUREMENT MODULE (gateway.php) ==========

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

// Giữ lại cancel / boost nếu panel vẫn hỗ trợ (doc mới không liệt kê nhưng không hại)
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
