import atexit
import html
import hmac
import ipaddress
import json
import secrets
import socket
import traceback

import streamlit as st

from connection_state_manager import get_connection_manager
import database_helper
import msg_security
from socket_chat_client import SocketChatClient


def _debug(message: str) -> None:
    print(f"[streamlit_app] {message}", flush=True)


# ─────────────────────────────────────────────────────────────────────────────

def apply_blue_dark_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bg-main: #1a2f4d;
                --bg-panel: #2a4066;
                --bg-input: #3a5580;
                --text-main: #f0f4ff;
                --text-muted: #b8cde8;
                --accent: #4a8fff;
                --accent-2: #7ab5ff;
                --border: #4a6fa3;
            }

            html, body {
                background-color: #1a2f4d !important;
            }

            .stApp {
                background:
                    radial-gradient(1200px 500px at 20% -10%, #2d5a8f 0%, transparent 60%),
                    radial-gradient(900px 420px at 95% 0%, #234a75 0%, transparent 58%),
                    linear-gradient(180deg, #1a2f4d 0%, #1d3a54 100%) !important;
                color: var(--text-main);
            }

            [data-testid="stHeader"] {
                background: rgba(26, 47, 77, 0.8) !important;
                border-bottom: 1px solid rgba(74, 143, 255, 0.25);
            }

            h1, h2, h3, p, label, span {
                color: var(--text-main) !important;
            }

            .stTextInput > div > div > input {
                background-color: var(--bg-input) !important;
                color: var(--text-main) !important;
                border: 1px solid var(--border) !important;
            }

            .stTextInput > label {
                color: var(--text-muted) !important;
            }

            .stButton > button {
                background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
                color: #ffffff !important;
                border: 1px solid #8ab4ff !important;
                border-radius: 10px !important;
                font-weight: 600 !important;
            }

            .stButton > button:hover {
                filter: brightness(1.12);
            }

            .stSuccess, .stInfo, .stWarning, .stError {
                background-color: rgba(42, 64, 102, 0.9) !important;
                border: 1px solid var(--border) !important;
            }

            /* ── Transparent wrappers ── */
            [data-testid="stMainBlockContainer"],
            [data-testid="stVerticalBlock"],
            [data-testid="stHorizontalBlock"],
            [data-testid="stChatFloatingInputContainer"],
            [data-testid="stChatInput"],
            [data-testid="stBottomBlockContainer"],
            .element-container, .main, .block-container {
                background-color: transparent !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            /* ── stBottom: nuke white with wildcard selector ── */
            [data-testid="stBottom"] * {
                background-color: transparent !important;
                box-shadow: none !important;
            }
            [data-testid="stBottom"],
            [data-testid="stBottom"] > div,
            [data-testid="stBottom"] > div > div,
            [data-testid="stBottom"] > div > div > div,
            [data-testid="stBottom"] > div > div > div > div,
            [data-testid="stBottom"] > div > div > div > div > div {
                background: #1a2f4d !important;
                background-color: #1a2f4d !important;
                box-shadow: none !important;
                border: none !important;
            }

            /* Preserve textarea and button colours inside stBottom */
            [data-testid="stBottom"] textarea {
                background: #223f66 !important;
            }
            [data-testid="stBottom"] button {
                background: #4a8fff !important;
            }

            /* Thin accent border on top */
            [data-testid="stBottom"] {
                border-top: 1px solid rgba(74,143,255,0.2) !important;
            }

            /* ── Chat input pill ── */
            [data-testid="stChatInput"] textarea {
                background: #223f66 !important;
                color: #f0f4ff !important;
                border: 1px solid #4a6fa3 !important;
                border-radius: 24px !important;
                padding: 0.55rem 3rem 0.55rem 1.1rem !important;
                font-size: 0.9rem !important;
                line-height: 1.4 !important;
                resize: none !important;
            }

            [data-testid="stChatInput"] textarea::placeholder {
                color: #8ab4cc !important;
            }

            /* Remove red focus ring — use a subtle blue glow instead */
            [data-testid="stChatInput"] textarea:focus {
                outline: none !important;
                box-shadow: none !important;
                border-color: #4a8fff !important;
            }
            [data-testid="stChatInput"] textarea:focus-visible {
                outline: none !important;
                box-shadow: none !important;
                border-color: #4a8fff !important;
            }

            /* ── Send button centred in the pill ── */
            [data-testid="stChatInput"] button {
                background: #4a8fff !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 50% !important;
                width: 30px !important;
                height: 30px !important;
                min-width: 0 !important;
                padding: 0 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                position: absolute !important;
                right: 8px !important;
                top: 50% !important;
                transform: translateY(-50%) !important;
                margin: 0 !important;
            }

            [data-testid="stChatInput"] button:hover {
                background: #6a9fff !important;
            }

            /* Divider styling */
            hr {
                border-color: rgba(74, 143, 255, 0.3) !important;
                margin: 0.75rem 0 !important;
            }

            /* Caption styling for empty state */
            .stCaption {
                color: var(--text-muted) !important;
                text-align: center;
                font-style: italic;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_local_ip_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    ipaddress.ip_address(ip)
    return ip


def secure_username_check(username: str) -> bool:
    return database_helper.get_account_id_by_username(username) is not None


def secure_password_check(account_id: str, chat_password: str) -> bool:
    if len(chat_password) < 1 or len(chat_password) > 128:
        return False
    stored_hash = database_helper.get_password(account_id)
    if not stored_hash:
        return False
    entered_hash = msg_security.hash_data(chat_password)
    return hmac.compare_digest(entered_hash, stored_hash)


def show_chat_screen() -> None:
    st.session_state["chat_open"] = True
    st.session_state["status_message"] = ""


def close_chat() -> None:
    st.session_state["chat_open"] = False


def init_session_state() -> None:
    defaults = {
        "connected": False,
        "chat_open": False,
        "username": "",
        "account_id": "",
        "status_message": "",
        "login_error": "",
        "session_id": secrets.token_hex(16),
        "manager_started": False,
        "chat_messages": [],
        "pending_outgoing_message": "",
        "socket_client": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _get_socket_chat_client() -> SocketChatClient:
    client = st.session_state.get("socket_client")
    if client is None:
        client = SocketChatClient()
        st.session_state["socket_client"] = client
    return client


def _sync_chatlogs_to_db_safe() -> None:
    try:
        database_helper.sync_chatlogs_from_temp_to_db()
        _debug("Chatlogs synced to DB successfully")
    except Exception:
        _debug("Chatlogs sync to DB failed")
        traceback.print_exc()


def process_events() -> bool:
    """Process queued events. Returns True if a rerun is needed."""
    username = st.session_state.get("username", "")
    if not username:
        return False
    manager = get_connection_manager()
    events = manager.consume_events(username)
    needs_rerun = False
    for event_name in events:
        if event_name == "show_chat":
            show_chat_screen()
            needs_rerun = True
        elif event_name == "close_chat":
            close_chat()
            needs_rerun = True
    return needs_rerun


def render_waiting_state() -> None:
    st.markdown(
        """
        <style>
            .wait-wrap {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin-top: 2rem;
            }
            .loader {
                width: 72px;
                height: 72px;
                border: 7px solid #d8e2f0;
                border-top: 7px solid #1f77b4;
                border-radius: 50%;
                animation: spin 1.1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .wait-text {
                margin-top: 1rem;
                font-size: 1.15rem;
                font-weight: 600;
            }
        </style>
        <div class="wait-wrap">
            <div class="loader"></div>
            <div class="wait-text">Waiting for other user...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _parse_chatlogs(raw_content: str) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for line in raw_content.splitlines():
        entry = line.strip()
        if not entry:
            continue
        try:
            payload = json.loads(entry)
            sender = str(payload.get("sender", "")).strip()
            encrypted = str(payload.get("encrypted", "")).strip()
            if sender and encrypted:
                parsed.append({"sender": sender, "encrypted": encrypted})
        except Exception:
            continue
    return parsed


def _load_chat_messages_from_temp() -> list[dict[str, str]]:
    raw = database_helper.get_chatlogs() or ""
    encrypted_entries = _parse_chatlogs(raw)
    messages: list[dict[str, str]] = []
    if not encrypted_entries and raw.strip():
        # Backward compatibility for older single-block encrypted chatlogs.
        try:
            legacy_text = msg_security.decrypt_message(raw.strip())
            if legacy_text:
                messages.append({"sender": "History", "text": legacy_text})
        except Exception:
            pass
        return messages

    for item in encrypted_entries:
        encrypted = item.get("encrypted", "")
        sender = item.get("sender", "")
        try:
            text = msg_security.decrypt_message(encrypted)
        except Exception:
            text = ""
        if sender and text:
            messages.append({"sender": sender, "text": text})
    return messages


def _append_encrypted_to_temp(sender: str, encrypted_text: str) -> None:
    payload = json.dumps({"sender": sender, "encrypted": encrypted_text}, ensure_ascii=True)
    database_helper.append_chatlogs_temp_line(payload)

def _get_other_user_connection(my_username: str):
    for account_id in database_helper.get_all_account_ids():
        username = database_helper.get_username(account_id)
        if not username or username == my_username:
            continue

        ip, port = database_helper.get_connection_info(account_id)
        if ip and port:
            return ip, port

    return None, None

def _pull_incoming_socket_messages() -> None:
    my_username = st.session_state.get("username", "")
    client = _get_socket_chat_client()
    incoming = client.consume_incoming()
    if not incoming:
        return
    for payload in incoming:
        sender = str(payload.get("sender", "")).strip()
        encrypted = str(payload.get("encrypted", "")).strip()
        if not sender or not encrypted:
            continue
        try:
            text = msg_security.decrypt_message(encrypted)
        except Exception:
            continue
        st.session_state["chat_messages"].append({"sender": sender, "text": text})
        # Keep encrypted chat cache synchronized locally.
        _append_encrypted_to_temp(sender, encrypted)
        if sender != my_username:
            st.session_state["pending_outgoing_message"] = ""


@st.fragment(run_every=2)
def _render_message_feed() -> None:
    """Auto-refreshing fragment — only the feed, reruns every 2 s."""
    my_username = st.session_state.get("username", "")

    st.markdown(
        """
        <style>
            .wa-feed { display: flex; flex-direction: column; gap: 10px; padding: 10px 1rem; }
            .wa-row { display: flex; width: 100%; }
            .wa-row.sent { justify-content: flex-end;  padding-left: 25%; }
            .wa-row.recv { justify-content: flex-start; padding-right: 25%; }
            .wa-bubble {
                display: inline-block;
                padding: 7px 12px;
                border-radius: 8px;
                font-size: 0.9rem;
                line-height: 1.45;
                word-wrap: break-word;
                word-break: break-word;
                white-space: pre-wrap;
                box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                max-width: 100%;
            }
            .wa-bubble.sent { background: #2e5fc2; color: #fff; border-bottom-right-radius: 2px; }
            .wa-bubble.recv {
                background: #2d4f7c; color: #deeeff;
                border: 1px solid rgba(100,160,255,0.18);
                border-bottom-left-radius: 2px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _pull_incoming_socket_messages()
    messages = st.session_state.get("chat_messages", [])

    if not messages:
        st.caption("No messages yet. Start the conversation.")
    else:
        rows_html = ""
        for message in messages:
            sender  = message.get("sender", "Unknown")
            body    = message.get("text", "")
            is_mine = sender == my_username
            side    = "sent" if is_mine else "recv"
            safe_body = html.escape(body)
            rows_html += (
                f'<div class="wa-row {side}">'
                f'<div class="wa-bubble {side}">{safe_body}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="wa-feed">{rows_html}</div>',
            unsafe_allow_html=True,
        )


def render_chat_screen() -> None:
    st.success("Secure chat is connected")

    manager = get_connection_manager()
    my_username = st.session_state.get("username", "")
    _debug(f"render_chat_screen() for user={my_username!r}")

    st.subheader("Live Chat")

    # Only keep Disconnect — Refresh is no longer needed
    btn_col1, btn_col2 = st.columns([1, 3])
    with btn_col1:
        disconnect_clicked = st.button("Disconnect", type="secondary", key="chat_disconnect_button", use_container_width=True)

    if disconnect_clicked:
        _debug(f"Disconnect button pressed by {my_username!r}")
        account_id = st.session_state.get("account_id")
        if account_id:
            try:
                database_helper.update_connection_info(account_id, None, None)
                _debug(f"Cleared IP address for account_id={account_id!r}")
            except Exception:
                _debug("Failed to clear IP address during disconnect")
                traceback.print_exc()
        _sync_chatlogs_to_db_safe()

        _get_socket_chat_client().stop()
        st.session_state["socket_client"] = None
        manager.disconnect_user(st.session_state["username"], st.session_state["session_id"])
        close_chat()
        st.session_state["connected"] = False
        st.session_state["username"] = ""
        st.session_state["account_id"] = ""
        st.session_state["status_message"] = "You disconnected"
        st.rerun()

    # Feed auto-refreshes every 2s inside fragment
    _render_message_feed()

    other_ip, other_port = _get_other_user_connection(my_username)
    socket_client = _get_socket_chat_client()
    socket_client.set_peer(other_ip, other_port)
    input_disabled = not (other_ip and other_port)
    outgoing_message = st.chat_input("Type a message...", disabled=input_disabled)
    if outgoing_message:
        _debug(f"Outgoing message submitted by {my_username!r}: {outgoing_message!r}")
        if not (other_ip and other_port):
            st.warning("Other user is disconnected.")
            return

        encrypted = msg_security.encrypt_message(outgoing_message.strip())
        payload = {"sender": my_username, "encrypted": encrypted}
        sent = socket_client.queue_message(payload)
        if sent:
            st.session_state["chat_messages"].append({"sender": my_username, "text": outgoing_message.strip()})
            _append_encrypted_to_temp(my_username, encrypted)
            st.session_state["pending_outgoing_message"] = outgoing_message.strip()
        else:
            st.warning("Message could not be sent right now.")


def connect_user(username: str, chat_password: str) -> None:
    st.session_state["login_error"] = ""
    username = username.strip()
    _debug(f"connect_user() called for username={username!r}")

    try:
        database_helper.cache_data(include_chatlogs=True)
        _debug("connect_user() cache_data() completed successfully")
    except Exception:
        _debug("connect_user() cache_data() failed")
        traceback.print_exc()
        st.session_state["login_error"] = "Could not load user data. Please try again."
        return

    if not secure_username_check(username):
        _debug(f"connect_user() invalid username={username!r}")
        st.session_state["login_error"] = "Invalid username."
        return

    account_id = database_helper.get_account_id_by_username(username)
    if account_id is None:
        _debug(f"connect_user() account_id lookup failed for username={username!r}")
        st.session_state["login_error"] = "Invalid username."
        return

    if not secure_password_check(account_id, chat_password):
        _debug(f"connect_user() password check failed for account_id={account_id!r}")
        st.session_state["login_error"] = "Invalid chat password."
        return

    try:
        ip_address = get_local_ip_address()
        _debug(f"connect_user() local ip resolved as {ip_address!r}")
    except (OSError, ValueError):
        _debug("connect_user() could not resolve local IP")
        st.session_state["login_error"] = "Could not resolve local IP address."
        return

    manager = get_connection_manager()
    manager.register_event_consumer(username)
    try:
        database_helper.update_ip_address(account_id, ip_address)
        manager.connect_user(username, ip_address, st.session_state["session_id"])
        _debug(f"connect_user() registered session for {username!r} with session_id={st.session_state['session_id']!r}")
    except Exception:
        _debug("connect_user() failed while updating IP or registering manager state")
        traceback.print_exc()
        st.session_state["login_error"] = "Could not connect right now. Please try again."
        return

    st.session_state["username"] = username
    st.session_state["account_id"] = account_id
    st.session_state["connected"] = True
    st.session_state["status_message"] = ""
    st.session_state["login_error"] = ""
    st.session_state["chat_messages"] = _load_chat_messages_from_temp()

    socket_client = _get_socket_chat_client()
    socket_client.stop()
    socket_client.start(username=username, account_id=account_id)
    database_helper.update_connection_info(
    account_id,
    ip_address,
    socket_client.port
)
    other_ip, other_port = _get_other_user_connection(username)
    socket_client.set_peer(other_ip, other_port)


def render_welcome_page() -> None:
    st.title("Secure End-to-End Encrypted Chat")
    st.write("Enter your details to connect securely.")

    if st.session_state["status_message"]:
        st.info(st.session_state["status_message"])
    if st.session_state["login_error"]:
        st.error(st.session_state["login_error"])

    username_input = st.text_input("Username", max_chars=20, autocomplete="off")
    password_input = st.text_input("Chat Password", type="password", max_chars=128)

    if st.button("Connect", type="primary"):
        connect_user(username_input, password_input)
        st.rerun()


def refresh_for_connection_polling(key: str) -> None:
    _debug(f"refresh_for_connection_polling() called with key={key!r}")
    st.caption("Use the Refresh messages button to load the latest messages from the database.")


def render_waiting_refresh_button() -> None:
    if st.button("Refresh status", key="waiting_refresh_button"):
        st.rerun()


def cleanup_current_session() -> None:
    try:
        username = st.session_state.get("username")
        session_id = st.session_state.get("session_id")
        connected = st.session_state.get("connected", False)
        if not username or not session_id or not connected:
            return

        manager = get_connection_manager()
        account_id = st.session_state.get("account_id")
        if account_id:
            database_helper.update_connection_info(account_id, None, None)
        _sync_chatlogs_to_db_safe()
        _get_socket_chat_client().stop()
        st.session_state["socket_client"] = None
        manager.disconnect_user(username, session_id)
        st.session_state["connected"] = False
        st.session_state["chat_open"] = False
    except Exception:
        return


def main() -> None:
    _debug("main() entered")
    st.set_page_config(page_title="Secure Chat", page_icon="\U0001F512", layout="wide")
    apply_blue_dark_theme()
    init_session_state()

    manager = get_connection_manager()
    if not st.session_state["manager_started"]:
        try:
            database_helper.cache_data()
            _debug("main() initial cache_data() succeeded")
        except Exception:
            _debug("main() initial cache_data() failed")
            traceback.print_exc()
            pass
        manager.start_monitor()
        atexit.register(cleanup_current_session)
        st.session_state["manager_started"] = True

    if st.session_state["connected"]:
        manager.heartbeat(
            st.session_state["username"],
            st.session_state["session_id"],
        )
        _debug(f"main() heartbeat sent for user={st.session_state['username']!r}")

    # Process events FIRST — a close_chat event sets connected=False so the
    # IP-count block below is skipped, landing directly on the welcome page
    # with no "waiting" flash in between.
    needs_rerun = process_events()
    _debug(f"main() process_events() returned needs_rerun={needs_rerun}")

    # Only run IP-count logic when still connected after event processing.
    if st.session_state["connected"]:
        try:
            database_helper.cache_data(include_chatlogs=False)
            all_ids = database_helper.get_all_account_ids()
            active_ip_count = sum(1 for aid in all_ids if database_helper.get_ip_address(aid))
            _debug(f"main() active_ip_count={active_ip_count}")
            if active_ip_count >= 2 and not st.session_state["chat_open"]:
                show_chat_screen()
                needs_rerun = True
                _debug("main() opened chat screen after detecting two active users")
        except Exception:
            _debug("main() failed while checking active IP count")
            traceback.print_exc()

    if needs_rerun:
        _debug("main() triggering rerun")
        st.rerun()

    if st.session_state["chat_open"]:
        render_chat_screen()
        return

    if st.session_state["connected"]:
        render_waiting_state()
        render_waiting_refresh_button()
        return

    render_welcome_page()


if __name__ == "__main__":
    main()