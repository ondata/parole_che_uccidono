#!/bin/bash

set -x
set -e
set -u
set -o pipefail

folder="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mlr --ijsonl --ocsv cut -f link then put '$l=sub($link,"^(http.+//.+?/).+$","\1")' then cut -f l then count -g l then sort -tr count then label fonte "${folder}"/../data/feed_entries.jsonl > "${folder}"/../data/url_summary.csv
