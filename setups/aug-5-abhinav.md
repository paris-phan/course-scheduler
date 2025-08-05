# overview

script migration to gcloud from current postgres structure
its a new schema with so many tables so good luck
most aren't populated/used until future functionality implementation

gcloud setup:

# Cloud SQL --> w/ PostgreSQL 17
# its like the lowest tier w/ shared 1 core 600 mb memory so don't query too big for rn otherwise let me know and i can increase i believe

# 1. setup gcloud cli

brew install --cask gcloud-cli

gcloud auth login
gcloud auth application-default login

gcloud auth set-quota-project course-scheduler-467723
gcloud auth application-default set-quota-project course-scheduler-467723


# 2. setup env

cd bakcned
python -m venv .venv
source .venv/bin/acvtiate

pip install -r requirements

### note: no more supabase package included not sure if your files wil break

copy backend/.env.example into .env and populate, sent my .env in imessage

^^^u get google auth credentials after gcloud auth login

# dev
using cloud-sql-python-connector[pg8000] really easy
https://pypi.org/project/cloud-sql-python-connector/


inside google cluod console 
under sql instance uva-courses-dev
-> cloud sql studio to see entries and tables and schema
