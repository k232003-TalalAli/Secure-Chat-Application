# SSD Secure Chat System

A secure two-user real-time messaging application built using Python, Streamlit, Firebase Firestore, and custom cryptographic implementations.
This project demonstrates the practical application of cryptography by implementing DES, RSA, and SHA-1 from scratch without relying on external cryptographic libraries.

---

## Features

- User Registration & Authentication
- Real-time Two-User Chat
- Custom DES Implementation
- Custom RSA Implementation
- Custom SHA-1 Implementation
- Firebase Firestore Integration
- TCP Socket Communication
- Connection State Management
- Cryptographic Audit Logging
- Session Monitoring & Heartbeats

---

## Security Architecture

| Layer | Purpose | Algorithm |
|---------|---------|------------|
| Authentication | Password Verification | SHA-1 |
| Key Storage | Protect RSA Keys | DES |
| Data Storage | Encrypt Chat Messages | DES |
| Message Transport | Encrypt Messages in Transit | RSA |

### Message Flow

```text
User Message
    ↓
RSA Encryption
    ↓
TCP Socket Transmission
    ↓
RSA Decryption
    ↓
Recipient
```

### Stored Data Protection

```text
Password
    ↓
SHA-1 Hash
    ↓
Firestore

RSA Keys
    ↓
DES Encryption
    ↓
Firestore

Chat Messages
    ↓
DES Encryption
    ↓
Firestore
```

---

## Technology Stack

| Component | Technology |
|------------|------------|
| Language | Python 3.10+ |
| Frontend | Streamlit |
| Database | Firebase Firestore |
| Networking | TCP Sockets |
| Cryptography | Custom DES, RSA, SHA-1 |
| Mathematics | SymPy |
| Backend SDK | firebase-admin |

---

## Project Structure

```text
SSD-Secure-Chat/
│
├── streamlit_app.py
├── connection_state_manager.py
├── database_helper.py
├── msg_security.py
│
├── des.py
├── des_key_gen.py
├── rsa.py
├── sha1.py
│
├── socket_chat_client.py
├── simulator.py
│
├── requirements.txt
├── serviceAccountKey.json
├── log.txt
│
└── README.md
```

### Module Overview

#### streamlit_app.py
Main user interface.

Responsible for:
- Login
- Registration
- Chat UI
- Session heartbeat

#### connection_state_manager.py
Manages:

- Active users
- Session lifecycle
- Event queues
- Heartbeat monitoring

#### database_helper.py
Handles:

- Firebase communication
- Local caching
- User management
- Chat storage

#### msg_security.py
High-level security API.

Provides:

- DES encryption/decryption
- RSA encryption/decryption
- SHA-1 hashing

#### des.py
Complete DES implementation including:

- Initial Permutation
- Feistel Network
- S-Boxes
- Final Permutation

#### rsa.py
RSA implementation including:

- Key generation
- Encryption
- Decryption

#### sha1.py
Pure Python SHA-1 implementation.

#### socket_chat_client.py
Handles:

- Incoming connections
- Outgoing messages
- TCP communication

#### simulator.py
Logs cryptographic operations into:

```text
log.txt
```

---

## Prerequisites

Before running the project, ensure you have:

- Python 3.10+
- Firebase Project
- Firestore Enabled
- Firebase Service Account Key

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd SSD-Secure-Chat
```

### 2. Create Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Firebase Configuration

### Step 1

Create a Firebase Project.

### Step 2

Enable:

- Firestore Database

### Step 3

Generate a Service Account Key:

```text
Firebase Console
→ Project Settings
→ Service Accounts
→ Generate New Private Key
```

### Step 4

Place the downloaded file in the project root:

```text
serviceAccountKey.json
```

Example:

```text
SSD-Secure-Chat/
│
├── serviceAccountKey.json
├── streamlit_app.py
└── ...
```

---

## Running the Application

Start Streamlit:

```bash
streamlit run streamlit_app.py
```

Streamlit will display a URL similar to:

```text
http://localhost:8501
```

Open it in your browser.

---

## Testing Two-User Communication

### User 1

Open:

```text
http://localhost:8501
```

Login with Account A.

### User 2

Open:

```text
Incognito Window
```

Navigate to:

```text
http://localhost:8501
```

Login with Account B.

### Verification Checklist

- Both users connect successfully
- Chat window appears
- Messages are delivered
- Messages decrypt correctly
- Connection manager updates state
- Simulator logs operations

---

## Audit Logs

Every cryptographic operation is logged.

Generated file:

```text
log.txt
```

Example entries:

```text
SHA1 Encrypt:
password123
→ cbfdac6008f9cab4083784cbd1874f76618d2a97

RSA Encrypt:
Hello
→ [1023, 921, 452]

DES Encrypt:
Secret Message
→ 8A3F9D...
```

---

## Academic Limitations

This project prioritizes educational value over production-grade security.

| Current Implementation | Production Alternative |
|------------------------|-----------------------|
| DES | AES-256-GCM |
| SHA-1 | Argon2 / bcrypt |
| Small RSA Keys | RSA-2048+ |
| ECB Mode | CBC / GCM |
| No Message Authentication | HMAC-SHA256 |

---

## Learning Outcomes

This project demonstrates:

- Symmetric Encryption (DES)
- Public Key Cryptography (RSA)
- Hash Functions (SHA-1)
- Secure Message Transmission
- Socket Programming
- Firebase Integration
- Concurrent Session Management
- Cryptographic System Design

---

## Authors

Developed as part of the SSD (Secure Software Design) academic project to demonstrate cryptographic algorithm implementation and secure communication concepts.
