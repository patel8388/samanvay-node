import json
import socket
import threading
import unittest
from unittest.mock import patch, MagicMock
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile

from samanvay import consensus, crypto, params
from samanvay.chain import Chain
from samanvay.server import Handler, _LocalHTTPServer, _identity, _get, _peer_url, sync


class NetworkHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.chain = Chain(Path(self.tmp.name) / "chain.sqlite3", params.default_config("devnet"))
        self.server = _LocalHTTPServer(("127.0.0.1", 0), self.chain)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.chain.close()
        self.tmp.cleanup()

    def status_and_genesis_page(self):
        tip = self.chain.tip
        status = {**_identity(self.chain), 'height': 0, 'hash': tip['hash'], 'work': '0'}
        page = {'blocks': [{'block': tip['block']}], 'next_offset': None,
                'snapshot': crypto.sha256d(tip['hash'].encode('ascii'))}
        return status, page

    def test_sync_rejects_false_tip_and_false_snapshot(self):
        status, page = self.status_and_genesis_page()
        for altered_status, altered_page in (
                ({**status, 'height': 10, 'hash': 'f' * 64, 'work': '2560'}, page),
                (status, {**page, 'snapshot': 'a' * 64}),
                ({**status, 'height': True}, page)):
            with self.subTest(status=altered_status):
                with patch('samanvay.server._get', side_effect=[altered_status, altered_page]):
                    with self.assertRaises(ValueError):
                        sync(self.chain, 'http://127.0.0.1:1234')

    def test_sync_rejects_skipped_repeated_and_changed_pages(self):
        status, page = self.status_and_genesis_page()
        with patch('samanvay.server._get', side_effect=[status, {**page, 'next_offset': 2}]):
            with self.assertRaises(ValueError):
                sync(self.chain, 'http://127.0.0.1:1234')
        for final in (page, {**page, 'snapshot': 'b' * 64}):
            with patch('samanvay.server._get', side_effect=[status, {**page, 'next_offset': 1}, final]):
                with self.assertRaises(ValueError):
                    sync(self.chain, 'http://127.0.0.1:1234')

    def test_peer_response_framing_rejects_duplicates_chunked_short_and_wrong_type(self):
        cases = [
            [('Content-Length', '2'), ('Content-Length', '2'), ('Content-Type', 'application/json')],
            [('Content-Length', '2'), ('Transfer-Encoding', 'chunked'), ('Content-Type', 'application/json')],
            [('Content-Length', '3'), ('Content-Type', 'application/json')],
            [('Content-Length', '2'), ('Content-Type', 'text/plain')],
            [('Content-Type', 'application/json')],
        ]
        for headers in cases:
            with self.subTest(headers=headers):
                response = MagicMock()
                response.status = 200
                response.msg = Message()
                for key, value in headers:
                    response.msg[key] = value
                response.read.return_value = b'{}'
                with patch('samanvay.server.HTTPConnection') as connection:
                    connection.return_value.getresponse.return_value = response
                    with self.assertRaises(ValueError):
                        _get(_peer_url('http://127.0.0.1:1234'), '/status', 1)
                    connection.return_value.close.assert_called_once()

    def test_real_multipage_sync_verifies_complete_snapshot(self):
        for index in range(130):
            self.chain.mine('s' + '0' * 39, timestamp=index + 1)
        target = Chain(Path(self.tmp.name) / 'target.sqlite3')
        try:
            self.assertEqual(sync(target, 'http://127.0.0.1:%d' % self.server.server_address[1]), 130)
            self.assertEqual(target.tip['hash'], self.chain.tip['hash'])
            self.assertEqual(target.state(), self.chain.state())
        finally:
            target.close()

    def test_duplicate_content_length_is_rejected_without_block_mutation(self):
        port = self.server.server_address[1]
        request = (
            f"POST /blocks HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Content-Type: application/json\r\nContent-Length: 2\r\n"
            "Content-Length: 2\r\nConnection: close\r\n\r\n{}"
        ).encode()
        with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
            sock.sendall(request)
            response = sock.recv(4096)
        self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
        self.assertEqual(self.chain.db.execute("SELECT COUNT(*) FROM blocks").fetchone()[0], 1)

    def test_old_page_snapshot_is_not_reported_as_current_after_mutation(self):
        # A page token must commit to the whole ordered source, not just the tip.
        import http.client
        port = self.server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/blocks?offset=0")
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        page = json.loads(response.read())
        conn.close()
        self.chain.mine("s" + "0" * 39)
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", "/blocks?offset=1&snapshot=" + page["snapshot"])
        changed = conn.getresponse()
        self.assertEqual(changed.status, 409)
        conn.close()

    def test_sync_rejects_empty_final_page_instead_of_false_success(self):
        chain = self.chain
        identity = _identity(chain)
        snapshot = "a" * 64

        class EmptyPage(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/status":
                    body = json.dumps({**identity, "height": 0, "hash": chain.tip["hash"],
                                       "work": "0", "network": "tSAMV"}).encode()
                else:
                    body = json.dumps({"blocks": [], "snapshot": snapshot,
                                       "next_offset": None}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        peer = ThreadingHTTPServer(("127.0.0.1", 0), EmptyPage)
        thread = threading.Thread(target=peer.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(ValueError):
                sync(chain, "http://127.0.0.1:%d" % peer.server_address[1])
        finally:
            peer.shutdown()
            thread.join(timeout=2)
            peer.server_close()


if __name__ == "__main__":
    unittest.main()
