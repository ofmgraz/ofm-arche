# ofmgraz ofm-arche
It generates a Turtle file for ARCHE metadata ingestion and saves it as `ofgraz.ttl`.

## Run workflow

### Option A: Locally
* create a virtual environment `python -m venv venv`
* update pip to latest version and install needed python packages `pip install -U pip && pip install -r requirements.txt`
* run ```./fetch_data.sh```
* run ```./xml2arche.py```
* 
### Option B: As a GitHub Action
* run Action [Generate TTL](https://github.com/ofmgraz/ofm-arche/actions/workflows/generate-ttl.yml)

## Notes
* `list_files.txt` contains a list of files with path to include with `topCollection` as root
* `handles.csv` contains pairs ```arche id,handle id``` previously generated. 
