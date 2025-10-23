# String Analyzer API — HNG Stage 1 (Backend Wizards)

A RESTful API service that analyzes strings and stores their computed properties.

This project was built as part of HNG Backend Stage 1, using Python 3.10 and Django 3.2.

Features

For each analyzed string, the API computes and stores:

| Property | Description |
|-----------|--------------|
| `length` | Number of characters in the string |
| `is_palindrome` | Boolean indicating if the string reads the same forwards and backwards (case-insensitive) |
| `unique_characters` | Count of distinct characters |
| `word_count` | Number of words separated by whitespace |
| `sha256_hash` | SHA-256 hash of the string for unique identification |
| `character_frequency_map` | Dictionary mapping each character to its occurrence count |

Tech Stack

- Backend: Django 3.2
- Language: Python 3.10
- Database: SQLite 3 (default)
- Server (Production): Gunicorn
- Deployment: Railway.app

Setup Instructions

1. Clone the repository
git clone https://github.com/odudu-usoro/hng_stage_1.git
cd hng_stage_1
2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate     # On Windows
# source venv/bin/activate  # On macOS/Linux
3. Install dependencies
pip install -r requirements.txt
4. Apply database migrations
python manage.py migrate
5. Run the development server
python manage.py runserver
Server will start at:

cpp
http://127.0.0.1:8000/
API Endpoints
1. Create / Analyze String
POST /strings/

Request Body

json
Copy code
{ "value": "madam" }
Responses

201 Created

json
Copy code
{
  "id": "765cc52b3dbc1bb8ec279ef9c8ec3d0f251c0c92a6ecdc1870be8f7dc7538b21",
  "value": "madam",
  "properties": {
    "length": 5,
    "is_palindrome": true,
    "unique_characters": 3,
    "word_count": 1,
    "sha256_hash": "765cc52b3dbc1bb8ec279ef9c8ec3d0f251c0c92a6ecdc1870be8f7dc7538b21",
    "character_frequency_map": { "m": 2, "a": 2, "d": 1 }
  },
  "created_at": "2025-10-23T00:05:41.899889+00:00"
}
409 Conflict — if string already exists

400 Bad Request — invalid body or missing "value"

422 Unprocessable Entity — invalid data type (non-string)

2. Get a Specific String
GET /strings/{string_value}/

Response (200 OK)

json
Copy code
{
  "id": "...",
  "value": "madam",
  "properties": { /* computed values */ },
  "created_at": "..."
}
3. Get All Strings
GET /strings/all/

Optional filters:
is_palindrome, min_length, max_length, word_count, contains_character

Example


GET /strings/all/?is_palindrome=true&min_length=3&contains_character=a
Response


{
  "data": [ /* array of matching strings */ ],
  "count": 5,
  "filters_applied": { "is_palindrome": true, "min_length": 3, "contains_character": "a" }
}
4. Natural-Language Filtering
GET /strings/filter-by-natural-language?query=all%20single%20word%20palindromic%20strings

Example Supported Queries

Natural Query	Interpreted Filters
all single word palindromic strings	word_count=1, is_palindrome=true
strings longer than 10 characters	min_length=11
strings containing the letter z	contains_character=z

Error Responses

400 Bad Request — Unable to parse query

422 Unprocessable Entity — Conflicting filters

5. Delete String
DELETE /strings/{string_value}/delete/

Response

204 No Content — successfully deleted

404 Not Found — string not in system

Example CURL Commands
Analyze new string
curl -X POST http://127.0.0.1:8000/strings/ \
     -H "Content-Type: application/json" \
     -d '{ "value": "madam" }'

Get all strings
curl http://127.0.0.1:8000/strings/all/

Get one string
curl http://127.0.0.1:8000/strings/madam/

Delete string
curl -X DELETE http://127.0.0.1:8000/strings/madam/delete/
Environment Variables
No external environment variables required for local setup.
For deployment (e.g., Railway):

Variable	Description
DJANGO_SETTINGS_MODULE	analyzer.settings
SECRET_KEY	Django secret key
DEBUG	False in production
ALLOWED_HOSTS	Railway app domain

Developer
Name: Odudu Usoro
Email: yakndarausoro1@gmail.com
Stack: Python / Django / RESTful API Design
Cohort: HNG Backend — Stage 1

Notes
409 Conflict responses are expected if a duplicate string is sent.

Default DB is SQLite3; can easily swap to PostgreSQL for production.

Codebase structured cleanly into strings/ Django app for modularity.

Local Testing Status
All endpoints tested successfully using curl:

✅ Create (201)

✅ Duplicate (409)

✅ Get One (200)

✅ List All (200)

✅ Delete (204)

Logs confirm correct behavior.

Deployment (Production)
When deploying (e.g., on Railway):

Push your repo to GitHub.

Create a new Railway project → “Deploy from GitHub”.

Set start command: 

web: gunicorn analyzer.wsgi
Add environment variables (SECRET_KEY, DEBUG, etc.).

Open your deployed base URL and verify with /strings/ requests.

Submission Checklist

 API endpoints implemented

 Proper JSON responses & error codes

 README documented

 Tested locally via curl

 Ready for deployment & submission