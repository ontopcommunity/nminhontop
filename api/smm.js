/**
 * SMM / Task Execution + Procurement API helpers
 * Tất cả endpoint + token lấy từ env (Vercel)
 */

const ACCESS_TOKEN = process.env.ACCESS_TOKEN || "";
const API_KEY = process.env.API_KEY || "";

const API_LOGIN = process.env.API_LOGIN || "";
const API_CONFIG = process.env.API_CONFIG || "";
const API_TASKS = process.env.API_TASKS || "";
const API_CLAIM = process.env.API_CLAIM || "";
const API_PROCUREMENT = process.env.API_PROCUREMENT || ""; // endpoint chung POST action=...

function ensure(name, val) {
  if (!val) throw new Error(`Thiếu env ${name}. Hãy set trên Vercel.`);
}

async function loginSession() {
  ensure("API_LOGIN", API_LOGIN);
  ensure("ACCESS_TOKEN", ACCESS_TOKEN);

  const res = await fetch(API_LOGIN, {
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

async function taskRequest(url, method = "GET", params = {}, cookie = null) {
  ensure("API_* task", url);
  let finalUrl = url;
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
    if (q) finalUrl += (url.includes("?") ? "&" : "?") + q;
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
  ensure("API_PROCUREMENT", API_PROCUREMENT);
  ensure("API_KEY", API_KEY);

  const body = new URLSearchParams({ key: API_KEY, action, ...params });
  const res = await fetch(API_PROCUREMENT, {
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
  return taskRequest(API_CONFIG, "GET", { loai, id }, cookie);
}

async function doFetchTasks(type, nickchay = "") {
  const cookie = await loginSession();
  const params = { type };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(API_TASKS, "GET", params, cookie);
}

async function doClaim(ids, nickchay = "") {
  const cookie = await loginSession();
  const params = { id: Array.isArray(ids) ? ids.join(",") : String(ids) };
  if (nickchay) params.nickchay = nickchay;
  return taskRequest(API_CLAIM, "POST", params, cookie);
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
};
