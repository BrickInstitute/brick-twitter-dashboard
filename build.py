"""
Daily Twitter Dashboard Builder for Brick Institute.

Fetches all records from the Airtable Twitter Gündem table and generates
a static index.html using template.html as the base.

Runs in GitHub Actions daily at 06:00 UTC (~09:00 Istanbul).
"""

import os
import json
import sys
import urllib.request
import urllib.parse
import urllib.error


AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')
BASE_ID = 'appCkkzxHJXphOPjH'
TABLE_ID = 'tbleX5AwtDJbuwgoA'
PAGE_SIZE = 100


def fetch_all_records():
    """Paginate through all records in the table."""
    if not AIRTABLE_TOKEN:
        print('ERROR: AIRTABLE_TOKEN env var not set', file=sys.stderr)
        sys.exit(1)

    all_records = []
    offset = None

    while True:
        params = {'pageSize': str(PAGE_SIZE)}
        if offset:
            params['offset'] = offset

        url = f'https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={'Authorization': f'Bearer {AIRTABLE_TOKEN}'}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f'ERROR: Airtable API returned {e.code}: {e.read().decode()}', file=sys.stderr)
            sys.exit(1)

        all_records.extend(data.get('records', []))
        offset = data.get('offset')
        if not offset:
            break

    return all_records


def transform(rec):
    """Convert an Airtable record into the compact JSON shape the dashboard expects."""
    f = rec.get('fields', {})
    username = f.get('Username', '') or ''
    name = f.get('Name', '') or ''

    # Strip "@username — " prefix from the Name field if present
    title = name
    prefix = f'@{username} — '
    if title.startswith(prefix):
        title = title[len(prefix):]

    return {
        'u': username,
        't': title,
        'n': f.get('Notes', '') or '',
        'url': f.get('Tweet URL', '') or '',
        'l': int(f.get('Likes', 0) or 0),
        'v': int(f.get('Views', 0) or 0),
        'b': int(f.get('Bookmarks', 0) or 0),
        'r': int(f.get('Replies', 0) or 0),
        'rt': int(f.get('Retweets', 0) or 0),
        'e': int(f.get('Engagement', 0) or 0),
        'd': f.get('Tarih', '') or '',
        'c': f.get('Kategori', '') or '',
        'ty': f.get('İçerik Türü', []) or [],
    }


def main():
    print('Fetching records from Airtable...')
    records = fetch_all_records()
    print(f'Fetched {len(records)} records')

    tweets = [transform(r) for r in records]

    # Filter out records missing critical fields
    tweets = [t for t in tweets if t['d'] and t['u'] and t['url']]

    # Sort by date desc, then views desc
    tweets.sort(key=lambda x: (x['d'], x['v']), reverse=True)

    tweets_json = json.dumps(tweets, ensure_ascii=False, separators=(',', ':'))

    # Read template
    with open('template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    if '___TWEETS_DATA_PLACEHOLDER___' not in template:
        print('ERROR: template.html missing ___TWEETS_DATA_PLACEHOLDER___ marker', file=sys.stderr)
        sys.exit(1)

    output = template.replace('___TWEETS_DATA_PLACEHOLDER___', tweets_json)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output)

    print(f'OK: Generated index.html with {len(tweets)} tweets')


if __name__ == '__main__':
    main()
