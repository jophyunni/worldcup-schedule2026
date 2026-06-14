#!/usr/bin/env python3
"""
Repository updater for World Cup schedule data.
Purpose:
  - Read current data/data/matches.json
  - Fetch official FIFA schedule page HTML
  - Try to replace obvious TBD placeholders when confirmed team names are found
  - Rewrite data/data/matches.json with new metadata.lastUpdatedUtc

Important:
  This is a practical starter implementation, not an official FIFA API client.
  HTML structures change, so selectors/regex may need maintenance.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / 'data' / 'matches.json'
FIFA_URL = 'https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums'

TEAM_NAMES = [
    'Mexico','South Africa','Korea Republic','Czechia','Canada','Bosnia and Herzegovina','USA','Paraguay','Qatar','Switzerland',
    'Brazil','Morocco','Haiti','Scotland','Australia','Türkiye','Côte d\'Ivoire','Ecuador','Germany','Curaçao','Netherlands',
    'Japan','Sweden','Tunisia','Saudi Arabia','Uruguay','Spain','Cabo Verde','IR Iran','New Zealand','France','Senegal','Iraq',
    'Norway','Argentina','Algeria','Austria','Jordan','Ghana','Panama','England','Croatia','Portugal','Congo DR','Uzbekistan','Colombia'
]

def fetch_html(url: str) -> str:
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))

def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def build_match_text_patterns(html: str):
    # Very forgiving text normalization.
    text = re.sub(r'\s+', ' ', html)
    return text

def extract_confirmed_pairs(text: str):
    # Simple extraction against known team names.
    pairs = set()
    escaped = sorted(TEAM_NAMES, key=len, reverse=True)
    union = '|'.join(re.escape(t) for t in escaped)
    pattern = re.compile(rf'({union})\s*(?:v|vs\.?|-)\s*({union})', re.IGNORECASE)
    for a,b in pattern.findall(text):
        pairs.add((a, b))
        pairs.add((b, a))
    return pairs

def looks_placeholder(name: str) -> bool:
    n = (name or '').strip().lower()
    return n in {'tbd', ''} or n.startswith('winner ') or n.startswith('runner-up ') or n.startswith('3rd') or n.startswith('third ') or n.startswith('loser ')

def main() -> int:
    html = fetch_html(FIFA_URL)
    text = build_match_text_patterns(html)
    confirmed_pairs = extract_confirmed_pairs(text)
    payload = load_json(DATA_FILE)
    changed = 0

    # This conservative updater only flips generic TBD/TBD when there is an exact same UTC+venue record in a manual mapping.
    # Add your manual stage mapping here once FIFA publishes/embeds bracket pairings consistently.
    manual_updates = {
        # Example:
        # ('2026-07-19T19:00:00Z', 'New York New Jersey Stadium'): ('Winner SF1', 'Winner SF2')
    }

    for m in payload.get('matches', []):
        key = (m.get('utc'), m.get('venue'))
        if key in manual_updates and (looks_placeholder(m.get('home')) or looks_placeholder(m.get('away'))):
            new_home, new_away = manual_updates[key]
            if (m.get('home'), m.get('away')) != (new_home, new_away):
                m['home'], m['away'] = new_home, new_away
                changed += 1

    payload.setdefault('metadata', {})['source'] = 'Official FIFA page / repository updater'
    payload['metadata']['lastUpdatedUtc'] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    payload['metadata']['detectedPairs'] = len(confirmed_pairs)
    save_json(DATA_FILE, payload)
    print(f'Updated data file. Changed matches: {changed}. Detected text pairs: {len(confirmed_pairs)}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
