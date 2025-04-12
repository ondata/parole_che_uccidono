#!/bin/bash

set -x
set -e
set -u
set -o pipefail

# Verifica la presenza di mlr (Miller)
check_mlr_installation() {
    if ! command -v mlr &> /dev/null; then
        echo "Errore: mlr (Miller) non è installato."
        echo "  - Altri sistemi: https://github.com/johnkerl/miller/releases"
        exit 1
    fi
}

# Esegui la verifica
check_mlr_installation

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mlr --ijsonl --ocsv cut -f link then put '$l=sub($link,"^(http.+//.+?/).+$","\1")' then cut -f l then count -g l then sort -tr count -f l then label fonte "${folder}"/../data/feed_entries.jsonl > "${folder}"/../data/url_summary.csv
