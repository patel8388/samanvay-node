"""Development-only HTTP block sync. Literal loopback; no wallet/admin API."""
import ipaddress
import json
import re
import threading
from urllib.parse import urlsplit, parse_qs
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from . import consensus, crypto
from .chain import MAX_DAG_BLOCKS

MAX_BODY = 2 * 1024 * 1024
MAX_RESPONSE_BLOCKS = 128
MAX_CONNECTIONS = 8


def _loopback_host(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _peer_url(peer):
    url = urlsplit(peer)
    if (url.scheme != 'http' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment
            or not _loopback_host(url.hostname) or url.port is None
            or not 1 <= url.port <= 65535):
        raise ValueError('peer must be literal-loopback HTTP with an explicit port')
    return url


def _strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON member')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('nonfinite JSON value')
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def _decimal_text(value):
    return isinstance(value, str) and re.fullmatch(r'(?:0|[1-9][0-9]*)', value) is not None


def _identity(chain):
    return {'network_id': chain.config['network_id'],
            'config_digest': crypto.sha256d(crypto.canonical(chain.config)),
            'genesis': consensus.block_hash(consensus.genesis(chain.config))}


def _block_snapshot(chain):
    """Return a stable commitment to the complete ordered page source."""
    hashes = (row[0] for row in chain.db.execute(
        'SELECT hash FROM blocks ORDER BY height ASC,hash ASC'))
    return crypto.sha256d(('\n'.join(hashes)).encode('ascii'))


class Handler(BaseHTTPRequestHandler):
    server_version = 'SamanvayLocal/0.1'
    protocol_version = 'HTTP/1.1'

    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def _send(self, code, obj):
        data = crypto.canonical(obj)
        if len(data) > MAX_BODY:
            code, data = 413, b'{"error":"response resource limit"}'
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def _json_body(self):
        if (self.headers.get('Transfer-Encoding')
                or self.headers.get('Content-Type', '').split(';', 1)[0].lower() != 'application/json'
                or len(self.headers.get_all('Content-Length') or []) != 1):
            raise ValueError('one content length and application/json required')
        length = int(self.headers.get('Content-Length', '-1'))
        if not 1 <= length <= MAX_BODY:
            raise ValueError('request byte limit')
        data = self.rfile.read(length)
        if len(data) != length:
            raise ValueError('incomplete request')
        result = _strict_json(data)
        if not isinstance(result, dict):
            raise ValueError('JSON object required')
        return result

    def do_GET(self):
        try:
            url = urlsplit(self.path)
            with self.server.chain.lock:
                chain = self.server.chain
                if url.path == '/status' and not url.query:
                    tip = chain.tip
                    return self._send(200, {**_identity(chain), 'height': tip['height'],
                                            'hash': tip['hash'], 'work': str(tip['work']), 'network': 'tSAMV'})
                if url.path != '/blocks':
                    return self._send(404, {'error': 'not found'})
                query = parse_qs(url.query, strict_parsing=True, keep_blank_values=True) if url.query else {}
                if set(query) - {'offset', 'snapshot'} or any(len(v) != 1 for v in query.values()):
                    raise ValueError('invalid pagination')
                offset = int(query.get('offset', ['0'])[0])
                if not 0 <= offset <= MAX_DAG_BLOCKS:
                    raise ValueError('invalid offset')
                snapshot = _block_snapshot(chain)
                requested_snapshot = query.get('snapshot', [snapshot])[0]
                if (not isinstance(requested_snapshot, str) or
                        consensus.HASH.fullmatch(requested_snapshot) is None or
                        requested_snapshot != snapshot):
                    return self._send(409, {'error': 'pagination snapshot changed'})
                rows = chain.db.execute('SELECT block FROM blocks ORDER BY height ASC,hash ASC LIMIT ? OFFSET ?',
                                        (MAX_RESPONSE_BLOCKS, offset)).fetchall()
                result, size = [], 0
                for row in rows:
                    encoded = row['block'].encode()
                    if result and size + len(encoded) > MAX_BODY // 2:
                        break
                    result.append({'block': json.loads(row['block'])})
                    size += len(encoded)
                count = chain.db.execute('SELECT COUNT(*) FROM blocks').fetchone()[0]
                following = offset + len(result)
                return self._send(200, {'blocks': result,
                                        'snapshot': snapshot,
                                        'next_offset': following if following < count else None})
        except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
            return self._send(400, {'error': 'invalid bounded local request'})

    def do_POST(self):
        if self.path not in ('/blocks', '/submit'):
            return self._send(404, {'error': 'not found'})
        try:
            block = self._json_body()
            digest = self.server.chain.add_block(block)
            self._send(200, {'accepted': True, 'hash': digest})
        except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
            self._send(400, {'accepted': False, 'error': 'invalid block/request'})

    def log_message(self, *args):
        pass


class _LocalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = MAX_CONNECTIONS

    def __init__(self, address, chain):
        if not _loopback_host(address[0]):
            raise ValueError('public and DNS binds are unsupported')
        self.chain = chain
        self.peer_slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if not self.peer_slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.peer_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.peer_slots.release()


def serve(chain, host='127.0.0.1', port=8765):
    server = _LocalHTTPServer((host, port), chain)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


def _get(url, path, timeout):
    connection = HTTPConnection(url.hostname, url.port, timeout=timeout)
    try:
        try:
            connection.request('GET', path, headers={'Accept': 'application/json', 'Connection': 'close'})
            response = connection.getresponse()
            lengths = response.msg.get_all('Content-Length', [])
            transfer = response.msg.get_all('Transfer-Encoding', [])
            content_types = response.msg.get_all('Content-Type', [])
            if (response.status != 200 or len(lengths) != 1 or transfer or
                    len(content_types) != 1 or
                    content_types[0].split(';', 1)[0].strip().lower() != 'application/json' or
                    not _decimal_text(lengths[0])):
                raise ValueError('peer status/framing rejected')
            length = int(lengths[0])
            if not 1 <= length <= MAX_BODY:
                raise ValueError('peer status/size rejected')
            data = response.read(length + 1)
            if len(data) != length:
                raise ValueError('peer response framing rejected')
            result = _strict_json(data)
            if not isinstance(result, dict):
                raise ValueError('invalid peer JSON')
            return result
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('peer HTTP/framing failure') from exc
    finally:
        connection.close()


def sync(chain, peer, timeout=3):
    url = _peer_url(peer)
    timeout = max(0.1, min(float(timeout), 10))
    identity = _get(url, '/status', timeout)
    if any(identity.get(key) != value for key, value in _identity(chain).items()):
        raise ValueError('peer genesis/network mismatch')
    tip_height = identity.get('height')
    tip_hash = identity.get('hash')
    tip_work = identity.get('work')
    if (type(tip_height) is not int or not 0 <= tip_height <= MAX_DAG_BLOCKS or
            not isinstance(tip_hash, str) or consensus.HASH.fullmatch(tip_hash) is None or
            not _decimal_text(tip_work)):
        raise ValueError('invalid peer status tip')
    offset, accepted, snapshot, seen, received = 0, 0, None, set(), []
    for _ in range(MAX_DAG_BLOCKS + 1):
        path = '/blocks?offset=' + str(offset)
        if snapshot is not None:
            path += '&snapshot=' + snapshot
        response = _get(url, path, timeout)
        blocks = response.get('blocks')
        page_snapshot = response.get('snapshot')
        if (not isinstance(blocks, list) or not blocks or
                len(blocks) > MAX_RESPONSE_BLOCKS or
                not isinstance(page_snapshot, str) or consensus.HASH.fullmatch(page_snapshot) is None):
            raise ValueError('peer block list bound')
        if snapshot is None:
            snapshot = page_snapshot
        elif page_snapshot != snapshot:
            raise ValueError('peer pagination snapshot changed')
        if offset != len(received) or len(received) + len(blocks) > MAX_DAG_BLOCKS:
            raise ValueError('invalid peer pagination offset')
        for item in blocks:
            if not isinstance(item, dict) or set(item) != {'block'}:
                raise ValueError('peer block envelope')
            digest = consensus.block_hash(item['block'])
            if digest in seen:
                raise ValueError('peer pagination repeated block')
            seen.add(digest)
            received.append(digest)
            known = chain.get(digest) is not None
            chain.add_block(item['block'])  # Invalid work never swallowed as a sync success.
            accepted += not known
        following = response.get('next_offset')
        if following is None:
            calculated = crypto.sha256d(('\n'.join(received)).encode('ascii'))
            if calculated != snapshot:
                raise ValueError('peer pagination snapshot mismatch')
            advertised = chain.get(tip_hash)
            if (advertised is None or advertised['height'] != tip_height or
                    advertised['work'] != int(tip_work)):
                raise ValueError('peer advertised tip unavailable')
            return accepted
        if (type(following) is not int or following != offset + len(blocks) or
                not offset < following <= MAX_DAG_BLOCKS):
            raise ValueError('invalid peer pagination progress')
        offset = following
    raise ValueError('sync batch limit')
