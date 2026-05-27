import requests, json
base='http://127.0.0.1:8000'
endpoints=['/api/onboarding/list','/api/analytics/dashboard','/api/offers/list']
for e in endpoints:
    try:
        r=requests.get(base+e, timeout=10)
        print(e, r.status_code)
        try:
            print(json.dumps(r.json(), indent=2)[:2000])
        except Exception:
            print('Non-JSON response:', r.text[:1000])
    except Exception as exc:
        print(e, 'ERROR', exc)
