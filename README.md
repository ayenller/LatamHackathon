# TiDB LATAM Hackathon 2026

Main repository for the TiDB LATAM Hackathon. Build something with **TiDB Cloud**, **AWS**, and an **LLM API**.

**Event ends 2026-09-05.** All AWS accounts, EC2 instances, S3 data, TiDB clusters, and API keys are deleted after that date.

---

## Start Here

👉 **[PARTICIPANT-GUIDE.md](PARTICIPANT-GUIDE.md)** — sign-in, MFA, EC2, S3, TiDB, network limits, and how to submit.

Read it before asking an organizer anything. Most "permission denied" messages are documented there and are intentional.

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
| Session Manager plugin | <https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html> |

---

## Getting Help

Ask an organizer on site. When reporting a problem, include: your account name, the region, what you ran, and the exact error text.
