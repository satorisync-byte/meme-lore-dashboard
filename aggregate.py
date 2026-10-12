#!/usr/bin/env python3
"""Radar Meme & Lore: raccoglie meme e narrative (Know Your Meme, kym.fun, knowyourmemecoin, 4chan /biz/, Reddit RSS),
calcola un punteggio, verifica lo stato su Solana (DexScreener + pump.fun) e genera index.html + data.json."""
import json, re, time, html, hashlib, math, os, sys
from email.utils import parsedate_to_datetime
from collections import defaultdict
import requests, feedparser

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) MemeLoreDashboard/1.0 (+https://github.com/satorisync-byte/meme-lore-dashboard)"}
MAX_AGE_H = 120  # freschezza: 5 giorni
NOW = time.time()
FONTI = []  # stato fonti per il footer
SUBS = ["CryptoCurrency", "CryptoMoonShots", "dogecoin", "cryptocurrencymemes", "memecoins", "SolanaMemeCoins", "SatoshiStreetBets",
        "Memecoinhub", "AllCryptoBets", "shitcoinmoonshots", "solana", "EthTrader", "Crypto_General"]
STOP = set("""the a an of and or to in on for with is are was be by at from it its this that as you your my me i we our not no but all just
what who how why when will can get got new now one out up so do does don't dont im it's like more than vs via meme memes about after into
still over day year he she they them his her their has have had there here any some been would could should also only very much many
biz thread general anon anons anyone guys post buy sell coin coins crypto token tokens price market money pump dump moon chart""".split())
S = requests.Session(); S.headers.update(UA)

def h8(s): return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:10]
def load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def save(p, o, ind=None): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=ind, separators=None if ind else (",", ":"))
def strip(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", "\n", s or ""))))).strip()
def words(s): return [w for w in re.findall(r"[a-z0-9']{3,}", s.lower()) if w not in STOP]
def fonte(nome, ok, n=0, nota=""): FONTI.append({"nome": nome, "ok": ok, "n": n, "nota": nota})

def get(url, **kw):
    time.sleep(0.6)  # ritmo cortese
    return S.get(url, timeout=kw.pop("timeout", 15), **kw)

# ---------- Know Your Meme ----------
def kym_feed(url, nome, tipo):
    out = []
    try:
        r = get(url)
        if r.status_code != 200 or "<rss" not in r.text[:500]:
            cf = "cloudflare" in r.text.lower() or r.status_code in (403, 503)
            fonte(nome, False, 0, f"HTTP {r.status_code}" + (" (Cloudflare)" if cf else "")); return out
        f = feedparser.parse(r.content)
        for e in f.entries:
            try: ts = parsedate_to_datetime(e.published).timestamp()
            except Exception: ts = NOW
            desc = e.get("summary", ""); m = re.search(r'<img[^>]+src="([^"]+)"', desc)
            summ = strip(re.sub(r"<a[^>]*>Read More</a>", "", desc))
            out.append({"titolo": strip(e.title), "link": e.link, "fonte": nome, "tipo": tipo, "ts": ts, "img": m and m.group(1),
                        "lore": summ[:420] + ("…" if len(summ) > 420 else ""), "viral": {"kym_confermato": 26, "kym_proposta": 16, "kym_news": 18}[tipo]})
        fonte(nome, True, len(out))
    except Exception as ex: fonte(nome, False, 0, type(ex).__name__)
    return out

# ---------- Lore già tokenizzata: kym.fun + knowyourmemecoin ----------
def lore_refs():
    refs = []
    try:
        r = get("https://www.kym.fun/memes/launched")
        n0 = len(refs)
        for href in dict.fromkeys(re.findall(r'href="(/memes/[^"?#]+)"', r.text)):
            slug = href.rsplit("/", 1)[-1]
            if slug in ("launched", "popular") or "/" in href[7:]: continue
            from urllib.parse import unquote
            refs.append({"titolo": unquote(slug).replace("-", " ").title(), "link": "https://www.kym.fun" + href, "fonte": "kym.fun"})
        fonte("kym.fun (meme lanciati)", r.status_code == 200, len(refs) - n0, "" if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as ex: fonte("kym.fun (meme lanciati)", False, 0, type(ex).__name__)
    try:
        r = get("https://knowyourmemecoin.com/"); n0 = len(refs)
        for slug in dict.fromkeys(re.findall(r'href="/coin/([a-z0-9-]+)"', r.text)):
            refs.append({"titolo": slug.replace("-", " ").title(), "link": "https://knowyourmemecoin.com/coin/" + slug, "fonte": "knowyourmemecoin"})
        fonte("knowyourmemecoin.com", r.status_code == 200, len(refs) - n0, "" if r.status_code == 200 else f"HTTP {r.status_code}")
    except Exception as ex: fonte("knowyourmemecoin.com", False, 0, type(ex).__name__)
    return refs

# ---------- 4chan /biz/ ----------
TICK_RE = re.compile(r"(?<![A-Za-z0-9])\$([A-Za-z][A-Za-z0-9]{1,9})\b")
NOT_TICK = set("""USD BTC ETH SOL USDT USDC XRP XRPL XRPUSD BNB ADA LINK SPY QQQ TSLA NVDA SEC CEO NOT CRYPTO ANTI FUD FUCK WITH AND ALL BUY SELL THIS THE
FDIC DTCC DRS ITM OTM ATH ICO IPO ETF CPI FED GDP USA LOL KEK NGMI WAGMI HODL YOU ARE FOR WHY HOW WHAT JUST NEW NOW CENT MONDAY TUESDAY FRIDAY
MINING NEET OKAY IRS AMA DCA API NFT DEX CEX TLDR EDIT LMAO WTF OMG SHIT""".split())
CAPS_RE = re.compile(r"\b[A-Z][A-Z0-9]{2,5}\b")
def biz():
    try:
        r = get("https://a.4cdn.org/biz/catalog.json")
        threads = [t for p in r.json() for t in p["threads"] if not t.get("sticky")]
    except Exception as ex:
        fonte("4chan /biz/", False, 0, type(ex).__name__); return [], ""
    tick = defaultdict(list); terms = defaultdict(list); corpus = []
    for t in threads:
        txt = strip((t.get("sub") or "") + " \n " + (t.get("com") or "")) + " " + " ".join(strip(x.get("com")) for x in t.get("last_replies") or [])
        corpus.append(txt.lower())
        own = strip((t.get("sub") or "") + " " + (t.get("com") or ""))
        for k in ({m.upper() for m in TICK_RE.findall(txt)} | set(CAPS_RE.findall(own))) - NOT_TICK:
            if not k.isdigit(): tick[k].append(t)
        sub = strip(t.get("sub") or "")
        gm = re.match(r"^/?([a-z0-9]{2,12})/?\s*-?", sub.lower())
        if gm and sub.startswith("/"): terms["/" + gm.group(1) + "/"].append(t)
    items = []
    def mk(label, ts_, kind):
        reps = sum(t.get("replies", 0) for t in ts_); top = max(ts_, key=lambda t: t.get("replies", 0))
        img = f"https://i.4cdn.org/biz/{top['tim']}s.jpg" if top.get("tim") else None
        sample = strip(top.get("sub") or top.get("com") or "")[:220]
        first = min(t.get("time", NOW) for t in ts_)
        return {"titolo": label, "link": f"https://boards.4chan.org/biz/thread/{top['no']}", "fonte": "4chan /biz/", "tipo": kind, "ts": first,
                "img": img, "lore": f"Citato in {len(ts_)} thread di /biz/ ({reps} risposte totali). Esempio: «{sample}»",
                "viral": min(30, 5 * len(ts_) + 5 * math.log10(1 + reps)), "biz_thread": len(ts_), "biz_risposte": reps}
    for k, ts_ in tick.items():
        if len(ts_) >= 2 or sum(t.get("replies", 0) for t in ts_) >= 15: items.append(mk("$" + k, ts_, "biz_ticker"))
    for k, ts_ in terms.items():
        if len(ts_) >= 1 and sum(t.get("replies", 0) for t in ts_) >= 30: items.append(mk("General " + k, ts_, "biz_general"))
    fonte("4chan /biz/ (API JSON)", True, len(items), f"{len(threads)} thread analizzati")
    return items, "\n".join(corpus)

# ---------- Reddit (RSS pubblici; spesso bloccati) ----------
def reddit():
    items, corpus, ok, fail = [], [], 0, []
    for i, s in enumerate(SUBS):
        try:
            r = S.get(f"https://www.reddit.com/r/{s}/hot/.rss?limit=25", timeout=8)
            if r.status_code != 200 or "<feed" not in r.text[:400]:
                fail.append(f"r/{s} ({r.status_code})")
                if i >= 2 and ok == 0: fail += [f"r/{x} (saltato)" for x in SUBS[i + 1:]]; break  # bloccato: non insistere
                continue
            ok += 1
            for e in feedparser.parse(r.content).entries:
                try: ts = time.mktime(e.updated_parsed)
                except Exception: ts = NOW
                t = strip(e.title); corpus.append(t.lower())
                m = re.search(r'<img[^>]+src="([^"]+)"', e.get("summary", ""))
                items.append({"titolo": t, "link": e.link, "fonte": f"r/{s}", "tipo": "reddit", "ts": ts, "img": m and html.unescape(m.group(1)),
                              "lore": strip(e.get("summary", ""))[:300], "viral": 10})
            time.sleep(1.5)
        except Exception as ex: fail.append(f"r/{s} ({type(ex).__name__})")
    fonte("Reddit RSS (13 subreddit)", ok > 0, len(items), f"{ok}/{len(SUBS)} ok" + ("; falliti: " + ", ".join(fail) if fail else ""))
    return items, "\n".join(corpus)

# ---------- Token ideas ----------
SUF = ["Coin", "Inu", "Wif Hat", "Moon", "Bonk", "AI"]
def core(t):
    q = re.findall(r"(?:^|\s)['‘“\"]([^'’”\"]{3,40})['’”\"](?=\s|$|[,.:!?])", t)
    if q and len(t.split()) > 6: t = max(q, key=len)
    t = re.split(r"\s*[/|:(]\s*", t)[0]; t = re.sub(r"[\"“”'‘’«»]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:40] or t[:40]
def mk_ticker(name, used):
    w = [x for x in re.sub(r"[^A-Za-z0-9 ]", "", name).upper().split() if x not in ("THE", "A", "OF", "AND", "IN", "MY", "IL", "LA")]
    j = "".join(w)
    cands = [j if 3 <= len(j) <= 6 else None, w[0] if w and 3 <= len(w[0]) <= 6 else None, "".join(x[0] for x in w) if len(w) >= 3 else None,
             (w[0][:3] + w[-1][:3]) if len(w) >= 2 else None, j[:5], j[:4]]
    for c in cands:
        if c and 3 <= len(c) <= 6 and c not in used and not c.isdigit(): used.add(c); return c
    c = (j + "MEME")[:5]
    while c in used: c = c[:-1] + chr(65 + (ord(c[-1]) - 64) % 26)
    used.add(c); return c
def token_ideas(it):
    if it["tipo"].startswith("biz_"):
        return []
    base = core(it["titolo"]); seed = int(h8(it["link"])[:4], 16); used = set()
    w = base.split(); short = " ".join(w[:3])
    pool = [(short, "nome del meme"), (f"{w[0]} {SUF[seed % 6]}" if w else base, "meme + suffisso"),
            ((w[0][:max(3, len(w[0]) * 2 // 3)] + (w[-1] if len(w) > 1 else "ino")).title() if w else base, "portmanteau")]
    out = []
    for n, tp in pool:
        if n.lower() in {o["nome"].lower() for o in out}: n = n + " Coin"
        out.append({"nome": n, "ticker": "$" + mk_ticker(n, used), "tipo": tp,
                    "descrizione": f"{tp.capitalize()}: memecoin ispirata al meme «{base}» ({it['fonte']})."})
    return out

# ---------- Solana: DexScreener + pump.fun ----------
TTL = 3600
class Sol:
    def __init__(s, cache): s.c = cache.setdefault("sol", {}); s.ok = {"dex": [0, 0], "pump": [0, 0]}; s.last = 0
    def _get(s, kind, url, params, red):
        k = kind + ":" + json.dumps(params, sort_keys=True); hit = s.c.get(k)
        if hit and NOW - hit[0] < TTL: return hit[1]
        s.ok[kind][1] += 1
        for _ in range(2):
            w = 0.3 - (time.time() - s.last)
            if w > 0: time.sleep(w)
            s.last = time.time()
            try:
                h = dict(UA)
                if kind == "pump": h.update({"Origin": "https://pump.fun", "Accept": "application/json"})
                r = requests.get(url, params=params, headers=h, timeout=10)
                if r.status_code == 429: time.sleep(3); continue
                if r.status_code != 200: break
                d = red(r.json()); s.ok[kind][0] += 1; s.c[k] = [int(NOW), d]; return d
            except Exception: break
        return None
    def dex(s, q):
        return s._get("dex", "https://api.dexscreener.com/latest/dex/search", {"q": q}, lambda d: [
            {"nome": (p.get("baseToken") or {}).get("name"), "ticker": (p.get("baseToken") or {}).get("symbol"), "addr": (p.get("baseToken") or {}).get("address"),
             "liq": round((p.get("liquidity") or {}).get("usd") or 0), "vol24": round((p.get("volume") or {}).get("h24") or 0),
             "mcap": round(p.get("marketCap") or 0), "fdv": round(p.get("fdv") or 0), "creato": p.get("pairCreatedAt"), "url": p.get("url"), "fonte": "DexScreener"}
            for p in (d.get("pairs") or []) if p.get("chainId") == "solana"])
    def pump(s, q):
        return s._get("pump", "https://frontend-api-v3.pump.fun/coins", {"searchTerm": q, "limit": 30, "offset": 0, "sort": "created_timestamp", "order": "DESC", "includeNsfw": "false"},
                      lambda d: [{"nome": c.get("name"), "ticker": c.get("symbol"), "addr": c.get("mint"), "liq": None, "vol24": None, "mcap": round(c.get("usd_market_cap") or 0),
                                  "fdv": None, "creato": c.get("created_timestamp"), "url": "https://pump.fun/coin/" + (c.get("mint") or ""), "fonte": "pump.fun"} for c in d] if isinstance(d, list) else None)

def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
def sol_check(sol, it):
    if it["tipo"] == "biz_ticker": names, ticks = set(), {it["titolo"][1:].upper()}
    elif it["tipo"] == "biz_general": return {"badge": "Non applicabile", "esatti": [], "simili": []}
    else:
        names = {norm(core(it["titolo"]))} | ({norm(it["token"][0]["nome"])} if it["token"] else set()); ticks = {t["ticker"][1:] for t in it["token"]}
    kw = [w for w in words(core(it["titolo"])) if len(w) >= 4][:2]
    qs = list(dict.fromkeys(([core(it["titolo"])] if not it["tipo"].startswith("biz") else []) + list(ticks)[:2]))
    exact, sim, failed = [], [], 0
    for q in qs:
        res = sol.dex(q)
        if res is None: failed += 1; continue
        for p in res:
            n, t = norm(p["nome"]), (p["ticker"] or "").upper()
            if n in names or (it["tipo"] == "biz_ticker" and t in ticks): exact.append(p)
            elif t in ticks or any(k in n for k in kw): sim.append(p)
    pq = core(it["titolo"]) if not it["tipo"].startswith("biz") else list(ticks)[0]
    res = sol.pump(pq); pump_ok = res is not None
    for p in res or []:
        n, t = norm(p["nome"]), (p["ticker"] or "").upper(); age = (NOW - (p["creato"] or 0) / 1000) / 86400
        if n in names or (it["tipo"] == "biz_ticker" and t in ticks): exact.append(p)
        elif age <= 14 and (t in ticks or any(k in n for k in kw)): sim.append(p)
    def uniq(l):
        seen, o = set(), []
        for x in sorted(l, key=lambda x: -((x.get("liq") or 0) + (x.get("vol24") or 0) + (x.get("mcap") or 0))):
            if x["addr"] in seen: continue
            seen.add(x["addr"]); y = dict(x); y.pop("addr")
            y["eta_g"] = round((NOW - y.pop("creato") / 1000) / 86400, 1) if y.get("creato") else None; o.append(y)
        return o[:6]
    exact, sim = uniq(exact), uniq([x for x in sim if x["addr"] not in {e.get("addr") for e in exact}])
    sim = [x for x in sim if x["url"] not in {e["url"] for e in exact}]
    badge = "Controllo non riuscito" if failed == len(qs) and not pump_ok else "Già lanciato" if exact else "Simili esistenti" if sim else "Libero"
    return {"badge": badge, "esatti": exact, "simili": sim, "pump_ok": pump_ok}

# ---------- Punteggio ----------
POT = {r"\b(cat|dog|frog|pepe|doge|shiba|wojak|chad|monkey|ape|bird|penguin|hamster|goat|bear|bull)s?\b": 8, r"\bai\b": 4,
       r"\b(face|reaction|stare|dance|dancing|song|audio|copypasta|guy|man|girl|uncle|grandma|nan|kid)\b": 5}
def score(it, cross):
    age_h = max(0, (NOW - it["ts"]) / 3600)
    fresc = round(max(0, 25 * (1 - age_h / MAX_AGE_H)))
    vir = round(min(35, it["viral"]))
    xs = round(min(20, 7 * len(cross)))
    t = core(it["titolo"]); nw = len(t.split()); pot = 6 if nw <= 3 else 3 if nw <= 5 else 0
    for rx, v in POT.items():
        if re.search(rx, it["titolo"].lower()): pot += v
    if it.get("img"): pot += 2
    if it["tipo"] == "biz_ticker": pot = min(pot, 6) + 2
    pot = min(20, pot)
    return {"viralita": vir, "freschezza": fresc, "incroci": xs, "potenziale": pot, "totale": min(100, vir + fresc + xs + pot)}

def trend(hist, it):
    e = hist.setdefault(it["id"], {"t": it["titolo"][:60], "h": []}); p = [int(NOW), it["punteggio"]["totale"], len(it["fonti"])]
    if not e["h"] or e["h"][-1][1:] != p[1:] or NOW - e["h"][-1][0] > 3 * 3600: e["h"].append(p)
    e["h"] = [x for x in e["h"] if x[0] > NOW - 7 * 86400][-48:]
    first = e["h"][0][0]; ref = [x for x in e["h"] if x[0] <= NOW - 6 * 3600]; base = ref[-1] if ref else e["h"][0]
    d = p[1] - base[1]
    stato = "nuovo" if NOW - first < 3 * 3600 else "crescita" if d >= 5 or p[2] > base[2] else "calo" if d <= -8 else "stabile"
    return {"stato": stato, "delta": d, "serie": [[x[0], x[1]] for x in e["h"]], "primo": first}

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cache = load("cache.json", {}); hist = load("history.json", {})
    items = []
    items += kym_feed("https://knowyourmeme.com/memes.rss", "Know Your Meme (confermati)", "kym_confermato")
    items += kym_feed("https://knowyourmeme.com/memes/submissions.rss", "Know Your Meme (nuove proposte)", "kym_proposta")
    items += kym_feed("https://knowyourmeme.com/newsfeed.rss", "Know Your Meme (newsfeed)", "kym_news")
    refs = lore_refs()
    bi, bcorp = biz(); items += bi
    ri, rcorp = reddit(); items += ri
    # dedup per link
    seen, uniq = set(), []
    for it in items:
        if it["link"] in seen: continue
        seen.add(it["link"]); uniq.append(it)
    items = [it for it in uniq if NOW - it["ts"] <= MAX_AGE_H * 3600]
    kym_corp = "\n".join((i["titolo"] + " " + i["lore"]).lower() for i in uniq if i["fonte"].startswith("Know"))
    sol = Sol(cache); out = []
    for it in items:
        it["id"] = h8(it["link"]); it["token"] = token_ideas(it)
        key = [w for w in words(core(it["titolo"])) if len(w) >= 4]
        phrase = core(it["titolo"]).lower()
        cross = []
        if it["tipo"] == "biz_ticker":
            tk = it["titolo"][1:].lower()
            if re.search(r"\b" + re.escape(tk) + r"\b", rcorp): cross.append("Reddit")
            if len(tk) >= 4 and re.search(r"\b" + re.escape(tk) + r"\b", kym_corp): cross.append("Know Your Meme")
        elif not it["tipo"].startswith("biz"):
            def hit(c): return len(phrase) >= 5 and phrase in c or (len(key) >= 2 and all(re.search(r"\b" + re.escape(k) + r"\b", c) for k in key[:2]))
            if not it["fonte"].startswith("4chan") and hit(bcorp): cross.append("4chan /biz/")
            if not it["fonte"].startswith("r/") and hit(rcorp): cross.append("Reddit")
            if it["fonte"].startswith("r/") and hit(kym_corp): cross.append("Know Your Meme")
        lr = [r for r in refs if norm(r["titolo"]) and (norm(r["titolo"]) == norm(core(it["titolo"])) or (len(norm(r["titolo"])) >= 5 and norm(r["titolo"]) in norm(it["titolo"])))]
        if lr: cross.append("Lore tokenizzata")
        it["fonti"] = [it["fonte"]] + cross; it["lore_ref"] = lr[:3]
        it["punteggio"] = score(it, cross)
        out.append(it)
    out.sort(key=lambda x: -x["punteggio"]["totale"])
    for it in out[:80]:
        it["solana"] = sol_check(sol, it)
        if it["solana"]["badge"] == "Già lanciato" and it["tipo"].startswith("kym"): it["punteggio"]["potenziale"] = max(0, it["punteggio"]["potenziale"] - 5)
        it["punteggio"]["totale"] = sum(it["punteggio"][k] for k in ("viralita", "freschezza", "incroci", "potenziale"))
    for it in out[80:]: it["solana"] = {"badge": "Non controllato", "esatti": [], "simili": []}
    hs = hist.setdefault("voci", {})
    for it in out:
        it["trend"] = trend(hs, it)
        if it["trend"]["stato"] == "crescita": it["punteggio"]["totale"] = min(100, it["punteggio"]["totale"] + 4)
        it["primo_visto"] = min(it["ts"], it["trend"]["primo"])
    for k in [k for k, v in hs.items() if not v["h"] or v["h"][-1][0] < NOW - 7 * 86400]: del hs[k]
    out.sort(key=lambda x: -x["punteggio"]["totale"])
    fonte("DexScreener API", sol.ok["dex"][1] == 0 or sol.ok["dex"][0] > 0, sol.ok["dex"][0], f"{sol.ok['dex'][0]}/{sol.ok['dex'][1]} richieste nuove ok (resto da cache 1h)")
    fonte("pump.fun API", sol.ok["pump"][1] == 0 or sol.ok["pump"][0] > 0, sol.ok["pump"][0], f"{sol.ok['pump'][0]}/{sol.ok['pump'][1]} richieste nuove ok")
    cache["sol"] = {k: v for k, v in cache.get("sol", {}).items() if NOW - v[0] < TTL}
    data = {"aggiornato": int(NOW), "fonti": FONTI, "voci": out, "lore_tokenizzata": refs}
    save("data.json", data); save("cache.json", cache); save("history.json", hist)
    tpl = open("template.html", encoding="utf-8").read()
    open("index.html", "w", encoding="utf-8").write(tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    print(f"Voci: {len(out)} | " + " | ".join(f"{f['nome']}: {'OK' if f['ok'] else 'KO'} {f['n']} {f['nota']}" for f in FONTI))

if __name__ == "__main__": main()
