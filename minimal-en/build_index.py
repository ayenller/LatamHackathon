"""Step 3 — turn structured rows into a semantic index.

`embedding` is a STORED generated column driven by EMBED_TEXT(), so writing
text is all it takes: TiDB produces the vector. Run once.
"""
import time

from config import EMBED_DIM, EMBED_MODEL, get_connection

DDL = f"""
CREATE TABLE IF NOT EXISTS airport_semantic (
  airport_id  SMALLINT PRIMARY KEY,
  iata        CHAR(3),
  icao        CHAR(4),
  city        VARCHAR(50),
  country     VARCHAR(50),
  label       TEXT,
  embedding   VECTOR({EMBED_DIM}) GENERATED ALWAYS AS (
                EMBED_TEXT("{EMBED_MODEL}", label)
              ) STORED,
  KEY idx_city (city), KEY idx_iata (iata), KEY idx_icao (icao)
)
"""

# City first and repeated, then the airport name and both codes: one vector
# then matches "Guarulhos", "Sao Paulo", "GRU" and "SBGR" alike.
CHUNK = """
INSERT IGNORE INTO airport_semantic (airport_id, iata, icao, city, country, label)
SELECT a.airport_id, a.iata, a.icao, g.city, g.country,
       CONCAT_WS(' ', g.city, g.city, g.country, '-',
                 CONCAT_WS(', ', a.name, g.city, g.country,
                           CONCAT('IATA ', COALESCE(a.iata, 'n/a')),
                           CONCAT('ICAO ', a.icao)))
FROM airport a
JOIN airport_geo g ON g.airport_id = a.airport_id
WHERE a.airport_id > %s
  AND (a.airport_id IN (SELECT `from` FROM flight)
    OR a.airport_id IN (SELECT `to` FROM flight))
ORDER BY a.airport_id
LIMIT %s
"""


def load(conn, batch=200):
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(airport_id), 0), COUNT(*) FROM airport_semantic")
        cursor_id, done = cur.fetchone()
    size = batch
    while True:
        try:
            with conn.cursor() as cur:
                cur.execute(CHUNK, (cursor_id, size))
                if cur.rowcount <= 0:
                    break
                cur.execute("SELECT MAX(airport_id), COUNT(*) FROM airport_semantic")
                cursor_id, done = cur.fetchone()
            print(f"  {done} rows")
        except Exception as exc:
            # The free hosted model is rate limited; back off and shrink.
            if "failed to generate embedding" not in str(exc):
                raise
            size = max(size // 2, 25)
            print(f"  throttled, waiting 20s (batch -> {size})")
            time.sleep(20)
            conn.ping(reconnect=True)
    print(f"  done: {done} airports")


def add_fulltext(conn):
    """Full-text search needs a columnar replica before the index can exist."""
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE airport_semantic SET TIFLASH REPLICA 1")
        for _ in range(60):
            cur.execute("SELECT AVAILABLE FROM information_schema.tiflash_replica "
                        "WHERE TABLE_NAME = 'airport_semantic'")
            row = cur.fetchone()
            if row and row[0] == 1:
                break
            time.sleep(5)
        try:
            cur.execute("ALTER TABLE airport_semantic "
                        "ADD FULLTEXT INDEX ft_label (label) WITH PARSER MULTILINGUAL")
            print("  FULLTEXT index created")
        except Exception as exc:
            if "Duplicate" in str(exc) or "already exists" in str(exc):
                print("  FULLTEXT index already present")
            else:
                raise


if __name__ == "__main__":
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(f'SELECT EMBED_TEXT("{EMBED_MODEL}", "hello")')
        print(f"EMBED_TEXT ok ({str(cur.fetchone()[0]).count(',') + 1} dims)")
        cur.execute(DDL)
    print("loading the index ...")
    load(conn)
    print("enabling full-text search ...")
    add_fulltext(conn)
