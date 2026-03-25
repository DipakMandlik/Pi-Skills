#!/usr/bin/env python3
import urllib.request, json, sys

def api(method, path, body=None, token=None):
    url = 'http://localhost:8000' + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'body': json.loads(e.read())}
    except Exception as e:
        return {'error': str(e)}

print('=== Login ===')
login = api('POST', '/auth/login', {'email': 'admin@platform.local', 'password': 'admin123'})
print('Role:', login.get('role', '?'))
token = login.get('access_token', '')

print('=== Auth/Me ===')
me = api('GET', '/auth/me', token=token)
print('Role:', me.get('role', '?'), 'Email:', me.get('email', '?'))
user_id = me.get('user_id', '')

print('=== Skills ===')
skills = api('GET', '/skills', token=token)
print('Skills:', len(skills.get('skills', [])), 'loaded')

print('=== Models ===')
models = api('GET', '/models', token=token)
print('Models:', len(models.get('models', [])), 'loaded')

print('=== Assign + Execute ===')
api('POST', '/skills/assign', {'user_id': user_id, 'skill_id': 'skill_summarizer'}, token=token)
api('POST', '/models/assign', {'user_id': user_id, 'model_id': 'claude-3-haiku-20240307'}, token=token)
exec_result = api('POST', '/execute', {'skill_id': 'skill_summarizer', 'model_id': 'claude-3-haiku-20240307', 'prompt': 'Hello world', 'max_tokens': 50}, token=token)
print('Execute:', str(exec_result.get('result', exec_result))[:80])

print('=== Denied ===')
denied = api('POST', '/execute', {'skill_id': 'skill_summarizer', 'model_id': 'gpt-4o', 'prompt': 'test', 'max_tokens': 50}, token=token)
print('Denied:', denied.get('error', '?'), denied.get('body', {}).get('detail', ''))

print('=== Monitoring ===')
mon = api('GET', '/monitoring?page_size=5', token=token)
print('Logs:', mon.get('total', 0), 'Execs:', mon.get('summary', {}).get('total_executions', 0), 'Denials:', mon.get('summary', {}).get('total_denials', 0))
