"""Steps 3-4 — semantic + full-text retrieval, then a semantic answer.

    python app.py "Sunday from Codo to Rozas, arrive before 18:00"
"""
import json
import re
import sys
import unicodedata

import pymysql

from config import TODAY, ask_claude, get_connection

# ---------------------------------------------------------------- retrieval

# Short forms and non-Latin names that no exact match would ever catch.
# CJK entries are deliberate: the app accepts questions in any language.
ALIASES = {
    "RIO": "RIO DE JANEIRO", "SP": "SAO PAULO", "SAMPA": "SAO PAULO",
    "圣保罗": "SAO PAULO", "里约": "RIO DE JANEIRO", "里约热内卢": "RIO DE JANEIRO",
}


def _fold(text):
    """'São Paulo' -> 'SAO PAULO'. Stored city names are unaccented uppercase."""
    d = unicodedata.normalize("NFD", text)
    return "".join(c for c in d if not unicodedata.combining(c)).upper().strip()


def resolve_place(conn, text):
    """Free-text place name -> (airport_ids, label, how).

    Three layers. Codes and city names are exact-match problems and must not go
    to the embedding: 'GIG' is closer to 'QIG' than to 'Galeao' in vector space.
    The vector layer handles what only it can — descriptive or misspelled names.
    """
    if not text:
        return [], "", "none"
    folded = ALIASES.get(text.strip(), ALIASES.get(_fold(text), _fold(text)))

    with conn.cursor() as cur:
        if re.fullmatch(r"[A-Z]{3,4}", folded):                       # 1. code
            col = "iata" if len(folded) == 3 else "icao"
            cur.execute(f"SELECT city, country FROM airport_semantic WHERE {col}=%s", (folded,))
            row = cur.fetchone()
            if row:
                return _city(conn, *row) + ("code",)

        # 2. city. Names repeat across countries (there is a Carolina in Brazil
        # and one in South Africa), so prefer the one that actually flies.
        cur.execute("""SELECT s.city, s.country, COUNT(f.flight_id) AS n
                       FROM airport_semantic s
                       LEFT JOIN flight f ON f.`from` = s.airport_id
                                          OR f.`to`   = s.airport_id
                       WHERE s.city = %s
                       GROUP BY s.city, s.country
                       ORDER BY n DESC LIMIT 1""", (folded,))
        row = cur.fetchone()
        if row:
            return _city(conn, row[0], row[1]) + ("city",)

        cur.execute("""SELECT city, country FROM airport_semantic      -- 3. vector
                       ORDER BY VEC_EMBED_COSINE_DISTANCE(embedding, %s) LIMIT 1""", (text,))
        row = cur.fetchone()
    return (_city(conn, *row) + ("vector",)) if row else ([], "", "none")


def _city(conn, city, country):
    """A traveler who says 'Rio' will take any airport in Rio."""
    with conn.cursor() as cur:
        cur.execute("SELECT airport_id FROM airport_semantic WHERE city=%s AND country=%s",
                    (city, country))
        return [r[0] for r in cur.fetchall()], f"{city}, {country}"


def search_similar(conn, text, lexical=None, k=5):
    """Semantic search, optionally filtered by full-text match (hybrid)."""
    sql = """SELECT city, country, iata,
                    VEC_EMBED_COSINE_DISTANCE(embedding, %s) AS distance
             FROM airport_semantic {where}
             ORDER BY distance LIMIT %s"""
    args = [text]
    where = ""
    if lexical:
        where = "WHERE fts_match_word(%s, label)"
        args.append(lexical)
    args.append(k)
    with conn.cursor() as cur:
        cur.execute(sql.format(where=where), args)
        return cur.fetchall()


# ------------------------------------------------------------------- intent

PROMPT = """You convert a traveler's message into a JSON search filter.

Today is {today}. The flight database only covers 2015-06-02 to 2015-06-08.
Resolve every relative date ("Sunday", "tomorrow", "周日") into that range.
The message may be in any language. Write place names in the form used locally
at that place, not a translation: "圣保罗" is "Sao Paulo" (Brazil), never
"Saint Paul"; "里约" is "Rio de Janeiro". Keep airport codes as-is.

Return ONLY a JSON object with these keys, null when the user did not say:
  origin_text, destination_text  strings
  date                           "YYYY-MM-DD"
  earliest_departure             "HH:MM"   (departure must be at or after this)
  latest_arrival                 "HH:MM"   (arrival must be at or before this)

"18:00前到" and "arrive before 6pm" set latest_arrival, never earliest_departure.

Message: {message}"""


# The model sometimes invents a time constraint the traveler never gave.
# If the message contains no clock reference at all, there cannot be one.
_TIME_HINT = re.compile(
    r"\d|[点時时]|上午|下午|早上|晚上|中午|凌晨"
    r"|\b(am|pm|noon|midnight|morning|evening|afternoon)\b", re.I)


def extract_intent(message):
    raw = ask_claude(PROMPT.format(today=TODAY, message=message))
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        raise ValueError(f"no JSON in model output: {raw[:200]}")
    intent = json.loads(match.group(0))
    if not _TIME_HINT.search(message):
        intent["earliest_departure"] = intent["latest_arrival"] = None
    return intent


# -------------------------------------------------------------------- query

SQL = """
SELECT f.flightno, al.airlinename,
       dg.city AS from_city, ag.city AS to_city,
       f.departure, f.arrival,
       TIMESTAMPDIFF(MINUTE, f.departure, f.arrival) AS duration_min
FROM flight f
JOIN airport_geo dg ON dg.airport_id = f.`from`
JOIN airport_geo ag ON ag.airport_id = f.`to`
JOIN airline     al ON al.airline_id = f.airline_id
WHERE {where}
ORDER BY f.arrival
LIMIT 8
"""


def _flights(conn, intent, origin_ids, dest_ids):
    where, args = [], []
    if origin_ids:
        where.append("f.`from` IN (%s)" % ",".join(["%s"] * len(origin_ids)))
        args += origin_ids
    if dest_ids:
        where.append("f.`to` IN (%s)" % ",".join(["%s"] * len(dest_ids)))
        args += dest_ids
    if intent.get("date"):
        where.append("f.departure >= %s AND f.departure < DATE_ADD(%s, INTERVAL 1 DAY)")
        args += [intent["date"], intent["date"]]
    if intent.get("earliest_departure"):
        where.append("TIME(f.departure) >= %s")
        args.append(intent["earliest_departure"])
    if intent.get("latest_arrival") and intent.get("date"):
        where.append("f.arrival <= CONCAT(%s, ' ', %s)")
        args += [intent["date"], intent["latest_arrival"]]
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(SQL.format(where=" AND ".join(where) or "1=1"), args)
        return cur.fetchall()


def search(conn, intent):
    """Most fully-constrained queries return nothing on this dataset, so widen
    in visible steps and report which one answered."""
    origin_ids, origin, _ = resolve_place(conn, intent.get("origin_text"))
    dest_ids, dest, dest_how = resolve_place(conn, intent.get("destination_text"))
    ctx = {"origin": origin, "destination": dest, "resolved_via": dest_how}

    rows = _flights(conn, intent, origin_ids, dest_ids)
    if rows:
        return {**ctx, "note": "exact match", "rows": rows}

    relaxed = {**intent, "earliest_departure": None, "latest_arrival": None}
    rows = _flights(conn, relaxed, origin_ids, dest_ids)
    if rows:
        return {**ctx, "note": "same day, outside the requested time window", "rows": rows}

    rows = _flights(conn, {**relaxed, "date": None}, origin_ids, dest_ids)
    if rows:
        return {**ctx, "note": "no flight on that date; other days on the same route",
                "rows": rows}

    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("""SELECT ag.city, ag.country, COUNT(*) AS flights
                       FROM flight f JOIN airport_geo ag ON ag.airport_id = f.`to`
                       WHERE f.`from` IN (%s) GROUP BY ag.city, ag.country
                       ORDER BY flights DESC LIMIT 5"""
                    % ",".join(["%s"] * len(origin_ids or [0])), origin_ids or [0])
        reachable = cur.fetchall()
    return {**ctx, "note": "no such route in this dataset", "rows": [], "reachable": reachable}


# ------------------------------------------------------------------- answer

ANSWER = """You are a travel assistant. The traveler asked: "{message}"

What they asked for: {asked}
What the database returned ({note}):
{body}

Write at most 3 sentences. Reply in {language}.

Rules you must follow:
- Reply in {language} and nothing else. The place names in this data are
  Brazilian, Spanish and Portuguese; they must NOT change your reply language.
- Every flight number, city, date and time must come from the list above.
  Never invent a flight, a connection, or a number of legs.
- The dates above are already correct for what they asked. Do not claim a
  listed flight is on the wrong day.
- If the list is empty, say plainly that no such route exists in this data,
  then name the destinations that are reachable instead."""


# Language is signalled by function words, not by nouns. Asking the model to
# judge it fails: the plain-English "Sunday from Codo to Rozas" was labelled
# Portuguese because Codo and Rozas are Iberian place names. Counting stop
# words is deterministic and costs no extra call.
STOPWORDS = {
    "English":    {"from", "to", "on", "at", "by", "before", "after", "arrive",
                   "arriving", "depart", "leave", "need", "want", "the", "and", "with"},
    "Portuguese": {"de", "do", "da", "para", "em", "no", "na", "antes", "depois",
                   "chegar", "sair", "partir", "quero", "preciso", "voo", "que"},
    "Spanish":    {"del", "en", "antes", "despues", "después", "llegar", "salir",
                   "quiero", "necesito", "vuelo", "el", "la", "los", "hasta"},
}


def _language(message: str) -> str:
    """CJK decides directly; Latin script is scored on stop words, default English."""
    if any("\u4e00" <= c <= "\u9fff" for c in message):
        return "Chinese"
    words = set(re.findall(r"[a-zà-ÿ]+", message.lower()))
    scores = {lang: len(words & sw) for lang, sw in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "English"


def _asked(intent):
    import datetime
    parts = []
    if intent.get("date"):
        d = datetime.date.fromisoformat(intent["date"])
        parts.append(f"date {intent['date']} (a {d.strftime('%A')})")
    if intent.get("earliest_departure"):
        parts.append(f"depart at or after {intent['earliest_departure']}")
    if intent.get("latest_arrival"):
        parts.append(f"arrive at or before {intent['latest_arrival']}")
    return "; ".join(parts) or "no date or time constraint"


def answer(conn, message):
    intent = extract_intent(message)
    result = search(conn, intent)
    if result["rows"]:
        body = "\n".join(
            f"- {r['flightno']} ({r['airlinename']}): {r['from_city']} "
            f"{r['departure']:%b %d %H:%M} -> {r['to_city']} {r['arrival']:%b %d %H:%M}, "
            f"{r['duration_min']} min" for r in result["rows"])
    else:
        body = ("(no flights on this route at all)\nDestinations actually served "
                f"from {result['origin']} this week:\n" + "\n".join(
                    f"- {r['city']}, {r['country']} — {r['flights']} departures this week"
                    for r in result.get("reachable", [])))
    text = ask_claude(ANSWER.format(message=message, asked=_asked(intent),
                                    language=_language(message),
                                    note=result["note"], body=body))
    return intent, result, text


def _cli():
    import argparse
    parser = argparse.ArgumentParser(
        description="Ask the Airport — retrieval and answering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Acceptance commands:
  python app.py --resolve GRU                     R3  place resolution, shows the layer
  python app.py --search "Santos Dumont"          R1  semantic search
  python app.py --search "..." --fts INTL         R2  hybrid: lexical filter + semantic rank
  python app.py "Sunday from Codo to Rozas..."    R4  full chain (semantic answer)
""")
    parser.add_argument("message", nargs="*", help="a traveler's sentence (full chain)")
    parser.add_argument("--resolve", metavar="PLACE", help="place resolution only")
    parser.add_argument("--search", metavar="TEXT", help="retrieval only")
    parser.add_argument("--fts", metavar="WORD", help="with --search, add a lexical filter")
    parser.add_argument("-k", type=int, default=5, help="rows to return (default 5)")
    args = parser.parse_args()

    conn = get_connection()

    if args.resolve:
        ids, label, how = resolve_place(conn, args.resolve)
        print(f"input   : {args.resolve}")
        print(f"resolved: {label}")
        print(f"via     : {how}      (code=exact code / city=exact city / vector=semantic)")
        print(f"airports: {len(ids)}  {ids}")
        return

    if args.search:
        rows = search_similar(conn, args.search, lexical=args.fts, k=args.k)
        mode = (f"hybrid (fts_match_word({args.fts!r}) + vector ranking)"
                if args.fts else "pure semantic search")
        print(f"query: {args.search!r}")
        print(f"mode : {mode}\n")
        print(f"  {'CITY':<28}{'COUNTRY':<22}{'IATA':<7}{'DISTANCE'}")
        for city, country, iata, distance in rows:
            print(f"  {city:<28}{country:<22}{iata or '--':<7}{distance:.3f}")
        return

    message = " ".join(args.message) or "Sunday from Codo to Rozas, arrive before 18:00"
    intent, result, text = answer(conn, message)
    print(f"input   : {message}")
    print(f"intent  : {json.dumps(intent, ensure_ascii=False)}")
    print(f"resolved: {result['origin']} -> {result['destination']} "
          f"(via {result['resolved_via']})")
    print(f"search  : {result['note']}, {len(result['rows'])} row(s)\n")
    print(text)


if __name__ == "__main__":
    _cli()
