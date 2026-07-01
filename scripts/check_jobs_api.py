import requests
r=requests.get('http://127.0.0.1:8000/api/intake/jobs', timeout=10)
print(r.status_code)
print(r.text[:2000])
