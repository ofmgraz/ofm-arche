import os
from acdh_baserow_pyutils import BaseRowClient

# Baserow config
BASEROW_DB_ID = os.environ.get("BASEROW_DB_ID")
BASEROW_URL = "https://baserow.acdh-dev.oeaw.ac.at/api/"
BASEROW_USER = os.environ.get("BASEROW_USER")
BASEROW_PW = os.environ.get("BASEROW_PW")
BASEROW_TOKEN = os.environ.get("BASEROW_TOKEN")
PROJECT_NAME = os.environ.get("arche-2-baserow")
# Arche schema url, namespaces and xpaths
SCHEMA_PATH = "https://raw.githubusercontent.com/acdh-oeaw/arche-schema/master/acdh-schema.owl"
VOCABS_PATH = "https://github.com/acdh-oeaw/vocabs-acdh-dumps/raw/main/vocabs-main/"
NAMESPACES = {
    "xmlns": "https://vocabs.acdh.oeaw.ac.at/acdh#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dct": "http://purl.org/dc/terms/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "acdh": "https://vocabs.acdh.oeaw.ac.at/schema#",
    "foaf": "http://xmlns.com/foaf/spec/#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#"
}
XPATHS = {
    "classes": "//owl:Class",
    "properties": "//owl:ObjectProperty|//owl:DatatypeProperty",
    "restriction_properties": "./owl:Restriction/owl:onProperty",
    "restriction_cardinality": "./owl:Restriction/owl:minCardinality|./owl:Restriction/owl:maxCardinality",
    "label": "./rdfs:label[@xml:lang='en']/text()",
    "comment": "./rdfs:comment[@xml:lang='en']/text()"
}
# denormalize mapping
MAPPING_PROJECT = {
    "Class": "Classes.json",
    "Predicate_uri": "Properties.json",
    "Object_uri_persons": "Persons.json",
    "Object_uri_places": "Places.json",
    "Object_uri_organizations": "Organizations.json",
    "Object_uri_vocabs": "Vocabs.json"
}
MAPPING_PERSONS = {
    "Predicate_uri": "Properties.json",
    "Object_uri_organizations": "Organizations.json"
}
MAPPING_ORGS = {
    "Predicate_uri": "Properties.json"
}
MAPPING_PLACES = {
    "Predicate_uri": "Properties.json"
}
LANG_SPECIAL_TOKEN = "na"

# Baserow client and jwt_token
br_client = BaseRowClient(BASEROW_USER, BASEROW_PW, BASEROW_TOKEN, br_base_url=BASEROW_URL)
jwt_token = br_client.get_jwt_token()
