# Campus Customs — Homework 4

This folder is the root of the Homework 4 project. It contains a React + Vite + TypeScript storefront and a FastAPI backend with a PydanticAI shopping agent.

## Local data pack

The database and catalogue photos are required to run the shop, but must stay out of GitHub. After obtaining the provided data pack, place its files in this layout, preserving the image filenames referenced by the database:

```text
data/
├── campus_customs.db
└── products/                 # source product images
```

The application can also serve generated cutouts from `data/product_cutouts/` when present; the original images in `data/products/` are sufficient to run it. The entire `data/` directory and any local data-pack archive are ignored by Git.

## Configure Python and the model key

From this folder, create and activate the virtual environment, then install the backend dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` in this folder and add your own `PORTKEY_API_KEY` locally. The template contains placeholders only; never commit `.env` or paste a real key into a tracked file. The configured model defaults to `gpt-5.6-luna` and can be changed with `PORTKEY_MODEL` in your local `.env`.

## Run the backend

In a terminal from this folder, activate `.venv`, then run the command from `backend/`:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The API is at `http://127.0.0.1:8000`; its interactive documentation is at `http://127.0.0.1:8000/docs`. Keep this terminal open.

## Run the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. Keep both servers running while using the site. The frontend calls the API at `http://127.0.0.1:8000`.

## Verify the project

From the `hw4/` folder, run the offline backend tests:

```bash
.venv/bin/python -m unittest discover -s backend/tests -v
```

To check the frontend production build, run `npm run build` from `frontend/`.

## GitHub submission safety

The repository should have this folder's contents at its root (so graders see `AI_prompts.md`, `backend/`, `frontend/`, and `output/` directly). `.gitignore` excludes `.env`, virtual environments, the local `data/` pack (including `campus_customs.db` and product photos), Python caches, frontend dependencies, and frontend build output. It keeps `.env.example` available as a safe configuration template. The screenshots in `output/app_check_images/` are homework evidence and are intentionally included.

Before pushing publicly, verify that the secret and local data paths are ignored:

```bash
git check-ignore -v .env data/campus_customs.db data/products/example.jpg
```

Do not force-add ignored secret or data files. This project is submitted as a GitHub repository URL; do not upload a ZIP.

## Expected project layout

```text
hw4/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app — run with: uvicorn main:app --reload --port 8000
│   ├── agent.py
│   ├── models.py
│   ├── tools.py
│   ├── create_product_cutouts.py # optional local image utility
│   ├── prompts/
│   │   └── prompt.md
│   └── tests/                  # offline backend tests
│       ├── test_audit.py
│       └── test_search_colors.py
├── frontend/
├── output/
│   ├── harness.md
│   ├── design.md
│   ├── usability.md
│   ├── app_check.html
│   ├── app_check_images/
│   └── audit_trail.json
└── data/                       # local-only data pack; not committed
│   ├── campus_customs.md
│   └── products/
```
