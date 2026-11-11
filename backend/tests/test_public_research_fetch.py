from unittest.mock import Mock

import pytest
import requests

from app.services import public_research_fetch as fetch


def dns(address='93.184.216.34'):
    return [(2, 1, 6, '', (address, 443))]


def response(body=b'public page', status=200, headers=None):
    result = Mock(status=status, headers=headers or {})
    result.read.side_effect = [body, b'']
    return result


@pytest.mark.parametrize('url', [
    'file:///etc/passwd', 'ftp://example.org/file', 'http://user:pass@example.org',
    'http://example.org:8080/', 'http://example.org:0/',
])
def test_rejects_invalid_url_before_connecting(monkeypatch, url):
    pool = Mock()
    monkeypatch.setattr(fetch.urllib3, 'HTTPConnectionPool', pool)
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text(url)
    pool.assert_not_called()


@pytest.mark.parametrize('address', [
    '127.0.0.1', '10.0.0.1', '169.254.169.254', '192.168.1.1', '100.64.0.1',
    '0.0.0.0', '224.0.0.1', 'ff02::1', '::1', 'fc00::1', 'fe80::1', '::ffff:127.0.0.1', '64:ff9b::7f00:1',
])
def test_private_and_metadata_addresses_never_connect(monkeypatch, address):
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', lambda *a, **k: dns(address))
    pool = Mock()
    monkeypatch.setattr(fetch.urllib3, 'HTTPSConnectionPool', pool)
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')
    pool.assert_not_called()


def test_mixed_public_and_private_dns_answers_are_denied(monkeypatch):
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', lambda *a, **k: dns() + dns('10.1.1.1'))
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')


def test_pins_public_address_preserving_tls_hostname(monkeypatch):
    resolver = Mock(return_value=dns())
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', resolver)
    result = response('שלום'.encode())
    pool = Mock()
    pool.urlopen.return_value = result
    constructor = Mock(return_value=pool)
    monkeypatch.setattr(fetch.urllib3, 'HTTPSConnectionPool', constructor)
    assert fetch.fetch_public_text('https://example.org/path?q=one') == ('שלום', 200)
    assert constructor.call_args.kwargs['host'] == '93.184.216.34'
    assert constructor.call_args.kwargs['assert_hostname'] == 'example.org'
    assert constructor.call_args.kwargs['server_hostname'] == 'example.org'
    assert pool.urlopen.call_args.args == ('GET', '/path?q=one')
    assert pool.urlopen.call_args.kwargs['headers']['Host'] == 'example.org'
    assert pool.urlopen.call_args.kwargs['redirect'] is False
    assert pool.urlopen.call_args.kwargs['retries'] is False
    resolver.assert_called_once()
    result.close.assert_called_once()
    pool.close.assert_called_once()


def test_public_redirect_to_metadata_is_denied(monkeypatch):
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', lambda host, *a, **k: dns(
        '169.254.169.254' if host == '169.254.169.254' else '93.184.216.34'
    ))
    result = response(status=302, headers={'Location': 'http://169.254.169.254/latest/meta-data/'})
    pool = Mock()
    pool.urlopen.return_value = result
    constructor = Mock(return_value=pool)
    monkeypatch.setattr(fetch.urllib3, 'HTTPSConnectionPool', constructor)
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')
    constructor.assert_called_once()
    result.close.assert_called_once()


def test_redirect_loop_is_bounded(monkeypatch):
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', lambda *a, **k: dns())
    pool = Mock()
    pool.urlopen.return_value = response(status=302, headers={'Location': '/again'})
    monkeypatch.setattr(fetch.urllib3, 'HTTPSConnectionPool', Mock(return_value=pool))
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')
    assert pool.urlopen.call_count == fetch.MAX_REDIRECTS + 1


def test_size_limit_applies_to_decoded_stream_and_closes_response(monkeypatch):
    monkeypatch.setattr(fetch, 'MAX_BYTES', 4)
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', lambda *a, **k: dns())
    result = response(body=b'12345')
    pool = Mock()
    pool.urlopen.return_value = result
    monkeypatch.setattr(fetch.urllib3, 'HTTPSConnectionPool', Mock(return_value=pool))
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')
    assert result.read.call_args.kwargs['decode_content'] is True
    result.close.assert_called_once()
    pool.close.assert_called_once()


def test_dns_failure_is_closed(monkeypatch):
    monkeypatch.setattr(fetch.socket, 'getaddrinfo', Mock(side_effect=fetch.socket.gaierror('no DNS')))
    with pytest.raises(requests.RequestException):
        fetch.fetch_public_text('https://example.org/')
