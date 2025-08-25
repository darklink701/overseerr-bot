# token_store.py
import os, sqlite3, time, uuid, logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()  # load .env for CRYPTO_KEY
DB_PATH = "tokens.db"

key = os.getenv("CRYPTO_KEY")
if not key:
    raise RuntimeError("CRYPTO_KEY environmental variable is missing")
FERNET = Fernet(key)

# logging to stdout
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("token_store")

# Define and initialize the SQLite database
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token_id TEXT PRIMARY KEY,           -- random row id
            discord_user_id TEXT NOT NULL UNIQUE,-- one row per Discord user
            enc_plex_token BLOB,                 -- encrypted Plex token (may be NULL until linked)
            linked_at INTEGER,                   -- epoch seconds when linked
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """)
        # Lightweight migration: add enc_plex_token/linked_at if older table exists without them
        try:
            con.execute("ALTER TABLE tokens ADD COLUMN enc_plex_token BLOB")
        except sqlite3.OperationalError:
            pass
        try:
            con.execute("ALTER TABLE tokens ADD COLUMN linked_at INTEGER")
        except sqlite3.OperationalError:
            pass
        
        # Set WAL mode to allow concurrent reads/writes
        con.execute("PRAGMA journal_mode=WAL;")
        con.commit()
        
    # Publish the DB path for debugging   
    log.info("SQLite DB initialized at %s", DB_PATH)

def save_plex_token(discord_user_id: str, plex_token: str):
    """Create or update the row for this Discord user with an encrypted Plex token."""
    ts = int(time.time())
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        INSERT INTO tokens (token_id, discord_user_id, enc_plex_token, linked_at, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(discord_user_id) DO UPDATE SET
            enc_plex_token = excluded.enc_plex_token,
            linked_at      = excluded.linked_at,
            updated_at     = excluded.updated_at
        """, (
            uuid.uuid4().hex,
            discord_user_id,
            FERNET.encrypt(plex_token.encode()),
            ts, ts, ts
        ))
        con.commit()
    log.info("Plex token saved for Discord ID %s", discord_user_id)

# Retrieve and decrypt the Plex token for specified user
def get_plex_token(discord_user_id: str) -> str | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT enc_plex_token FROM tokens WHERE discord_user_id=? LIMIT 1",
            (discord_user_id,)
        ).fetchone()
    if not row or not row[0]:
        log.warning("No Plex token for Discord ID %s", discord_user_id)
        return None
    return FERNET.decrypt(row[0]).decode()

# Check if user has a Plex token on file
def is_linked(discord_user_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT 1 FROM tokens WHERE discord_user_id=? AND enc_plex_token IS NOT NULL LIMIT 1",
            (discord_user_id,)
        ).fetchone()
    return bool(row)

# Delete the Plex token for specified user
def delete_plex_token(discord_user_id: str):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE tokens SET enc_plex_token=NULL, linked_at=NULL, updated_at=? WHERE discord_user_id=?",
            (int(time.time()), discord_user_id)
        )
        con.commit()
    log.info("Plex token deleted for Discord ID %s", discord_user_id)
