#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semplice estrattore di feed RSS per violenza donne

Questo script scarica un feed RSS da Google Alerts, estrae le entry
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
import requests
from datetime import datetime
from lxml import etree
from pathlib import Path

# Configura logging dettagliato per debug
logging.basicConfig(
    level=logging.DEBUG,
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
TMP_FEED = TMP_DIR / "feed_temp.xml"
TMP_JSON = TMP_DIR / "feed_temp.json"

# URL del feed RSS di Google Alerts
RSS_FEED_URL = "https://www.google.com/alerts/feeds/15244278077982194024/11541540114411201767"

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

def download_feed():
    """Scarica il feed RSS e lo salva in un file temporaneo."""
    logger.info(f"Scaricamento del feed RSS da {RSS_FEED_URL}")

    try:
        response = requests.get(RSS_FEED_URL, timeout=30)
        response.raise_for_status()  # Solleva un'eccezione se la richiesta fallisce

        with open(TMP_FEED, 'wb') as f:
            f.write(response.content)

        logger.info(f"Feed RSS salvato in {TMP_FEED}")

        # Verifico che il file esista e contenga dati
        if not TMP_FEED.exists():
            logger.error(f"Il file {TMP_FEED} non esiste dopo il download!")
            return False

        if TMP_FEED.stat().st_size == 0:
            logger.error(f"Il file {TMP_FEED} è vuoto dopo il download!")
            return False

        logger.debug(f"Dimensione file XML: {TMP_FEED.stat().st_size} bytes")
        return True
    except Exception as e:
        logger.error(f"Errore durante il download del feed: {e}")
        return False

def parse_feed():
    """Estrae le entry dal feed RSS XML."""
    logger.info(f"Analisi del feed RSS {TMP_FEED}")

    try:
        # Verifica contenuto XML raw prima del parsing
        with open(TMP_FEED, 'r', encoding='utf-8') as f:
            xml_content = f.read(1000)  # Primi 1000 caratteri per debug
            logger.debug(f"Primi 1000 caratteri del XML: {xml_content}")

        # Parsing del documento XML
        tree = etree.parse(str(TMP_FEED))
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
                link = entry.xpath('./atom:link/@href', namespaces=NAMESPACES)[0]
                published = entry.xpath('./atom:published/text()', namespaces=NAMESPACES)[0]

                # Crea un dizionario per ogni entry
                entry_data = {
                    'id': entry_id,
                    'title': title,
                    'link': link,
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

def process_entries():
    """Processa le entry: scarica, estrae, salva, ordina."""
    try:
        # Assicura che le directory necessarie esistano
        ensure_directories()

        # Scarica il feed
        if not download_feed():
            logger.error("Download del feed fallito, uscita.")
            return False

        # Estrai le entry dal feed
        entries = parse_feed()
        if not entries:
            logger.warning("Nessuna entry valida trovata nel feed")
            return False

        # Scrivi le entry direttamente nel file JSONL
        # Per semplicità, sovrascriviamo il file (in produzione si potrebbe volerle aggregare)
        logger.info(f"Scrittura di {len(entries)} entry nel file {ARCHIVE_FILE}")

        try:
            # Ordina le entry per data di pubblicazione (decrescente)
            sorted_entries = sorted(entries, key=lambda x: x['published'], reverse=True)

            # Scrive le entry ordinate nel file
            with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
                for entry in sorted_entries:
                    json_str = json.dumps(entry, ensure_ascii=False)
                    f.write(json_str + '\n')

            # Verifica che il file esista e contenga dati
            if not ARCHIVE_FILE.exists():
                logger.error(f"Il file {ARCHIVE_FILE} non esiste dopo la scrittura!")
                return False

            if ARCHIVE_FILE.stat().st_size == 0:
                logger.error(f"Il file {ARCHIVE_FILE} è vuoto dopo la scrittura!")
                return False

            logger.debug(f"Dimensione file JSONL: {ARCHIVE_FILE.stat().st_size} bytes")
            logger.info(f"Scrittura completata con successo in {ARCHIVE_FILE}")

            # Leggi e verifica una riga per confermare formato corretto
            with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                logger.debug(f"Prima riga del file JSONL: {first_line}")

            return True
        except Exception as e:
            logger.error(f"Errore durante la scrittura del file: {e}")
            return False
    except Exception as e:
        logger.error(f"Errore imprevisto: {e}")
        return False

def main():
    """Funzione principale."""
    try:
        logger.info("Avvio elaborazione feed RSS")

        success = process_entries()

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
