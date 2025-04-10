#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Estrattore di feed RSS da Google Alerts

Questo script scarica feed RSS da Google Alerts, estrae le entry
e le salva in un file JSONL, evitando duplicati e ordinando per data.

Dipendenze:
- requests: per scaricare il feed
- lxml: per il parsing XML
- json: per gestire i dati in formato JSON
"""

import os
import sys
import json
import logging
import re
import requests
from datetime import datetime
from lxml import etree
from pathlib import Path

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configurazione percorsi relativi allo script
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
TMP_DIR = PROJECT_DIR / "tmp"
ARCHIVE_FILE = DATA_DIR / "feed_entries.jsonl"
TMP_FEED_PREFIX = "feed_temp"

# Lista di URL dei feed RSS di Google Alerts
RSS_FEED_URLS = [
    "https://www.google.com/alerts/feeds/15244278077982194024/11541540114411201767",
    "https://www.google.com/alerts/feeds/15244278077982194024/10845276624304286453"
]

# Namespace per il parsing XML
NAMESPACES = {
    'atom': 'http://www.w3.org/2005/Atom',
    'idx': 'urn:atom-extension:indexing'
}

def ensure_directories():
    """Assicura che le directory necessarie esistano e siano scrivibili."""
    logger.debug(f"Verifica directory: DATA_DIR={DATA_DIR}, TMP_DIR={TMP_DIR}")

    DATA_DIR.mkdir(exist_ok=True, parents=True)
    TMP_DIR.mkdir(exist_ok=True, parents=True)

    # Verifica che le directory esistano e siano scrivibili
    if not os.access(DATA_DIR, os.W_OK):
        logger.error(f"La directory {DATA_DIR} non è scrivibile!")
        sys.exit(1)
    if not os.access(TMP_DIR, os.W_OK):
        logger.error(f"La directory {TMP_DIR} non è scrivibile!")
        sys.exit(1)

    logger.debug("Directory verificate e scrivibili")

def download_feed(feed_url, temp_file):
    """Scarica il feed RSS e lo salva in un file temporaneo."""
    logger.info(f"Scaricamento del feed RSS da {feed_url}")

    try:
        response = requests.get(feed_url, timeout=30)
        response.raise_for_status()  # Solleva un'eccezione se la richiesta fallisce

        with open(temp_file, 'wb') as f:
            f.write(response.content)

        logger.info(f"Feed RSS salvato in {temp_file}")

        # Verifico che il file esista e contenga dati
        if not temp_file.exists():
            logger.error(f"Il file {temp_file} non esiste dopo il download!")
            return False

        if temp_file.stat().st_size == 0:
            logger.error(f"Il file {temp_file} è vuoto dopo il download!")
            return False

        logger.debug(f"Dimensione file XML: {temp_file.stat().st_size} bytes")
        return True
    except Exception as e:
        logger.error(f"Errore durante il download del feed {feed_url}: {e}")
        return False

def clean_google_redirect_link(link):
    """
    Pulisce i link di reindirizzamento di Google, rimuovendo:
    - all'inizio "https://www.google.com/url?rct=j&sa=t&url="
    - alla fine da "&ct=" in poi

    Ritorna il link URL reale a cui punta l'articolo.
    """
    if not link:
        return link

    # Pattern per estrarre l'URL reale dal link di reindirizzamento Google
    pattern = r'https://www\.google\.com/url\?rct=j&sa=t&url=(.+?)(?:&ct=.+)?$'
    match = re.search(pattern, link)

    if match:
        # URL decodificato dal link di reindirizzamento
        real_url = match.group(1)
        return real_url

    return link  # Ritorna il link originale se non corrisponde al pattern

def parse_feed(feed_file):
    """Estrae le entry dal feed RSS XML."""
    logger.info(f"Analisi del feed RSS {feed_file}")

    try:
        # Parsing del documento XML
        tree = etree.parse(str(feed_file))
        root = tree.getroot()

        entries = []
        # Estrai tutte le entry dal feed
        entry_elements = root.xpath('//atom:entry', namespaces=NAMESPACES)
        logger.info(f"Trovate {len(entry_elements)} entry nel feed")

        for idx, entry in enumerate(entry_elements, 1):
            try:
                # Estrai i dati pertinenti
                entry_id = entry.xpath('./atom:id/text()', namespaces=NAMESPACES)[0]
                title = entry.xpath('./atom:title/text()', namespaces=NAMESPACES)[0]
                raw_link = entry.xpath('./atom:link/@href', namespaces=NAMESPACES)[0]
                published = entry.xpath('./atom:published/text()', namespaces=NAMESPACES)[0]

                # Pulisci il link rimuovendo il reindirizzamento Google
                cleaned_link = clean_google_redirect_link(raw_link)

                # Crea un dizionario per ogni entry
                entry_data = {
                    'id': entry_id,
                    'title': title,
                    'link': cleaned_link,
                    'published': published
                }

                entries.append(entry_data)
                logger.debug(f"Estratta entry {idx}/{len(entry_elements)}: id={entry_id}")
            except Exception as e:
                logger.error(f"Errore durante l'estrazione dei dati dell'entry {idx}: {e}")
                continue

        logger.info(f"Estratte {len(entries)} entry valide dal feed")
        return entries
    except Exception as e:
        logger.error(f"Errore durante il parsing del feed: {e}")
        return []

def read_existing_entries():
    """Legge le entry esistenti dal file di archivio."""
    if not ARCHIVE_FILE.exists():
        return []

    entries = []
    try:
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Salta righe vuote
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        logger.warning(f"Impossibile decodificare la riga JSON: {line}")
    except Exception as e:
        logger.error(f"Errore durante la lettura del file archivio: {e}")

    return entries

def remove_duplicate_links(entries):
    """Rimuove entry duplicate basandosi sull'URL del link, mantenendo solo la prima occorrenza."""
    unique_entries = []
    seen_links = set()
    duplicates_removed = 0

    for entry in entries:
        link = entry.get('link', '')
        if link and link not in seen_links:
            seen_links.add(link)
            unique_entries.append(entry)
        else:
            duplicates_removed += 1

    if duplicates_removed > 0:
        logger.info(f"Rimosse {duplicates_removed} entry duplicate (stesso URL)")

    return unique_entries

def process_feeds():
    """Processa tutti i feed: scarica, estrae, salva, ordina."""
    try:
        # Assicura che le directory necessarie esistano
        ensure_directories()

        # Leggi le entry esistenti
        existing_entries = read_existing_entries()

        # Crea un set degli ID esistenti per il controllo dei duplicati
        existing_ids = {entry['id'] for entry in existing_entries}

        # Crea un set degli URL esistenti per il controllo dei link duplicati
        existing_links = {entry.get('link', '') for entry in existing_entries}

        # Raccogliere tutte le nuove entry da tutti i feed
        all_new_entries = []

        # Elabora ogni feed URL
        for index, feed_url in enumerate(RSS_FEED_URLS):
            # Crea un nome univoco per il file temporaneo del feed
            temp_feed_file = TMP_DIR / f"{TMP_FEED_PREFIX}_{index}.xml"

            # Scarica il feed
            if not download_feed(feed_url, temp_feed_file):
                logger.warning(f"Download del feed {feed_url} fallito, passaggio al successivo.")
                continue

            # Estrai le entry dal feed
            entries = parse_feed(temp_feed_file)
            if not entries:
                logger.warning(f"Nessuna entry valida trovata nel feed {feed_url}")
                continue

            # Filtra per rimuovere duplicati con quelli già archiviati (per ID e per link)
            new_entries = [
                entry for entry in entries
                if entry['id'] not in existing_ids and entry['link'] not in existing_links
            ]

            # Aggiorna gli insiemi di ID e link esistenti con quelli appena elaborati
            existing_ids.update(entry['id'] for entry in new_entries)
            existing_links.update(entry['link'] for entry in new_entries)

            # Aggiungi le nuove entry a quelle raccolte da tutti i feed
            all_new_entries.extend(new_entries)

            logger.info(f"Estratte {len(new_entries)} nuove entry dal feed {feed_url}")

            # Pulizia: rimuovi il file temporaneo del feed
            if temp_feed_file.exists():
                temp_feed_file.unlink()

        # Se ci sono nuove entry da aggiungere
        if all_new_entries:
            # Combina le entry esistenti con le nuove
            combined_entries = existing_entries + all_new_entries

            # Rimuovi eventuali entry con lo stesso link (può accadere se un articolo è presente in più feed)
            combined_entries = remove_duplicate_links(combined_entries)

            # Ordina tutte le entry per data di pubblicazione (decrescente)
            sorted_entries = sorted(combined_entries, key=lambda x: x['published'], reverse=True)

            # Scrive le entry ordinate nel file
            with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
                for entry in sorted_entries:
                    json_str = json.dumps(entry, ensure_ascii=False)
                    f.write(json_str + '\n')

            logger.info(f"Aggiunte {len(all_new_entries)} nuove entry al file {ARCHIVE_FILE}")
            logger.info(f"Il file contiene {len(sorted_entries)} entry totali dopo la rimozione dei duplicati")
        else:
            logger.info("Nessuna nuova entry trovata in tutti i feed elaborati")

        # Verifica finale
        if ARCHIVE_FILE.exists() and ARCHIVE_FILE.stat().st_size > 0:
            logger.info(f"File {ARCHIVE_FILE} aggiornato con successo")
            return True
        else:
            logger.warning(f"Il file {ARCHIVE_FILE} potrebbe non essere stato aggiornato correttamente")
            return False

    except Exception as e:
        logger.error(f"Errore imprevisto durante l'elaborazione dei feed: {e}")
        return False

def main():
    """Funzione principale."""
    try:
        logger.info("Avvio elaborazione feed RSS")

        success = process_feeds()

        if success:
            logger.info("Elaborazione completata con successo!")
            return 0
        else:
            logger.error("Elaborazione terminata con errori.")
            return 1
    except Exception as e:
        logger.error(f"Errore fatale durante l'esecuzione: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
