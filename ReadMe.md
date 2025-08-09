If any venv active
deactivate >> Use this command
pip install uv >> uv is the module for creating venv
uv venv .venv  >>> its create .venv folder with virtual enviorment
.venv\Scripts\Activate.ps1 >>> Its Activate virtual enviorment

#Basics
uv pip install fastapi uvicorn[standard] python-dotenv pydantic psycopg[binary] aioredis passlib[bcrypt]
#For export
uv pip freeze > requirements.txt

alembic init alembic
docker run --name breakbroker-db -e POSTGRES_DB=breakbroker -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -v pgdata:/var/lib/postgresql/data -p 5432:5432 -d postgres:14
$env:PYTHONPATH = "."
uvicorn app.main:app --reload
