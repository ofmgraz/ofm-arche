# ofmgraz ofm-arche
It generates a Turtle file for ARCHE metadata ingestion and saves it as `ofgraz.ttl`.

## Generate metadata

### Option A: Locally
* create a virtual environment `python -m venv venv`
* update pip to latest version and install needed python packages `pip install -U pip && pip install -r requirements.txt`
* run ```./fetch_data.sh```
* run ```./xml2arche.py```
* 

### Option B: As a GitHub Action
* run Action [Generate TTL](https://github.com/ofmgraz/ofm-arche/actions/workflows/generate-ttl.yml)

## Ingest metadata

### Option A: Locally
* create a virtual environment `python -m venv venv`
* update pip to latest version and install needed python packages `pip install -U pip && pip install -r requirements.txt`
* run ```composer require "acdh-oeaw/arche-ingest:^1"```
* run ```vendor/bin/arche-import-metadata ofmgraz.ttl https://arche-dev.acdh-dev.oeaw.ac.at/api $ARCHE_LOGIN $ARCHE_PW --retriesOnConflict 25```

### Option B: As a GitHub Action
* run Action [Upload metadata](https://github.com/ofmgraz/ofm-arche/actions/workflows/upload-ttl.yml)


## Notes
* `list_files.txt` contains a list of files with path to include with `topCollection` as root
* `handles.csv` contains pairs ```arche id,handle id``` previously generated. The handles of the TEI files are not included in this list, as they provide already provide it.
