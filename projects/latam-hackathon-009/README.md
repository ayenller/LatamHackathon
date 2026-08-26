# latam-hackathon-009

> Team 009 — TiDB LATAM Hackathon 2026
> Replace this template with your own content. Keep the file name and directory name unchanged.

## Project Title

_One line describing what you built._

## Problem

_What problem does this solve, and for whom?_

## Solution

_How your project works. What makes it interesting._

## Architecture

```
_Diagram or description: EC2 → TiDB Serverless → LLM API, etc._
```

## Tech Stack

- **Database:** TiDB Cloud Starter (public endpoint, TLS)
- **Compute:** AWS EC2 (`latam-hackathon-009`, sa-east-1)
- **Storage:** `s3://tidb-latam-hackathon-2026-048364544505/latam-hackathon-009/`
- **Model:** _which LLM API you used_
- **Language / framework:** _..._

## Demo

_Screenshots or a link to a recorded demo. Do not embed credentials in images._

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure — copy the template and fill in your own values.
#    NEVER commit the resulting .env file.
cp .env.example .env

# 3. Run
python src/main.py
```

## Environment Variables

Document the variable **names** your project needs. Never the values.

| Variable | Description |
|---|---|
| `TIDB_HOST` | TiDB Cloud public endpoint |
| `TIDB_USER` | TiDB user |
| `TIDB_PASSWORD` | TiDB password — from your `.env` only |
| `LLM_API_KEY` | Model API key issued on site |

## Team

| Name | Role | GitHub |
|---|---|---|
| | | |
