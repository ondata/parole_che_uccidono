# Analisi delle immagini negli articoli di femminicidio

## Origine

Idea di Jacopo Solmi: analizzare come la stampa racconta la violenza sulle donne attraverso
le **immagini** che accompagnano gli articoli — non solo il testo. La foto dell'assassino
seria e della vittima sorridente, o la coppia felice "prima della tragedia", modificano
profondamente la percezione del racconto e possono influenzare l'opinione pubblica.

## Obiettivo

Costruire un dataset strutturato che rilevi come le diverse testate giornalistiche scelgono
le immagini negli articoli su femminicidio e violenza, e se questo abbia o meno pattern
sistematici.

---

## Flusso proposto

```
URL (da feed_entries.jsonl)
        │
        ▼
1. Analisi testo/titolo via LLM
   → È a tema femminicidio/violenza? Sì/No
   → Se No: salta. Se Sì: continua.
        │
        ▼
2. Screenshot della pagina (agent-browser)
   → Gestione cookie banner prima dello screenshot
        │
        ▼
2b. Estrazione immagine OpenGraph / Twitter Card (via meta tag `og:image` / `twitter:image`)
   → Disponibile senza caricare la pagina, è l'immagine "ufficiale" scelta dalla testata
   → Annotare separatamente: URL immagine, dimensioni, alt text se presenti

3. Estrazione immagini dall'articolo (via screenshot o DOM)
   → Identificare immagini pertinenti (non loghi, pub, ecc.)
        │
        ▼
4. Analisi AI delle immagini
   → Chi è ritratto? Vittima / Autore / Coppia / Altro
   → Tipo di foto: sorridente, formale, dal vivo, archivio, social
   → Contesto: evento tragico, momento felice, altro
        │
        ▼
5. Archiviazione strutturata (JSONL)
   → url, fonte, data, titolo, rilevante, immagini: [{tipo, soggetto, contesto}]
```

---

## Dati prodotti

Ogni riga del dataset conterrebbe:

| Campo | Descrizione |
|---|---|
| `url` | URL dell'articolo |
| `fonte` | Dominio della testata |
| `data` | Data pubblicazione |
| `titolo` | Titolo dell'articolo |
| `screenshot` | Path file PNG |
| `og_image` | URL immagine OpenGraph/Twitter Card (se presente) |
| `immagini` | Array con analisi di ogni immagine |
| `vittima_sorridente` | Bool — almeno un'immagine della vittima sorridente |
| `autore_serio` | Bool — almeno un'immagine dell'autore seria/formale |
| `coppia_felice` | Bool — immagine di coppia pre-tragedia |

---

## Esempio visivo

Screenshot di 6 articoli casuali dal feed (griglia 3×2):

![Griglia screenshot articoli](screenshot_grid.png)

> 6/6 articoli caricati correttamente. Screenshot a 1024×1024 px via `agent-browser set viewport 1024 1024`.
> Cookie banner gestiti interattivamente: `agent-browser snapshot -i` → identificazione ref del bottone → `click @ref`.
> L'immagine **OpenGraph** (`og:image`) è estraibile senza caricare la pagina completa,
> utile come fallback rapido quando il cookie banner o il paywall impedisce lo screenshot.

---

## Fattibilità tecnica

Testata il 2026-02-13:

- `agent-browser` funziona per screenshot su URL reali dal feed
- Il titolo è già disponibile in `feed_entries.jsonl` — l'analisi testuale può usarlo
  come primo filtro rapido (molti articoli già marcati con "femminicidio" nel titolo)
- Il testo completo si estrae con `agent-browser get text` o parsing HTML
- Le immagini si estraggono con `agent-browser get attr img src` o JS eval
- L'analisi AI immagini richiede un modello vision (es. Claude claude-sonnet-4-5-20250929 con immagini)
- Problema comune: **cookie banner** che copre il contenuto — va gestito con click
  su "Accetto" prima di screenshot

### Comandi agent-browser rilevanti

```bash
# Naviga e accetta cookie
agent-browser open <url>
agent-browser wait --load networkidle
# Opzionale: cerca e clicca il pulsante cookie consent
agent-browser find text "Accetto" click  # o "Accetta" / "OK"

# Estrai testo per classificazione
agent-browser get text body

# Screenshot
agent-browser screenshot --full output.png

# Estrai src delle immagini
agent-browser eval "Array.from(document.querySelectorAll('article img')).map(i=>i.src)"
```

---

## Questioni aperte

- Come standardizzare l'estrazione immagini tra testate con strutture HTML diverse?
- Soglia di confidenza per la classificazione "rilevante" dell'articolo?
- Come gestire immagini generiche (stock photo, loghi testate)?
- Archiviare le immagini scaricate o solo l'analisi AI?
- Privacy: alcune immagini potrebbero ritrarre persone private — conservare solo metadati?
