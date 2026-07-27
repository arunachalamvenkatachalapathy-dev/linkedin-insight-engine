import os, requests, time, re

if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k.strip()] = v.strip()

gkey = os.environ.get('GEMINI_API_KEY')

def test_call(prompt):
    models = ['gemini-2.5-flash', 'gemini-2.0-flash']
    for m in models:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gkey}'
        for attempt in range(4):
            r = requests.post(url, json={'contents': [{'parts': [{'text': prompt}]}]})
            if r.status_code == 200:
                print(f'[{m}] 200 OK')
                return r.json()['candidates'][0]['content']['parts'][0]['text']
            elif r.status_code == 429:
                delay = 62
                try:
                    match = re.search(r'"retryDelay":\s*"(\d+)s"', r.text)
                    if match:
                        delay = int(match.group(1)) + 5
                except Exception:
                    pass
                print(f'[{m}] 429 Rate Limit. Sleeping {delay}s...')
                time.sleep(delay)
            else:
                print(f'[{m}] {r.status_code}: {r.text[:100]}')
                break
    raise RuntimeError('All failed')

for i in range(3):
    res = test_call(f'Give 1 line advice about climate change #{i}')
    print(f'Call {i+1} result: {res[:60]}...')
    time.sleep(10)
