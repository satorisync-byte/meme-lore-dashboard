#!/usr/bin/env python3
"""🐸 Meme Lore: avvisi Telegram per meme/lore con punteggio >= SOGLIA. Ogni voce viene avvisata una sola volta (alerted_telegram.json)."""
import json, os, time, html, requests
SOGLIA, MAX_PER_RUN, KEEP_DAYS = 65, 5, 10
DASH = "https://satorisync-byte.github.io/meme-lore-dashboard/"
TRL = {"crescita": "📈 in crescita", "nuovo": "🆕 nuovo", "stabile": "➖ stabile", "calo": "📉 in calo"}
E = lambda s: html.escape(str(s or ""), quote=True)

def msg(s):
    p = s["punteggio"]; tr = s.get("trend") or {}; so = s.get("solana") or {}
    lines = ["🐸 <b>Meme Lore</b> — nuovo meme sopra 65", "", f"<b>{E(s['titolo'])}</b>", E((s.get("lore") or "")[:300]),
             f"Punteggio: <b>{p['totale']}</b> (Viralità {p['viralita']} · Freschezza {p['freschezza']} · Incroci {p['incroci']} · Potenziale {p['potenziale']})",
             f"Fonti: <a href=\"{E(s['link'])}\">{E(', '.join(s['fonti']))}</a>", f"Andamento: {TRL.get(tr.get('stato'), '—')}",
             f"Solana: {E(so.get('badge') or 'non controllato')}"]
    for t in (so.get("esatti") or [])[:2]:
        lines.append(f"• <a href=\"{E(t['url'])}\">{E(t['nome'])} ${E(t['ticker'])}</a> MC ${t.get("mcap") or t.get("fdv") or "—"}")
    if s.get("token"):
        lines += ["", "<b>Idee token:</b>"] + [f"• {E(t['nome'])} <code>{E(t['ticker'])}</code> — {E(t['descrizione'])}" for t in s["token"][:3]]
    lines += ["", "<i>Solo suggerimenti, non consulenza finanziaria.</i>", f"<a href=\"{DASH}\">Apri la dashboard Meme Lore</a>"]
    return "\n".join(lines)

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    path = "alerted_telegram.json"
    try: st = json.load(open(path))
    except Exception: st = {"alerted": {}}
    now = time.time()
    st["alerted"] = {k: v for k, v in st.get("alerted", {}).items() if now - v.get("ts", 0) < KEEP_DAYS * 86400}
    seen = set(st["alerted"]) | {v.get("link") for v in st["alerted"].values()}
    stories = json.load(open("data.json"))["voci"]
    todo = [s for s in stories if s["punteggio"]["totale"] >= SOGLIA and s.get("id") not in seen and s["link"] not in seen][:MAX_PER_RUN]
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    print(f"Storie >= {SOGLIA} da avvisare: {len(todo)}")
    if not tok or not chat:
        print("Segreti Telegram mancanti: avvisi saltati."); return
    sent = 0
    try:  # diagnostica connettività (token fittizio, nessun segreto)
        t0 = time.time(); r = requests.get("https://api.telegram.org/bot0:diag/getMe", timeout=(10, 20))
        print(f"Diagnostica api.telegram.org: HTTP {r.status_code} in {time.time() - t0:.1f}s")
    except Exception as e: print(f"Diagnostica api.telegram.org: {type(e).__name__}")
    for s in todo:
        ok = False
        for attempt in range(2):
            try:
                r = requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", timeout=(10, 45),
                                  json={"chat_id": chat, "text": msg(s), "parse_mode": "HTML", "disable_web_page_preview": False})
                j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                ok = r.status_code == 200 and j.get("ok")
                print(f"Telegram sendMessage: HTTP {r.status_code} ok={bool(ok)} {'' if ok else str(j.get('description', ''))[:120]} | {s['titolo'][:70]}")
                if ok or r.status_code not in (429, 500, 502, 503, 504): break
                time.sleep(min(30, int((j.get("parameters") or {}).get("retry_after", 5))))
            except Exception as e:
                print(f"Telegram sendMessage: errore di rete {type(e).__name__} (tentativo {attempt + 1}/2) | {s['titolo'][:70]}")
                time.sleep(5)
        if not ok:  # ripiego: curl IPv4 (token passato via file di configurazione temporaneo, mai stampato)
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f: json.dump({"chat_id": chat, "text": msg(s), "parse_mode": "HTML"}, f)
            try:
                out = subprocess.run(["curl", "-4", "-s", "-m", "60", "-o", "/tmp/tg.out", "-w", "%{http_code}", "-H", "Content-Type: application/json",
                                      "--data-binary", "@" + f.name, "-K", "-"], input=f'url = "https://api.telegram.org/bot{tok}/sendMessage"\n',
                                     capture_output=True, text=True, timeout=70).stdout.strip()
                body = json.load(open("/tmp/tg.out")) if os.path.exists("/tmp/tg.out") and os.path.getsize("/tmp/tg.out") else {}
                ok = out == "200" and body.get("ok")
                print(f"Telegram sendMessage (curl -4): HTTP {out or 'nessuna risposta'} ok={bool(ok)} {'' if ok else str(body.get('description', ''))[:120]}")
            except Exception as e: print(f"Telegram curl: {type(e).__name__}")
        if ok:
            sent += 1
            st["alerted"][s.get("id") or s["link"]] = {"link": s["link"], "titolo": s["titolo"][:120], "punteggio": s["punteggio"]["totale"], "ts": int(now)}
        time.sleep(1.2)
    st["aggiornato"] = int(now)
    json.dump(st, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"Avvisi inviati: {sent}/{len(todo)}")

if __name__ == "__main__":
    try: main()
    except Exception as e: print(f"notify.py: errore {type(e).__name__}: {str(e)[:120]}")
