# TiDB LATAM Hackathon 2026

Main repository for the TiDB LATAM Hackathon. Build something with **TiDB Cloud**, **AWS**, and an **LLM API**.

**Event ends 2026-09-05.** All AWS accounts, EC2 instances, S3 data, TiDB clusters, and API keys are deleted after that date.

---

## Start Here

📄 **[Ask the Airport.pdf](Ask%20the%20Airport.pdf)** — the official event brief: format, scoring breakdown, suggested directions, and the 2h30 timeline.

👉 **[PARTICIPANT-GUIDE.md](PARTICIPANT-GUIDE.md)** — sign-in, MFA, EC2, S3, TiDB, network limits, and how to submit.

Read both before asking an organizer anything. Most "permission denied" messages are documented in the guide and are intentional.

---

## The Challenge

Build a generative AI application in one afternoon. **That is the whole brief** — we are not prescribing the problem.

| | |
|---|---|
| **Date** | Wed 02 Sep 2026, São Paulo |
| **Build sprint** | 2h30 |
| **Squad size** | 3–4 people |
| **Demo** | 2 minutes max |
| **Total points** | 100 |

Bring a perspective: an assistant, an analytics tool, a copilot, an agent, something we haven't thought of. Judging rewards **clever ideas and genuine business value** far more than it rewards checking boxes.

---

## The Dataset — `airportdb`

We have prepared a curated airline database. You do not have to use it, but it is there because it is **rich in interesting problems**: delays cascade, connections break, weather disrupts, passengers have preferences and histories.

Teams that find a real problem in this data and solve it well will score higher on creativity and business value than teams starting from a blank sheet.

| | |
|---|---|
| **Window** | 2015-06-02 to 2015-06-08 (one week) |
| **Scope** | All flights touching a Brazilian airport, plus a global sample for variety |
| **Size** | ~5,000 flights · ~500K bookings · weather included |
| **Tables** | `airline` `airplane` `airport` `booking` `flight` `flightschedule` `passenger` `weatherdata` and more |
| **Import time** | Small enough to load in minutes |

The dataset dump is handed out on site. If the venue wifi makes the import crawl, use **TiDB Cloud's import-from-S3** in the console instead — the cluster fetches it directly.

### Dig for the problem first

Before writing code, spend a few minutes **querying the data and looking for what is broken in it**. The interesting projects come from a real pattern someone noticed, not from a feature list.

Questions worth asking the data:

- Which connections break most often, and does weather explain it?
- Which routes are chronically late, and who is sitting on those planes?
- What does a passenger's booking history say about what they would accept as a rebooking?
- Where does the schedule promise something the aircraft rotation cannot deliver?

### Directions worth stealing

- **Natural-language analytics** — a question in, SQL generated, answer out.
- **Disruption copilot** — cross-reference flights and weather to predict which connections break, and explain why in plain language.
- **Travel agent with memory** — learn a passenger's preferences in one conversation, apply them in the next. Rebook them when their flight slips three hours.
- **Semantic concierge** — vector search over routes and notes for "find me something like this".
- **Something else entirely** — genuinely, the creativity points are real.

---

## Expected Stack

You are free to build however you like, but these are what the event provides and what the scoring rewards.

### Kiro — AI development tool

We expect teams to build with **[Kiro](https://kiro.dev)**. Commit your `.kiro/` specs to your repository — they are read during judging and are among the cheapest points on the board.

**Suggested way to work:** put **one laptop on the screen and let the AI drive the development and deployment**, while the whole team watches, argues, and steers. Two and a half hours is not enough time for four people to write code in parallel and merge it. It *is* enough time for four people to out-think a problem together while one machine does the typing.

Assign roles instead of splitting the codebase: **data · AI · interface · pitch**.

### AWS EC2

One instance per team, in **sa-east-1 (São Paulo)**, tagged with your team name. Connect via Session Manager — see the [participant guide](PARTICIPANT-GUIDE.md).

Deploying there is worth points, but do not let it eat your submission window. Running locally and recording the demo beats missing the deadline.

### Amazon Bedrock

**Available in sa-east-1** — Amazon Nova is **not** available in São Paulo:

| Purpose | Model ID |
|---|---|
| Text | `anthropic.claude-3-haiku-20240307-v1:0` |
| Text (alternative) | `mistral.mixtral-8x7b-instruct-v0:1` |
| Embeddings | `amazon.titan-embed-text-v2:0` — 1024 dimensions |

```python
import json, boto3

bedrock = boto3.client("bedrock-runtime", region_name="sa-east-1")

def ask(prompt: str) -> str:
    resp = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=json.dumps({...}),
    )
    return json.loads(resp["body"].read())["content"][0]["text"]
```

### TiDB vector search — the short way

TiDB can generate the embeddings for you, so you never call an embedding API from your own code:

```sql
CREATE TABLE flight_notes (
  id BIGINT AUTO_RANDOM PRIMARY KEY,
  flight_id INT,
  note TEXT,
  embedding VECTOR(1024) GENERATED ALWAYS AS (
    EMBED_TEXT("tidbcloud_free/amazon/titan-embed-text-v2", note)
  ) STORED
);

SELECT flight_id, note FROM flight_notes
ORDER BY VEC_COSINE_DISTANCE(
  embedding,
  EMBED_TEXT("tidbcloud_free/amazon/titan-embed-text-v2", 'nonstop to Germany')
) LIMIT 5;
```

Insert text, get vectors.

---

## What We Provide, On Site

Nothing below is handed out in advance. Collect it from an organizer at the venue.

| Item | Per | Notes |
|---|---|---|
| **AWS account** | one per group | IAM user `latam-hackathon-0XX`. Temporary password, changed on first sign-in, **MFA required**. |
| **Bedrock API key** | one per group | Issued after MFA is confirmed. One key per group — never shared between groups. |
| **EC2 instance** | one per group | sa-east-1, pre-tagged to your group. |
| **S3 folder** | one per group | `s3://tidb-latam-hackathon-2026-048364544505/latam-hackathon-0XX/` |
| **airportdb dataset** | one per group | Import into your own TiDB Cloud Starter cluster. |

You register your own **TiDB Cloud Starter** cluster — it is free and takes about a minute.

**Key discipline:** keys live in the `.env` file on your machine or EC2, and nowhere else. Never in a commit, a README, a screenshot, or a Dockerfile. All keys are revoked when the event ends.

---

## Repository Layout

```
projects/
├── latam-hackathon-001/
│   ├── README.md        # project description — required
│   ├── .env.example     # variable names only, never values
│   ├── src/             # your source code
│   └── docs/            # optional
├── latam-hackathon-002/
├── ...
└── latam-hackathon-010/
```

One directory per team. **Your directory name matches your AWS username, your EC2 `Participant` tag, and your S3 prefix** — all use the same hyphenated form. Do not rename it.

---

## How to Submit

You do **not** have write access here. Fork → branch → PR.

```bash
git clone https://github.com/<your-username>/LatamHackathon.git
cd LatamHackathon
git checkout -b latam-hackathon-0XX
# work only inside projects/latam-hackathon-0XX/
git add projects/latam-hackathon-0XX/
git commit -m "latam-hackathon-0XX: <what you built>"
git push origin latam-hackathon-0XX
```

Then open a Pull Request against `main`.

### PR Rules

| Rule | Why |
|---|---|
| Touch only your own `projects/latam-hackathon-0XX/` directory | GitHub write access cannot be scoped per-directory, so this is enforced by review |
| `README.md` in your directory must be filled in | It is how judges understand your project |
| No secrets in any file, screenshot, or commit | Push Protection will block the push |
| Keep the directory name unchanged | Permission policies match on it |

PRs that modify another team's files, repository configuration, or CI will be closed.

---

## Rules

- `main` is protected. Only organizers can merge.
- Secret Scanning and Push Protection are enabled. Never commit an API key, TiDB password, AWS credential, or IP allowlist.
- Each participant gets one AWS account, one EC2 instance, one S3 prefix, and one model API key. Do not share credentials between teams.
- Enroll MFA on first sign-in. Organizers verify this before handing out API keys.

---

## Resources

| What | Where |
|---|---|
| AWS Console | `https://tidb-latam-hackathon.signin.aws.amazon.com/console` |
| AWS Region | `sa-east-1` (São Paulo) |
| Shared S3 bucket | `s3://tidb-latam-hackathon-2026-048364544505/<your-username>/` |
| TiDB Cloud | <https://tidbcloud.com> — register your own Starter cluster |
| TiDB docs | <https://docs.pingcap.com/tidbcloud/> |
| Kiro | <https://kiro.dev> |
| Bedrock in sa-east-1 | Claude 3 Haiku · Mixtral 8x7B · Titan Embeddings V2 |
| Event brief | [Ask the Airport.pdf](Ask%20the%20Airport.pdf) |
| Session Manager plugin | <https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html> |

---

## Getting Help

Ask an organizer on site. When reporting a problem, include: your account name, the region, what you ran, and the exact error text.
