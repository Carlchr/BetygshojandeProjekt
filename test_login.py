import requests

s = requests.Session()
r = s.post('http://127.0.0.1:5500/login', data={'username':'test','password':'test'}, allow_redirects=False)
print('status', r.status_code)
print('headers', r.headers)
print('text', r.text[:200])
if 'Location' in r.headers:
    print('redirect', r.headers['Location'])
    r2 = s.get('http://127.0.0.1:5500' + r.headers['Location'])
    print('after', r2.status_code, r2.text[:200])