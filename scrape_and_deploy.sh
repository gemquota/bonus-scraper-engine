#!/bin/bash
set -e
cd /data/data/com.termux/files/home/dev/codex/golf

echo "=== Killing old processes ==="
fuser -k 8000/tcp 2>/dev/null || true
pkill -9 -f "python3.*main.py" 2>/dev/null || true
pkill -9 -f "python3.*run_scraper" 2>/dev/null || true
sleep 2

echo "=== Running scraper ==="
python3 -u run_scraper.py 2>&1 | tee /tmp/scrape_run.log

echo "=== Exporting from DB to CSV ==="
python3 -c "
import csv, sqlite3, json

conn = sqlite3.connect('data/base.db')
c = conn.cursor()

HEADERS = ['url','mname','id','name','transactiontype','bonusfixed','amount','minwithdraw','maxwithdraw','rollover','balance','claimconfig','claimcondition','bonus','bonusrandom','reset','mintopup','maxtopup','referlink','perceived_value','is_new']

import os
marker = None
if os.path.exists('data/last_scrape_start.txt'):
    marker = open('data/last_scrape_start.txt').read().strip()
cutoff = marker
if not cutoff:
    cutoff = c.execute(\"SELECT datetime('now','-1 day')\").fetchone()[0]
c.execute('SELECT uid, eid, u, v, pv, raw, exp, fp, mirrors, s1, sl, mname, name FROM b WHERE sl >= ?', (cutoff,))
rows = c.fetchall()

with open('data/Dayne_Bonuses.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    for row in rows:
        uid, eid, u, v, pv, raw_json, exp, fp, mirrors, s1, sl, mname, name = row
        try:
            bonus = json.loads(raw_json) if raw_json else {}
        except:
            bonus = {}
        normalized = {k.lower(): val for k, val in bonus.items()} if bonus else {}
        csv_row = {
            'url': u, 'mname': mname or '', 'id': eid or '', 'name': name or '',
            'transactiontype': normalized.get('transactiontype', ''),
            'bonusfixed': normalized.get('bonusfixed', ''),
            'amount': v if v else normalized.get('amount', ''),
            'minwithdraw': normalized.get('minwithdraw', ''),
            'maxwithdraw': normalized.get('maxwithdraw', ''),
            'rollover': normalized.get('rollover', ''),
            'balance': normalized.get('balance', ''),
            'claimconfig': normalized.get('claimconfig', ''),
            'claimcondition': normalized.get('claimcondition', ''),
            'bonus': normalized.get('bonus', ''),
            'bonusrandom': normalized.get('bonusrandom', ''),
            'reset': normalized.get('reset', ''),
            'mintopup': normalized.get('mintopup', ''),
            'maxtopup': normalized.get('maxtopup', ''),
            'referlink': normalized.get('referlink', ''),
            'perceived_value': pv if pv else '',
            'is_new': 1 if sl and sl == s1 else 0,
        }
        writer.writerow(csv_row)
print(f'Exported {len(rows)} bonuses')
"

echo "=== Fresh-scrape CSV ==="
cp data/Dayne_Bonuses.csv data/Dayne_Bonuses_Fresh.csv

echo "=== Cleaning CSV ==="
python3 clean_bonuses.py data/Dayne_Bonuses.csv

echo "=== Building site + all-bonus CSVs ==="
python3 build_sites_csv.py

echo "=== Updating viewer app ==="
cp data/Dayne_Bonuses.csv dayne-bonuses-viewer/public/dayne-bonuses.csv
cp data/Dayne_Bonuses_Cleaned.csv dayne-bonuses-viewer/public/dayne-bonuses-cleaned.csv
cp data/Dayne_Bonuses_All.csv dayne-bonuses-viewer/public/dayne-bonuses-all.csv
cp data/Dayne_Sites.csv dayne-bonuses-viewer/public/dayne-sites.csv
cp data/Dayne_Bonuses_Fresh.csv dayne-bonuses-viewer/public/dayne-bonuses-fresh.csv

echo "=== Building viewer ==="
cd dayne-bonuses-viewer
npm run build 2>&1 | tail -5
cp app.json icon.svg dist/ 2>/dev/null || true

echo "=== Deploying to GitHub Pages ==="
git add -A
git commit -q -m "Update: fresh scrape $(date +%m-%d) + bonus data" || true
git push origin main
echo "Pushed — GitHub Actions deploys to https://gemquota.github.io/dayne-bonuses/"

echo "=== Done ==="
