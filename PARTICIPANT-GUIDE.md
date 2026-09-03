# Participant Guide — TiDB LATAM Hackathon 2026

> Replace every `latam-hackathon-0XX` below with your own account name.

All accounts and resources are deleted once the event ends.

---

## 1. Sign In

```
https://tidb-latam-hackathon.signin.aws.amazon.com/console
```

- **Username:** `latam-hackathon-0XX`
- You will be forced to change your password on first sign-in (minimum 14 characters, with uppercase, lowercase, number and symbol).
- Immediately after changing your password, **enroll an MFA device**: top-right user menu → *Security credentials* → *Assign MFA device*.
- Organizers will not hand out your model API key or TiDB credentials until MFA is enrolled.

Your region is fixed to **sa-east-1 (São Paulo)**. Switching to any other region shows nothing and every call is denied.

---

## 2. EC2

You can only operate the instance tagged `Participant = <your username>`.

| You can | You cannot |
|---|---|
| List instances | Launch or terminate instances |
| Start / stop / reboot **your own** instance | Touch anyone else's instance |
| Connect to your own instance via Session Manager | Modify security groups, VPC, routes, EIPs |

### Connecting

There is **no SSH port open** and no key pair. Use **Session Manager**.

**Console:** EC2 → select your instance → *Connect* → *Session Manager* → *Connect*

**Local terminal** (install the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) first):

```bash
aws ssm start-session --target <your-instance-id> --region sa-east-1
```

Both drop you in as **`ssm-user`**, not `ec2-user`, in `/usr/bin`. Switch before you do anything else:

```bash
sudo su - ec2-user
```

`/home/ec2-user` is mode `0700`, so as `ssm-user` a `cd` into it fails with **`Permission denied`** — not "no such directory", which sends people looking for the wrong problem. `ssm-user` has passwordless sudo, so the switch always works.

Everything below assumes you are `ec2-user`. Clone your repo and write your `.env` under `/home/ec2-user`, or the paths in this guide will not match what you see.

**VS Code Remote SSH** over an SSM tunnel — add to `~/.ssh/config`:

```
Host hackathon
  HostName <your-instance-id>
  User ec2-user
  ProxyCommand sh -c "aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region sa-east-1"
```

### Deploying

Code moves in through GitHub, not from your laptop — you have no AWS access keys, and that is deliberate.

```bash
# 1. Tools — neither git nor pip is preinstalled
sudo dnf install -y git python3-pip

# 2. The system Python is 3.9, which boto3 no longer supports. Install 3.11:
sudo dnf install -y python3.11 python3.11-pip

# 3. Your code
git clone https://github.com/<you>/<your-repo>.git
cd <your-repo>
python3.11 -m pip install -r requirements.txt

# 4. Your keys — on the instance only, never committed
cat > .env <<'ENV'
AWS_BEARER_TOKEN_BEDROCK=<your Bedrock key>
AWS_REGION=ap-southeast-1
TIDB_HOST=gateway01.<region>.prod.aws.tidbcloud.com
TIDB_PASSWORD=<your password>
ENV
chmod 600 .env

# 5. Run it so it survives the session closing
setsid nohup python3.11 src/main.py > app.log 2>&1 < /dev/null &
```

Use a heredoc for `.env` rather than pasting into `vi` — the browser shell mangles indentation.

Things that will bite you otherwise:

| | |
|---|---|
| **913 MB RAM**, no swap | `t3.micro`. pandas is fine; torch or large in-memory embeddings will be killed by the OOM reaper. Process in batches. |
| **Session closes → process dies** | Use `setsid nohup ... &` as above, or `tmux`. |
| **20-minute idle timeout** | The browser shell disconnects when idle. Your backgrounded process keeps running. |
| **`git push` fails from here** | Outbound SSH is closed. Push from your laptop, `git pull` here. |
| **Public IP changes on restart** | No Elastic IP. Re-check it in the console after every stop/start. |


---

## 3. S3

Everyone shares one bucket. Each participant owns one prefix:

```
s3://tidb-latam-hackathon-2026-048364544505/latam-hackathon-0XX/
```

**Always work inside your own folder.** Creating a folder or uploading a file at the bucket root is denied — this is intentional, not a bug.

### Console

Open the bucket and you will see every participant's folder name, but you can only open your own. Clicking into someone else's returns *Access Denied* — expected.

Direct link to your folder:

```
https://sa-east-1.console.aws.amazon.com/s3/buckets/tidb-latam-hackathon-2026-048364544505?region=sa-east-1&prefix=latam-hackathon-0XX/
```

### CLI

```bash
BUCKET=s3://tidb-latam-hackathon-2026-048364544505/latam-hackathon-0XX

# Upload
aws s3 cp ./model.pkl $BUCKET/ --region sa-east-1

# List your folder
aws s3 ls $BUCKET/ --region sa-east-1

# Download
aws s3 cp $BUCKET/model.pkl . --region sa-east-1
```

### Expected denials

| Action | Result |
|---|---|
| Create your own bucket | Denied — `s3:CreateBucket` is not granted |
| Create a folder at the bucket root | Denied |
| Read or write another participant's folder | Denied |
| `aws s3 ls s3://<bucket>/ --recursive` | Denied — recursive listing of the whole bucket |

Signing out and back in will **not** change any of this. Ask an organizer if you believe you need more.

---

## 4. Amazon Bedrock

Your key is issued for **ap-southeast-1 (Singapore)**, not São Paulo. It will not authenticate against any other region.

Put it in your config file — never in a commit, a screenshot or a Dockerfile:

```bash
# .env  —  keep it git-ignored
AWS_BEARER_TOKEN_BEDROCK=<the key handed to you on site>
AWS_REGION=ap-southeast-1
```

```python
bedrock = boto3.client("bedrock-runtime", region_name="ap-southeast-1")
```

`boto3` reads the bearer token straight from the environment, so you do not need AWS credentials on the machine for this. Requires `boto3 >= 1.39`.

Available on-demand models:

| Purpose | Model ID |
|---|---|
| Text | `anthropic.claude-3-5-sonnet-20240620-v1:0` |
| Text (faster) | `anthropic.claude-3-haiku-20240307-v1:0` |
| Embeddings | `cohere.embed-english-v3` · `cohere.embed-multilingual-v3` — 1024 dims |

`amazon.titan-embed-text-v2:0` and the Mistral models do **not** exist in ap-southeast-1. For embeddings, prefer TiDB's built-in Auto Embedding (§6) — it never touches Bedrock and needs no key.

You are free to use a different model or a different provider entirely. Explore.

---

## 5. The Dataset — `airportdb`

A curated airline database: airports, flights, bookings, passengers and weather, filtered to flights touching Brazil across one week in June 2015. Using it is optional, but it is there because it is **rich in real problems** — delays cascade, connections break, weather disrupts, passengers have histories.

### Download

```bash
curl -O https://hackaton-tidb.s3.sa-east-1.amazonaws.com/dumps/hackathon_airportdb.sql.gz
gunzip hackathon_airportdb.sql.gz
```

10 MB compressed, ~30 MB of SQL. No credentials needed — the link is public.

### Load it into your TiDB cluster

```bash
mysql -h <your-tidb-host> -P 4000 -u <your-user> -p \
      --ssl-ca=/etc/ssl/cert.pem \
      -e "CREATE DATABASE IF NOT EXISTS airportdb"

mysql -h <your-tidb-host> -P 4000 -u <your-user> -p \
      --ssl-ca=/etc/ssl/cert.pem airportdb < hackathon_airportdb.sql
```

TLS is required on the public endpoint — without `--ssl-ca` you get an SSL error.

If the venue wifi makes the import crawl, use **TiDB Cloud's import-from-S3** in the console instead. The cluster pulls the file server-side and never touches your connection.

### What is in it

| Table | Rows | What it holds |
|---|---:|---|
| `booking` | 617,062 | seat, price, passenger, flight |
| `airport` / `airport_geo` | 9,854 each | codes, names, city, country, lat/lon |
| `flightschedule` | 9,881 | the planned timetable, by weekday |
| `weatherdata` | 9,216 | temp, humidity, pressure, wind, condition |
| `flight` | 5,191 | actual departures and arrivals |
| `airplane` | 5,583 | capacity, type, airline |
| `passenger` / `passengerdetails` | 36,095 each | name, passport, birthdate, address, email |
| `employee` | 1,000 | staff records |
| `airline` | 113 | IATA code, name, base airport |
| `airplane_type` | 342 | aircraft identifiers |

Flights run **2015-06-02 to 2015-06-09**. 12 tables in total.

> The event brief mentions 8 tables and ~500K bookings. The dump actually carries **12 tables and 617,062 bookings** — the numbers above are counted from the file itself.

### Where the interesting questions are

Spend a few minutes querying before you write code. The strong projects come from a pattern someone noticed in the data, not from a feature list.

- `flight` versus `flightschedule` — where does reality diverge from the timetable, and for which routes?
- `weatherdata` joined to departure times — does weather actually explain the delays, or is something else going on?
- `booking` per passenger over the week — what does someone's history say about what they would accept as a rebooking?
- Connection windows: which itineraries break when the inbound leg slips an hour?

`passengerdetails` contains names, addresses and email addresses. It is synthetic data, but treat it as if it were not: do not paste it into a public repo, a screenshot or a prompt log.

---

## 6. TiDB Cloud

Each participant registers their own **TiDB Cloud Starter** cluster and connects over the public endpoint with TLS.

Restrict the cluster's **IP Access List** to your EC2's public IP and your laptop's IP. Do not use `0.0.0.0/0`.

### Auto Embedding — TiDB writes the vectors for you

Semantic search normally means writing four steps: call an embedding API from your code, store the vector, embed the incoming question too, then compare. **Auto Embedding deletes all four.** You declare a `VECTOR` column as generated from a text column, and TiDB calls the embedding model itself on every `INSERT` and `UPDATE`. At query time you hand it plain text and it embeds that for you.

No embedding code, no API key, no round trip to Singapore, and it does not spend your Bedrock quota.

> Auto Embedding runs **only on TiDB Cloud Starter hosted on AWS** — exactly the cluster you are registering for this event.

#### Choose a model

| Model string | Dims | Use it when |
|---|---:|---|
| `tidbcloud_free/cohere/embed-multilingual-v3` | 1024 | Your data or your users' questions are in **Portuguese or Spanish** — 100+ languages, and it matches *across* them |
| `tidbcloud_free/amazon/titan-embed-text-v2` | 1024 | English-only content |
| `tidbcloud_free/cohere/embed-english-v3` | 1024 | English-only; alternative to Titan |

These are hosted by TiDB Cloud: **no API key, no cost** (fair-use limits apply). Jina AI, OpenAI, Gemini, Hugging Face and NVIDIA NIM are available too, and you can bring your own key for models outside the free set.

This is a LatAm event — default to the multilingual model. With it, a question typed in Portuguese finds a note written in English.

#### A working example

```sql
CREATE TABLE route_notes (
  id       BIGINT AUTO_RANDOM PRIMARY KEY,
  note     TEXT,
  note_vec VECTOR(1024) GENERATED ALWAYS AS (
             EMBED_TEXT("tidbcloud_free/cohere/embed-multilingual-v3",
                        note,
                        '{"input_type": "search_document", "input_type@search": "search_query"}')
           ) STORED,
  VECTOR INDEX idx_note_vec ((VEC_COSINE_DISTANCE(note_vec)))
);

INSERT INTO route_notes (note) VALUES
  ('Thunderstorms over Guarulhos delayed every evening departure'),
  ('Voo direto para Frankfurt, sem escalas, saída pela manhã'),
  ('Conexión de 45 minutos en Lisboa, muy justa si el vuelo se retrasa');
```

You insert text only. The vector column fills itself.

```sql
SELECT id, note
FROM route_notes
ORDER BY VEC_EMBED_COSINE_DISTANCE(note_vec, 'tight connection risk')
LIMIT 3;
```

One asymmetry trips up everyone who skims the docs:

| Where | Which function |
|---|---|
| Defining the index | `VEC_COSINE_DISTANCE(col)` — or `VEC_L2_DISTANCE(col)` |
| Running the query | `VEC_EMBED_COSINE_DISTANCE(col, 'your text')` — only the `VEC_EMBED_` variants accept text |

`EMBED_TEXT()` belongs in the generated-column definition, not in your `ORDER BY`.

#### Putting `airportdb` behind it

Build one searchable sentence per row and let the generated column handle the rest:

```sql
INSERT INTO route_notes (note)
SELECT CONCAT_WS(' ', /* the columns worth searching */ ) FROM /* your table */;
```

Check the column names first — `DESCRIBE airport;`, `DESCRIBE flight;` — they are not what you would guess. Airport and city names, airline names and weather conditions all make good text. IDs and timestamps do not; keep those as ordinary columns and filter on them in `WHERE`.

#### Gotchas

| | |
|---|---|
| `VECTOR(n)` must match the model | 1024 for all three models above. A mismatch fails at **insert** time, not at `CREATE TABLE`. |
| `STORED`, never `VIRTUAL` | A virtual generated column cannot carry a vector index. |
| Embedding happens on write | Bulk-loading calls the model once per row. Insert in batches and expect it to be slower than a plain load. |
| Input limits | Titan caps at 8,192 tokens / 50,000 characters per row. Truncate long text yourself. |
| Free, not unlimited | Hosted models have usage limits. If you hit one, switch models or bring your own key. |

Full documentation: <https://docs.pingcap.com/ai/vector-search-auto-embedding-overview/>

---

## 7. Network Limits

### Inbound — your app is reachable

| Port | For |
|---|---|
| 8000–8999 | Your web app — Streamlit (8501), FastAPI/Django (8000), anything in the range |
| 3000 | React / Next.js dev server |

Open to the whole internet, so you can share a link with judges and teammates. Start your app bound to **`0.0.0.0`**, not `127.0.0.1`, or nothing outside the instance can reach it:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://<your-instance-public-ip>:8501` in a browser. Find the IP in the EC2 console under **Public IPv4 address**.

> ⚠️ **The public IP changes every time the instance stops and starts.** Re-check it after any restart.

> ⚠️ **Anything you serve here is public.** No auth, no TLS, and scanners find open ports within hours. Do not put credentials, personal data or anything you would not publish behind these ports.

**SSH (22) and RDP (3389) stay closed** and will not be opened. Use Session Manager.

### Outbound — three ports only

| Port | For |
|---|---|
| 443 | HTTPS — GitHub, pip/npm, Bedrock, TiDB Cloud |
| 80 | HTTP — package repositories |
| 4000 | TiDB Cloud public endpoint |

Everything else is blocked. One consequence worth knowing: **outbound SSH is closed**, so `git push` over `git@github.com:...` will not work from the instance. Develop and push from your laptop, and `git pull` on the instance.

---

## 8. What You Do Not Have

Launching or terminating EC2, modifying security groups or VPC, managing any IAM user or policy, granting yourself permissions, reading Secrets Manager, and touching another participant's EC2 or S3 folder.

Need something else? Ask an organizer. Do not attempt to work around the limits — CloudTrail logs everything.

---

## 9. API Key Discipline

- Keys are handed out **on site**, one per participant. Never share a key.
- Store keys in the `.env` file on your EC2 only.
- Never put a key in GitHub, a README, a screenshot, a Dockerfile, or a container image.
- All keys are revoked when the event ends.

This repository has **Secret Scanning and Push Protection enabled**. A push containing a key will be blocked.

---

## 10. Submitting Your Work

Two phases. **Build in your own repository during the sprint. Submit here at the end.**

### Phase 1 — during the sprint

Work in a **public** repository you own. Move fast, do not wait on reviews.

- Commit your `.kiro/` specs.
- Write a `SUBMISSION.md` at the root: what you built, how to run it, what is next.
- Push before the deadline and confirm the repo is actually public — Part B of the score is verified by AI reading it.

### Phase 2 — at the end

Copy your finished project into your team directory in the main repository and open a Pull Request. You do **not** have write access there, so fork it.

```bash
# 1. Fork https://github.com/ayenller/LatamHackathon, then clone your fork
git clone https://github.com/<your-username>/LatamHackathon.git
cd LatamHackathon
git checkout -b latam-hackathon-0XX

# 2. Copy your project in — leave out .git, .env and anything secret
rsync -a --exclude '.git' --exclude '.env' --exclude 'venv' \
      ~/your-project/ projects/latam-hackathon-0XX/

# 3. Push to your fork, then open a PR against main
git add projects/latam-hackathon-0XX/
git commit -m "latam-hackathon-0XX: <what you built>"
git push origin latam-hackathon-0XX
```

Your directory starts empty. Fill it with:

```
projects/latam-hackathon-0XX/
├── README.md        # description, architecture, screenshots, how to run
├── SUBMISSION.md    # same file as in your own repo
├── src/             # source code
├── .kiro/           # Kiro specs, if you used Kiro
└── docs/            # optional
```

Link back to your own public repo from the `README.md`.

**PRs that touch files outside your own directory will be rejected.** Never copy your project's `.git` directory in — submit the files, not the repository.

---

## 11. Cleanup

As soon as the event ends, all of the following are permanently deleted: your AWS account, your EC2 instance and its disk, your S3 folder and its contents, TiDB clusters, and every API key.

**Push anything you want to keep to your GitHub fork before you leave.**
