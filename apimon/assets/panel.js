// Hana widget 握手（对齐可工作的 todo 插件：简单 ready 消息）
parent.postMessage({ type: "ready" }, "*");

const TOKEN = new URLSearchParams(location.search).get("token") || "";
const PLUGIN_ID = (function () {
  const m = /^\/api\/plugins\/([^/]+)(?:\/|$)/.exec(location.pathname || "");
  return m ? decodeURIComponent(m[1]) : "apimon";
})();

function api(path, init) {
  const url = "/api/plugins/" + encodeURIComponent(PLUGIN_ID) + "/" + String(path).replace(/^\/+/, "");
  const o = Object.assign({}, init || {});
  const h = Object.assign({}, (init && init.headers) || {});
  if (TOKEN) h["Authorization"] = "Bearer " + TOKEN;
  o.headers = h;
  return fetch(url, o);
}

const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
const num = (n, d = 2) => (Math.round(Number(n || 0) * Math.pow(10, d)) / Math.pow(10, d)).toFixed(d);
const tok = (n) => { n = Number(n || 0); if (n >= 1e6) return (n / 1e6).toFixed(2) + "M"; if (n >= 1e3) return (n / 1e3).toFixed(1) + "K"; return String(Math.round(n)); };
const pct = (r) => (Number(r || 0) * 100).toFixed(2) + "%";

const root = document.getElementById("root");
const surface = (root && root.dataset.surface) || "widget";
let SINCE = "";
let BAL = null, BALts = 0;
try { SINCE = localStorage.getItem("apimon_since") || ""; } catch (e) {}

function keyBox(has) {
  if (has) return "";
  return '<div class="sec"><h3>配置 API Key（查余额用）</h3>'
    + '<div class="hint">只存本地插件配置；不填也能看消耗（读本地账本，不需要 key）。</div>'
    + '<div class="keyrow"><input id="keyin" type="password" placeholder="sk-...">'
    + '<button id="keysave">保存</button></div></div>';
}
async function saveKey() {
  const v = (document.getElementById("keyin").value || "").trim();
  if (!v) return;
  try { await api("key-set?key=" + encodeURIComponent(v)); } catch (e) {}
  load();
}

async function load() {
  let ks, s, bal;
  try {
    ks = await api("key-state").then((r) => r.json());
    s = await api("summary?days=7&since=" + encodeURIComponent(SINCE)).then((r) => r.json());
    if (ks && ks.has && (!BAL || Date.now() - BALts > 300000)) {
      BAL = await api("balance").then((r) => r.json()).catch(() => ({ ok: false }));
      BALts = Date.now();
    }
    bal = (ks && ks.has) ? (BAL || { ok: false }) : { ok: false };
  } catch (e) {
    root.innerHTML = '<div class="panel"><div class="empty">读取失败：' + esc(e.message) + '</div></div>';
    return;
  }
  if (!s || !s.ok) { root.innerHTML = '<div class="panel"><div class="empty">' + esc((s && s.error) || "读不到数据") + '</div></div>'; return; }

  let html = '<div class="panel"><div class="head"><span class="t">💰 API 用量</span>'
    + '<span class="sub">' + (s.since ? '自 ' + s.since + ' 起' : '账本 ' + (s.count || 0) + ' 条') + ' ｜ ' + new Date().toLocaleTimeString('zh-CN', { hour12: false }) + '</span>'
    + '<span class="sp"></span><button id="rf">刷新</button></div>'
    + '<div class="keyrow"><span class="sub">统计起始</span><input type="date" id="sinceIn" value="' + esc(SINCE) + '">'
    + '<button id="sinceSet">应用</button>' + (s.since ? '' : '<span class="sub">（默认全部历史）</span>') + '</div>';

  if (bal && bal.ok && bal.data && bal.data.balance_infos && bal.data.balance_infos.length) {
    const b = bal.data.balance_infos[0];
    html += '<div class="bal"><span class="v">' + esc(b.total_balance) + '</span><span class="u">' + esc(b.currency || "") + ' 余额</span></div>';
  } else if (ks && ks.has) {
    html += '<div class="bal"><span class="e">余额查询失败：' + esc((bal && bal.error) || "未知") + '</span></div>';
  }
  html += keyBox(ks && ks.has);

  const card = (title, o) =>
    '<div class="k"><div class="kt">' + title + '</div><div class="kv">¥' + num(o.cost, 3) + '</div>'
    + '<div class="kd">命中 ' + pct(o.hitRatio) + ' ｜ ' + tok(o.tokens) + ' tok</div>'
    + '<div class="bar"><i style="width:' + Math.min(100, o.hitRatio * 100).toFixed(1) + '%"></i></div>'
    + '<div class="kd">命中省 ¥' + num(o.saved, 4) + '</div></div>';
  html += '<div class="grid">' + card("今日", s.today) + card("近 7 天", s.win) + card("累计", s.total) + '</div>';

  const t = s.today;
  html += '<div class="sec"><h3>今日 token 拆解</h3><table>'
    + '<tr><th>项目</th><th>tokens</th><th>说明</th></tr>'
    + '<tr><td>缓存命中输入</td><td>' + tok(t.hitTok) + '</td><td class="u">便宜档</td></tr>'
    + '<tr><td>缓存未命中输入</td><td>' + tok(t.missTok) + '</td><td class="u">全价</td></tr>'
    + '<tr><td>输出</td><td>' + tok(t.outTok) + '</td><td class="u">最贵</td></tr>'
    + '<tr><td>请求数</td><td>' + t.reqs + '</td><td></td></tr></table></div>';

  const rows = (obj, label) => {
    const es = Object.entries(obj || {}).sort((a, b) => b[1].cost - a[1].cost);
    if (!es.length) return "";
    let h = '<div class="sec"><h3>' + label + '</h3><table>'
      + '<tr><th>名称</th><th>花费</th><th>tokens</th><th>命中率</th></tr>';
    es.forEach(([k, v]) => {
      h += '<tr><td title="' + esc(k) + '">' + esc(k) + '</td><td>¥' + num(v.cost, 3) + '</td><td>'
        + tok(v.tokens) + '</td><td>' + pct(v.hitRatio) + '</td></tr>';
    });
    return h + '</table></div>';
  };
  html += rows(s.byModel, "分模型（累计）");
  if (surface !== "widget") html += rows(s.byAgent, "分 Agent（累计）");

  html += '<div class="hint">价格按 DeepSeek 官方（9/10 起）：Flash 命中 0.02/0.04、未命中 1/2、输出 4/8 元/百万（空闲/高峰），按每条时间戳自动判档。</div></div>';

  root.innerHTML = html;
  const rfb = document.getElementById("rf");
  if (rfb) rfb.addEventListener("click", load);
  const ssb = document.getElementById("sinceSet");
  if (ssb) ssb.addEventListener("click", () => {
    SINCE = (document.getElementById("sinceIn").value || "");
    try { localStorage.setItem("apimon_since", SINCE); } catch (e) {}
    load();
  });
  const ksb = document.getElementById("keysave");
  if (ksb) ksb.addEventListener("click", saveKey);
}

load();
setInterval(() => { if (!document.hidden) load(); }, 30000);
