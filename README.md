# Wikipedia Word-Frequency Dictionary API

A **FastAPI** service that crawls Wikipedia articles up to a given depth, builds a **word-frequency dictionary** using `scikit-learn`’s `CountVectorizer`, and serves the results through simple HTTP endpoints.  

This project was built as part of an assignment, but is structured cleanly for real-world use (async crawling, dependency injection, tests, and Docker support).

---

## Getting Started

### Requirements
- Python 3.9+
- `pip`
- Docker + Docker Compose (for containerized runs)

### Run Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

3. Visit the docs:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Run with Docker
Build and run using Compose (hot-reload enabled):

```bash
docker compose up --build
```

Server is available at [http://localhost:8000](http://localhost:8000).

---

## API Endpoints

### `GET /word-frequency`
Generate a word-frequency dictionary for a Wikipedia article up to the given depth.

**Parameters (query):**
- `article` *(string, required)* — title of the starting Wikipedia article  
- `depth` *(int, required)* — depth of traversal (0 = just this page)

**Response:**
```json
{
  "apple": {
    "count": 2,
    "percent": 40.0
  },
  "banana": {
    "count": 3,
    "percent": 60.0
  }
}
```

---

### `POST /keywords`
Generate a filtered word-frequency dictionary with ignore list and percentile cutoff.

**Request body:**
```json
{
  "article": "Earth",
  "depth": 1,
  "ignore_list": ["earth", "planet"],
  "percentile": 50
}
```

- `ignore_list` *(array[string])* — words to exclude  
- `percentile` *(int, 0–100)* — keep only words at or above this percentile of frequency

**Response:**
```json
{
  "orbit": {
    "count": 5,
    "percent": 55.6
  },
  "sun": {
    "count": 4,
    "percent": 44.4
  }
}
```


## Running Tests

Unit tests are written with `unittest` and cover:
- Core text utilities (`app/core/text.py`)
- API routes (`app/api/routes.py`)
- Wikipedia client (`app/wiki.py`, mocked)

Run them with:

```bash
python -m unittest discover tests -v
```

---

## Tech Notes

- **FastAPI** — web framework  
- **httpx (async)** — Wikipedia API calls  
- **scikit-learn / CountVectorizer** — word counting and preprocessing  
- **Pydantic v2** — request/response models  
- **unittest** — test framework  
- **Docker Compose** — dev-friendly containerization  