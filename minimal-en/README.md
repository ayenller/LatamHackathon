# Ask the Airport — reference implementation

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # pymysql + both model providers
cp .env.example .env      # fill in your credentials
python build_index.py     # build the index, ~50s, run once
python verify.py          # level-by-level acceptance, R1-R3 automatic
python app.py "Sunday from Codo to Rozas, arrive before 18:00"
```

| File | Role |
| :-- | :-- |
| `config.py` | Reads .env, provides the connection and the model call (Bedrock or Gemini) |
| `build_index.py` | Stage 2 — table, index load, full-text index |
| `app.py` | Stage 3 retrieval + stage 4 answer |
| `verify.py` | Level acceptance script |
