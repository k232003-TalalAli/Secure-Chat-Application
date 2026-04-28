import json
import queue
import socket
import threading
import time
from typing import Dict, List, Optional


class SocketChatClient:
    """Background socket chat client with duplex send/receive support."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5555) -> None:
        self.host = host
        self.port = port
        self._peer_port: Optional[int] = None
        self.username = ""
        self.account_id = ""
        self.connected = False
        self.running = False
        self._listen_socket: Optional[socket.socket] = None
        self._active_receive_socket: Optional[socket.socket] = None
        self._active_send_socket: Optional[socket.socket] = None
        self._outgoing: queue.Queue[str] = queue.Queue()
        self._incoming: queue.Queue[Dict[str, str]] = queue.Queue()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._listen_thread: Optional[threading.Thread] = None
        self._send_thread: Optional[threading.Thread] = None
        self._peer_ip: Optional[str] = None

    def start(self, username: str, account_id: str) -> None:
        with self._lock:
            if self.running:
                return
            self.username = username
            self.account_id = account_id
            self.running = True
            self.connected = False
            self._stop_event.clear()
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._send_thread = threading.Thread(target=self._send_loop, daemon=True)
            self._listen_thread.start()
            self._send_thread.start()

    def stop(self) -> None:
        with self._lock:
            self.running = False
            self.connected = False
            self._stop_event.set()
        self._close_sockets()
        self._drain_queue(self._outgoing)
        self._drain_queue(self._incoming)

    def set_peer(self, peer_ip: Optional[str], peer_port: Optional[int]) -> None:
      with self._lock:
        if self._peer_ip == peer_ip and self._peer_port == peer_port:
            return
        self._peer_ip = peer_ip
        self._peer_port = peer_port
        self.connected = False
      self._close_send_socket()

    def queue_message(self, message_payload: Dict[str, str]) -> bool:
        if not self.running:
            return False
        try:
            body = json.dumps(message_payload)
        except Exception:
            return False
        self._outgoing.put(body)
        return True

    def consume_incoming(self) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        while True:
            try:
                messages.append(self._incoming.get_nowait())
            except queue.Empty:
                break
        return messages

    def is_connected(self) -> bool:
        with self._lock:
            return self.connected

    def _listen_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._listen_socket.bind((self.host, 0))  # automatic port allocation
                self.port = self._listen_socket.getsockname()[1]
                self._listen_socket.listen(4)
                self._listen_socket.settimeout(1.0)
                break
            except OSError:
                if self._listen_socket is not None:
                    try:
                        self._listen_socket.close()
                    except OSError:
                        pass
                    self._listen_socket = None
                time.sleep(0.4)

        if self._listen_socket is None:
            return

        while not self._stop_event.is_set():
            try:
                client_socket, _ = self._listen_socket.accept()
                threading.Thread(
                    target=self._handle_receive_connection,
                    args=(client_socket,),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_receive_connection(self, client_socket: socket.socket) -> None:
        with self._lock:
            self._active_receive_socket = client_socket
        client_socket.settimeout(1.0)
        buffer = b""
        try:
            while not self._stop_event.is_set():
                try:
                    chunk = client_socket.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        payload = json.loads(line.decode("utf-8"))
                        if isinstance(payload, dict):
                            self._incoming.put(payload)
                    except Exception:
                        continue
        finally:
            with self._lock:
                if self._active_receive_socket is client_socket:
                    self._active_receive_socket = None
            try:
                client_socket.close()
            except OSError:
                pass

    def _send_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._outgoing.get(timeout=0.5)
            except queue.Empty:
                continue

            if not self._ensure_sender_connected():
                self._outgoing.put(message)
                time.sleep(0.2)
                continue

            try:
                assert self._active_send_socket is not None
                self._active_send_socket.sendall(message.encode("utf-8") + b"\n")
                with self._lock:
                    self.connected = True
            except OSError:
                with self._lock:
                    self.connected = False
                self._close_send_socket()
                self._outgoing.put(message)
                time.sleep(0.3)

    def _ensure_sender_connected(self) -> bool:
        if self._active_send_socket is not None:
            return True

        with self._lock:
           peer_ip = self._peer_ip
           peer_port = self._peer_port

        if not peer_ip:
            return False

        send_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        send_socket.settimeout(1.0)
        try:
            if not peer_ip or not peer_port:
               return False

            send_socket.connect((peer_ip, peer_port))
            send_socket.settimeout(None)
        except OSError:
            try:
                send_socket.close()
            except OSError:
                pass
            return False

        with self._lock:
            self._active_send_socket = send_socket
            self.connected = True
        return True

    def _close_send_socket(self) -> None:
        send_socket = self._active_send_socket
        self._active_send_socket = None
        if send_socket is not None:
            try:
                send_socket.close()
            except OSError:
                pass

    def _close_sockets(self) -> None:
        if self._listen_socket is not None:
            try:
                self._listen_socket.close()
            except OSError:
                pass
            self._listen_socket = None

        if self._active_receive_socket is not None:
            try:
                self._active_receive_socket.close()
            except OSError:
                pass
            self._active_receive_socket = None

        self._close_send_socket()

    @staticmethod
    def _drain_queue(target_queue: queue.Queue) -> None:
        while True:
            try:
                target_queue.get_nowait()
            except queue.Empty:
                return
