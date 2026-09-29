import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const HANA_HOME = process.env.HANA_HOME || path.join(os.homedir(), ".hanako");
const LEDGER = path.join(HANA_HOME, "usage-ledger.json");

// DeepSeek 官方价（元 / 百万 tokens）· 2026-09-10 起
// 高峰 = 北京时间 周一至周五 9:00-12:00、14:00-18:00，其余空闲（空闲价 = 高峰半价）
const PRICE = {
  flash: { hit: { peak: 0.04, off: 0.02 }, miss: { peak: 2.0, off: 1.0 }, out: { peak: 8.0, off: 4.0 } },
  pro:   { hit: { peak: 0.30, off: 0.15 }, miss: { peak: 9.0, off: 4.5 }, out: { peak: 27.0, off: 13.5 } },
};
const priceOf = (m) => /pro/i.test(String(m || "")) ? PRICE.pro : PRICE.flash;

function bj(iso) {
  const t = new Date(iso);
  if (isNaN(t.getTime())) return null;
  const d = new Date(t.getTime() + 8 * 3600e3);
  const y = d.getUTCFullYear(), mo = d.getUTCMonth() + 1, da = d.getUTCDate();
  return { hh: d.getUTCHours(), dow: d.getUTCDay(),
           key: `${y}-${String(mo).padStart(2, "0")}-${String(da).padStart(2, "0")}` };
}
const isPeak = (p) => !!p && p.dow >= 1 && p.dow <= 5 && ((p.hh >= 9 && p.hh < 12) || (p.hh >= 14 && p.hh < 18));
const blank = () => ({ hitTok: 0, missTok: 0, outTok: 0, tokens: 0, cost: 0, reqs: 0 });
function add(a, h, m, o, c) { a.hitTok += h; a.missTok += m; a.outTok += o; a.tokens += h + m + o; a.cost += c; a.reqs++; }
const costOf = (h, m, o, pr, peak) => { const k = peak ? "peak" : "off";
  return h / 1e6 * pr.hit[k] + m / 1e6 * pr.miss[k] + o / 1e6 * pr.out[k]; };
const ratio = (a) => (a.hitTok + a.missTok) ? a.hitTok / (a.hitTok + a.missTok) : 0;

function scan(days, since) {
  let d;
  try { d = JSON.parse(fs.readFileSync(LEDGER, "utf8")); }
  catch (e) { return { ok: false, error: "读不到用量账本：" + e.message, ledger: LEDGER }; }
  const entries = Array.isArray(d.entries) ? d.entries : [];
  const nowKey = (bj(new Date().toISOString()) || {}).key || "";
  const sinceTs = since ? new Date(since + "T00:00:00+08:00").getTime() : null;
  const out = { ok: true, today: blank(), win: blank(), total: blank(),
                byModel: {}, byAgent: {}, count: entries.length, ledger: LEDGER, days: days || 0, since: since || "" };
  for (const e of entries) {
    const u = e.usage; if (!u) continue;
    const iso = e.startedAt || e.endedAt;
    if (sinceTs && iso && new Date(iso).getTime() < sinceTs) continue;
    const p = iso ? bj(iso) : null;
    const pr = priceOf((e.model || {}).modelId);
    const h = Number((u.cache || {}).readTokens || 0);
    const m = Number((u.input || {}).uncachedTokens || 0);
    const o = Number((u.output || {}).totalTokens || 0);
    const c = costOf(h, m, o, pr, isPeak(p));
    add(out.total, h, m, o, c);
    if (p && p.key === nowKey) add(out.today, h, m, o, c);
    if (days > 0 && iso && new Date(iso) >= new Date(Date.now() - days * 864e5)) add(out.win, h, m, o, c);
    const mk = (e.model || {}).modelId || "?";
    (out.byModel[mk] = out.byModel[mk] || blank(), add(out.byModel[mk], h, m, o, c));
    const ag = (e.attribution || {}).agentId || "?";
    (out.byAgent[ag] = out.byAgent[ag] || blank(), add(out.byAgent[ag], h, m, o, c));
  }
  for (const k of ["today", "win", "total"]) out[k].hitRatio = ratio(out[k]);
  for (const k of Object.keys(out.byModel)) out.byModel[k].hitRatio = ratio(out.byModel[k]);
  const savedPer = (t) => t / 1e6 * (PRICE.flash.miss.off - PRICE.flash.hit.off);
  out.today.saved = savedPer(out.today.hitTok);
  out.win.saved = savedPer(out.win.hitTok);
  out.total.saved = savedPer(out.total.hitTok);
  return out;
}

function keyFile(ctx) { return path.join(ctx.dataDir, "config.json"); }
function getKey(ctx) {
  try { const c = JSON.parse(fs.readFileSync(keyFile(ctx), "utf8")); if (c && c.apiKey) return String(c.apiKey).trim(); } catch (_) {}
  try { return String(ctx.config.get("apiKey") || "").trim(); } catch (_) { return ""; }
}
function setKey(ctx, k) {
  try { fs.mkdirSync(ctx.dataDir, { recursive: true }); } catch (_) {}
  fs.writeFileSync(keyFile(ctx), JSON.stringify({ apiKey: String(k || "").trim() }, null, 1), "utf8");
}

function esc(v) {
  return String(v).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}
function renderShell(c, ctx, surface) {
  const hanaCss = c.req.query("hana-css") || "";
  const theme = c.req.query("hana-theme") || "inherit";
  let css = "", js = "";
  try { css = fs.readFileSync(path.join(ctx.pluginDir, "assets", "panel.css"), "utf8"); } catch (_) {}
  try { js = fs.readFileSync(path.join(ctx.pluginDir, "assets", "panel.js"), "utf8"); } catch (_) {}
  return `<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>API 用量</title>
${hanaCss ? `<link rel="stylesheet" href="${esc(hanaCss)}">` : ""}
<style>${css}</style>
</head><body data-hana-theme="${esc(theme)}" data-surface="${esc(surface)}">
<div id="root" data-surface="${esc(surface)}"></div>
<script>${js}</script>
</body></html>`;
}

export default function (app, ctx) {
  app.get("/widget", (c) => c.html(renderShell(c, ctx, "widget")));
  app.get("/page", (c) => c.html(renderShell(c, ctx, "page")));

  app.get("/summary", (c) => c.json(scan(Number(c.req.query("days") || 0) || 0, c.req.query("since") || "")));

  app.get("/balance", async (c) => {
    const key = getKey(ctx);
    if (!key) return c.json({ ok: false, error: "未配置 API Key" });
    try {
      const r = await ctx.network.fetch("https://api.deepseek.com/user/balance", {
        method: "GET", headers: { Authorization: "Bearer " + key, Accept: "application/json" },
      });
      const body = typeof r === "string" ? r : await r.text();
      return c.json({ ok: true, data: JSON.parse(body) });
    } catch (e) { return c.json({ ok: false, error: String(e).slice(0, 240) }); }
  });

  app.get("/key-state", (c) => c.json({ ok: true, has: !!getKey(ctx) }));
  app.get("/key-set", (c) => { setKey(ctx, c.req.query("key") || ""); return c.json({ ok: true }); });
}
