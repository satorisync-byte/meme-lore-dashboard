# 🐸 Radar Meme & Lore per memecoin Solana

Dashboard in italiano per scoprire meme e lore nuovi da trasformare in memecoin su Solana.

**Sito:** https://satorisync-byte.github.io/meme-lore-dashboard/

## Fonti
- **Know Your Meme**: feed RSS ufficiali (`/memes.rss` confermati, `/memes/submissions.rss` nuove proposte, `/newsfeed.rss`), richieste lente e con User-Agent dichiarato, nel rispetto di robots.txt.
- **kym.fun** e **knowyourmemecoin.com**: elenco della lore già tokenizzata (incrocio "Lore tokenizzata").
- **4chan /biz/**: API JSON ufficiale in sola lettura (`a.4cdn.org/biz/catalog.json`); ticker e general ricorrenti tra i thread, risposte come slancio.
- **Reddit** (13 subreddit crypto/meme): feed `.rss` pubblici. Attualmente bloccati (HTTP 403): la dashboard lo segnala nello stato fonti.
- **Solana**: DexScreener (ricerca per nome/ticker, solo `chainId=solana`: market cap/FDV, liquidità, volume 24h, età della coppia) + pump.fun per i token appena creati.

## Punteggio (0-100)
Viralità (max 35) + Freschezza (max 25, zero a 5 giorni; le voci più vecchie sono escluse) + Incroci tra fonti (max 20) + Potenziale meme (max 20) + 4 se in crescita. Dettagli nel piè di pagina della dashboard.

Badge Solana: **Libero** · **Simili esistenti** · **Già lanciato**. Per i meme non lanciati vengono proposti nome, ticker e descrizione.

## Funzioni
Preferiti (salvati nel browser), andamento nel tempo (`history.json`), immagini, filtri e ordinamento, layout per iPhone (schede sotto 768px).

## Aggiornamento e avvisi
GitHub Actions ogni 5 minuti (`.github/workflows/update.yml`). Avvisi Telegram con prefisso **🐸 Meme Lore** per le voci con punteggio ≥ 50, ognuna inviata una sola volta (`alerted_telegram.json`). Segreti: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

Uso locale: `pip install -r requirements.txt && python aggregate.py && python notify.py`

*Solo suggerimenti, non consulenza finanziaria.*
