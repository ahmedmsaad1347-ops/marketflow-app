"""Test fixtures complete real verification; no application bypass flags."""
from unittest.mock import patch


def prepare_client(client):
    config = client.get('/api/auth/config')
    assert config.status_code == 200, config.text
    client.headers['X-CSRF-Token'] = config.json()['csrf_token']
    return client


def signup_verified(client, main, **kwargs):
    prepare_client(client)
    with patch.object(main.auth, 'send_mail') as mail:
        response = client.post('/api/auth/signup', **kwargs)
    assert response.status_code == 202, response.text
    token = mail.call_args.args[2]
    verified = client.post('/api/auth/verify-email', json={'token': token})
    assert verified.status_code == 200, verified.text
    return client.get('/api/auth/me')
