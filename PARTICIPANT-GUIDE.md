# Participant Guide — TiDB LATAM Hackathon 2026

> Replace every `latam-hackathon-0XX` below with your own account name.

Event ends **2026-09-05**. All accounts and resources are deleted after that date.

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

**VS Code Remote SSH** over an SSM tunnel — add to `~/.ssh/config`:

```
Host hackathon
  HostName <your-instance-id>
  User ec2-user
  ProxyCommand sh -c "aws ssm start-session --target %h --document-name AWS-StartSSHSession --parameters portNumber=%p --region sa-east-1"
```

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

## 4. TiDB Cloud

Each participant registers their own **TiDB Cloud Starter** cluster and connects over the public endpoint with TLS.

Restrict the cluster's **IP Access List** to your EC2's public IP and your laptop's IP. Do not use `0.0.0.0/0`.

---

## 5. Network Limits

Your instance's security group has **no inbound rules** and allows outbound **HTTPS 443 only**.

- ✅ HTTPS to GitHub, pip/npm registries, model APIs, TiDB public endpoint
- ❌ Plain HTTP (port 80) times out. If `dnf` fails, switch to an HTTPS mirror or ask an organizer to open port 80.

---

## 6. What You Do Not Have

Launching or terminating EC2, modifying security groups or VPC, managing any IAM user or policy, granting yourself permissions, reading Secrets Manager, and touching another participant's EC2 or S3 folder.

Need something else? Ask an organizer. Do not attempt to work around the limits — CloudTrail logs everything.

---

## 7. API Key Discipline

- Keys are handed out **on site**, one per participant. Never share a key.
- Store keys in the `.env` file on your EC2 only.
- Never put a key in GitHub, a README, a screenshot, a Dockerfile, or a container image.
- All keys are revoked when the event ends.

This repository has **Secret Scanning and Push Protection enabled**. A push containing a key will be blocked.

---

## 8. Submitting Your Work

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

## 9. Cleanup — 2026-09-05

After the event, all of the following are permanently deleted: your AWS account, your EC2 instance and its disk, your S3 folder and its contents, TiDB clusters, and every API key.

**Push anything you want to keep to your GitHub fork before that date.**
