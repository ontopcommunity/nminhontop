/**
 * SMM / Task Execution + Procurement API helpers
 * Chỉ cần 1 env link: API_BASE
 * Các path cụ thể được chia sẵn trong code
 */

const API_BASE = (process.env.API_BASE || "").replace(/\/+$/, ""); // bỏ dấu / cuối
const ACCESS_TOKEN = process.env.ACCESS_TOKEN || "";
const API_KEY = process.env.API_KEY || "";

// ========== PATHS (chia sẵn trong mã nguồn) ==========
// Mày chỉ cần set API_BASE = https://domain.com
// Các endpoint bên dưới sẽ tự ghép
const PATHS = {
  // Module Vận hành Nhiệm vụ
  login: "/api/login",           // POST access_token → nhận PHPSESSID
  config: "/api/config",         // GET loai, id
  tasks: "/api/tasks",           // GET type, nickchay
  claim: "/api/claim",           // POST id, nickchay

  // Module Cung ứng (thường là 1 endpoint chung)
  procurement: "/api/v2",        // POST key + action=services|add|status|balance|cancel|boost
};

function ensureBase() {
  if (!API_BASE) throw new Error("Thiếu env API_BASE. Hãy set trên Vercel (ví dụ: https://panel.example.com)");
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
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ access_token: ACCESS_TOKEN }).toString(),
    redirect: "manual",
  });

  const setCookie = res.headers.get("set-cookie") || "";
  const match = setCookie.match(/PHPSESSID=([^;]+)/i);
  if (!match) {
    const text = await res.text().catch(() => "");
    throw new Error(`Login fail – không nhận được PHPSESSID. Status ${res.status}. Body: ${text.slice(0, 200)}`);
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
    throw new Error(`API trả về không phải JSON (${res.status}): ${text.slice(0, 180)}`);
  }
}

async function procurement(action, params = {}) {
  ensureBase();
  if (!API_KEY) throw new Error("Thiếu env API_KEY");

  const body = new URLSearchParams({ key: API_KEY, action, ...params });
  const res = await fetch(url(PATHS.procurement), {
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
    throw new Error(`Procurement lỗi (${res.status}): ${text.slice(0, 180)}`);
  }
}

// ========== TASK MODULE ==========
async function doConfig(loai, id) {
  const cookie = await loginSession();
  return taskRequest(PATHS.config, "GET", { loai, id }, cookie);
}

async function doFetchTasks(type, nickchay = "") {
  const cookie = await loginSession();
  const params = { type };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(PATHS.tasks, "GET", params, cookie);
}

async function doClaim(ids, nickchay = "") {
  const cookie = await loginSession();
  const params = { id: Array.isArray(ids) ? ids.join(",") : String(ids) };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(PATHS.claim, "POST", params, cookie);
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
