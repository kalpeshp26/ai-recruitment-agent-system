import requests
BASE='http://127.0.0.1:8000'
payload={'title':'Smoke Job 2','department':'Eng'}
try:
    r=requests.post(BASE+'/api/intake/jobs', json=payload, timeout=10)
    print('STATUS', r.status_code)
    print('TEXT', r.text)
    try:
        print('JSON', r.json())
    except Exception as e:
        print('No JSON:', e)
except Exception as e:
    print('Request failed', e)
