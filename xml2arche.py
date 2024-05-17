#!/usr/bin/env python3
import glob
import os
import re
from rdflib import Graph, Namespace, URIRef, RDF, Literal, XSD
from acdh_tei_pyutils.tei import TeiReader
from PIL import Image
import requests
from io import BytesIO

fails = ("A63_51", "A64_34", "A64_37", "A64_38")

TOP_COL_URI = URIRef("https://id.acdh.oeaw.ac.at/ofmgraz")
MASTERS_URI = URIRef("https://id.acdh.oeaw.ac.at/ofmgraz/masters")
DERIVTV_URI = URIRef("https://id.acdh.oeaw.ac.at/ofmgraz/derivatives")
TEIDOCS_URI = URIRef("https://id.acdh.oeaw.ac.at/ofmgraz/xmltei")

ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}

##################################################################################################
#                                                                                                #
#                                          CONFIG                                                #
#                                                                                                #
##################################################################################################

RightsHolder = URIRef("https://id.acdh.oeaw.ac.at/oeaw")
Owner = URIRef("https://id.acdh.oeaw.ac.at/oeaw")
MetadataCreator = URIRef("https://orcid.org/0000-0002-8815-6741")
Owner = URIRef("https://id.acdh.oeaw.ac.at/oeaw")
Licensor = URIRef("https://orcid.org/0000-0002-0484-832X")
Depositor = URIRef("https://orcid.org/0000-0002-0484-832X")
Licence = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/cc-by-4-0")
Franziskanerkloster = URIRef("https://d-nb.info/gnd/16174362-6")


##################################################################################################
# I know an element present in the node wanted (e.g. tei:persName), but it can be in different
# types of nodes (e.g. tei:perStmt vs tei:person). So I get a list of those elements
# and put the parent element into a list if it isn't already there.
def get_parent_node(feat, file_path):
    nodes = []
    root = TeiReader(file_path)
    siblings = root.any_xpath(f".//{feat}")
    [nodes.append(sibling.getparent()) for sibling in siblings if sibling not in nodes]
    return nodes



def get_temporalcoverid(year):
    ids = {"13": URIRef("https://www.wikidata.org/wiki/Q7034"),
           "14": URIRef("https://www.wikidata.org/wiki/Q7018"),
           "15": URIRef("https://www.wikidata.org/wiki/Q7017"),
           "16": URIRef("https://www.wikidata.org/wiki/Q7016"),
           "17": URIRef("https://www.wikidata.org/wiki/Q7015")}
    return ids[year[0:2]]
    
# Takes a TEI element (respStmt or person) and returns a tuple of triples to add to the RDF
def make_person(person):
    output = []
    if (
        person.xpath(".//tei:persName/@ref", namespaces=nsmap)
        and person.xpath(".//tei:persName/@ref", namespaces=nsmap) == "placeholder"
    ):
        return output
    elif person.xpath(".//tei:persName/@ref", namespaces=nsmap):
        subject = URIRef(person.xpath(".//tei:persName/@ref", namespaces=nsmap)[0])
        output = [(subject, RDF.type, ACDH["Person"])]
    else:
        ids = person.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
        for i in ids:
            if output:
                output.append(
                    (subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()")[0]))
                )
            else:
                subject = URIRef(i.xpath("./text()")[0])
                output = [(subject, RDF.type, ACDH["Person"])]
    first_name = person.xpath(".//tei:persName/tei:forename/text()", namespaces=nsmap)[
        0
    ]
    last_name = person.xpath(".//tei:persName/tei:surname/text()", namespaces=nsmap)[0]
    return output + [(subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}"))]


# Takes a tei:place element and returns a tuple of triples to add to the RDF
def make_place(place):
    if place.xpath(".//tei:placeName[@xml:lang='de']", namespaces=nsmap):
        placename = place.xpath(
            ".//tei:placeName[@xml:lang='de']/text()", namespaces=nsmap
        )[0]
    else:
        placename = place.xpath(".//tei:placeName/text()", namespaces=nsmap)[0]
    i = place.xpath(".//tei:idno[@subtype='GND']", namespaces=nsmap)
    if i:
        subject = URIRef(i[0].xpath("./text()")[0])
        output = [(subject, RDF.type, ACDH["Place"])]
    ids = place.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
    for i in ids:
        if output and i.xpath("./@subtype")[0] != "GND":
            output.append(
                (subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()")[0]))
            )
        else:
            subject = URIRef(i.xpath("./text()")[0])
            output = [(subject, RDF.type, ACDH["Place"])]

    return output + [(subject, ACDH["hasTitle"], Literal(f"{placename}"))]


def get_persons(tei):
    list_file = glob.glob(tei)[0]
    persons = get_parent_node("tei:persName", list_file)
    return [x for person in persons for x in make_person(person)]


def get_places(tei):
    # Tries first to get the German name
    places = TeiReader(tei).any_xpath(".//tei:place[@xml:lang='de']")
    if not places:
        places = TeiReader(tei).any_xpath(".//tei:place")
    return [x for place in places for x in make_place(place)]


def search_editor(tei):
    if ref := tei.any_xpath(".//tei:publisher[@ref]"):
        editor = ref[0].xpath("./text()")[0]
    else:
        editor = False
    return editor


def get_date(tei):
    dates = tei.any_xpath(".//tei:bibl/tei:date")[0]
    if nb := dates.xpath("./@notBefore", namespaces=nsmap):
        na = dates.xpath("./@notAfter", namespaces=nsmap)[0]
        nb = nb[0]
    else:
        # If no date is available, we give a broad range
        nb = "1300-01-01"
        na = "1800-01-01"
    return (Literal(nb, datatype=XSD.date), Literal(na, datatype=XSD.date))


def get_contributors(tei):
    predobj = []
    contributors = tei.any_xpath(".//tei:respStmt")
    for contributor in contributors:
        pred = contributor.xpath(".//tei:persName/@role", namespaces=nsmap)[0].split(
            ":"
        )[-1]
        if obj := contributor.xpath(".//tei:persName/@ref", namespaces=nsmap):
            obj = URIRef(obj[0])
            pred = ACDH[pred]
        # The contributor has no PI
        else:
            forename = contributor.xpath(".//tei:forename/text()", namespaces=nsmap)[0]
            surname = contributor.xpath(".//tei:surname/text()", namespaces=nsmap)[0]
            obj = Literal(f"{forename} {surname}")
            pred = ACDH["hasNonLinkedIdentifier"]
        predobj.append((pred, obj))
    return predobj

def get_used_device(tei):
    device = tei.any_xpath(".//tei:notesStmt/tei:note/text()")
    if device:
        return Literal(re.match(r"Originals digitised with a (\w+) device", device[0]).group(1))
    else:
        return Literal("")

def get_extent(tei):
    measures = []
    description = tei.any_xpath(".//tei:supportDesc")[0]
    if height := description.xpath(".//tei:height", namespaces=nsmap):
        h = height[0].xpath("./text()", namespaces=nsmap)[0]
        w = description.xpath(".//tei:width/text()", namespaces=nsmap)[0]
        unit = description.xpath(".//tei:dimensions/@unit", namespaces=nsmap)[0]
        measures.append(f"{h}x{w} {unit}")
    if extent := description.xpath(".//tei:measure/@quantity", namespaces=nsmap):
        extent = extent[0]
        pagination = description.xpath(".//tei:measure/@unit", namespaces=nsmap)[0]
        if pagination == "leaf":
            pagination = "Folien"
        else:
            pagination = "Seiten"
        measures.append(f"{extent} {pagination}")
    return Literal("; ".join(measures))


def get_tifs(tei):
    tifs = []
    for tif in tei.any_xpath(".//tei:graphic/@url"):
        try:
            dims = get_dims(tif)
        except Exception:
            dims = False
        base = re.search("files/images/(.*)/full/full", tif).group(1)
        # prin("------------------------")
        if base not in tifs:
            tifs.append((base, dims))
    return tifs

def get_nextitem(first_item, doc):
    if next_item := doc.any_xpath("/@next"):
        if first_item == next_item[0]:
            next_item = False
        else:
            next_item = next_item[0]
    return next_item

def get_dims(file_path):
    response = requests.get(file_path)
    img = Image.open(BytesIO(response.content))
    return  img.width, img.height

def get_dims(file_path):
    return 0, 0

def get_coverage(doc):
    places = doc.any_xpath('.//tei:standOff/tei:listPlace/tei:place/tei:idno[@subtype="GND"]/text()')
    return [URIRef(place) for place in places]


g = Graph().parse("arche_seed_files/arche_constants.ttl")

[g.add(x) for x in get_persons("data/indices/listperson.xml")]

[g.add(x) for x in get_places("data/indices/listplace.xml")]

count = 0
files = glob.glob("data/editions/*.xml")


# MASTERS_URI
# DERIVTV_URI
# TEIDOCS_URI
for SUB_URI in (TEIDOCS_URI, MASTERS_URI, DERIVTV_URI):
        g.add((SUB_URI, RDF.type, ACDH["Collection"]))
        g.add((SUB_URI, ACDH["isPartOf"], TOP_COL_URI))
        g.add((SUB_URI, ACDH["hasRightsHolder"], RightsHolder))
        g.add((SUB_URI, ACDH["hasMetadataCreator"], MetadataCreator))
        g.add((SUB_URI, ACDH["hasLicensor"], Franziskanerkloster))
        g.add((SUB_URI, ACDH["hasOwner"], Franziskanerkloster))
        g.add((SUB_URI, ACDH["hasDepositor"], Franziskanerkloster))
g.add((MASTERS_URI, ACDH["hasTitle"], Literal("Master Scans")))
g.add((DERIVTV_URI, ACDH["hasTitle"], Literal("Derivatives")))
g.add((TEIDOCS_URI, ACDH["hasTitle"], Literal("TEI Documents")))


first_item = False
for xmlfilepath in files:
    xmlfile = os.path.basename(xmlfilepath)
    basename = xmlfile.split(".")[0]
    doc = TeiReader(xmlfilepath)
    dates = get_date(doc)
    extent = get_extent(doc)
    hasNextItem = get_nextitem(first_item, doc)
    if not first_item:
        first_item = get_nextitem(first_item, doc)
    subj = URIRef(os.path.join(TEIDOCS_URI, xmlfile))
    g.add((subj, RDF.type, ACDH["Resource"]))
    # Creates collection
    if has_title := doc.any_xpath(".//tei:title[@type='main']/text()"):
        has_title = has_title[0]
    else:
        has_title = basename
    g.add((subj, ACDH["hasAlternativeTitle"], Literal(has_title)))
    # creates resource for the XML
    g.add((subj, ACDH["isPartOf"], TEIDOCS_URI))
    if signature := doc.any_xpath(".//tei:idno[@type='shelfmark']"):
        g.add((subj, ACDH["hasTitle"], Literal(signature[0].text)))
        g.add((subj, ACDH["hasNonLinkedIdentifier"], Literal(signature[0].text)))
    g.add(
        (
            subj,
            ACDH["hasCategory"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"),
        )
    )
    g.add((subj, ACDH["hasFilename"], Literal(f"{basename}.xml")))
    g.add((subj, ACDH["hasFormat"], Literal("application/xml")))
    g.add(
        (
            subj,
            ACDH["hasLanguage"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat"),
        )
    )
    coverage = get_coverage(doc)
    [g.add((subj, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]
    contributors = get_contributors(doc)
    [g.add((subj, x[0], x[1])) for x in contributors]
    g.add((subj, ACDH["hasUsedDevice"], get_used_device(doc)))
    g.add((subj, ACDH["hasExtent"], extent))
    g.add((subj, ACDH["hasRightsHolder"], RightsHolder))
    g.add((subj, ACDH["hasOwner"], Owner))
    g.add((subj, ACDH["hasMetadataCreator"], MetadataCreator))
    g.add((subj, ACDH["hasDepositor"], Depositor))
    g.add((subj, ACDH["hasLicense"], Licence))
    g.add((subj, ACDH["hasLicensor"], Licensor))
    g.add((subj, ACDH["hasCoverageStartDate"], dates[0]))
    g.add((subj, ACDH["hasCoverageEndDate"], dates[1]))
    dateid = get_temporalcoverid(dates[0])
    g.add((subj, ACDH["hasTemporalCoverageIdentifier"], dateid))
    # Add TIFFs to collection
    for picture in get_tifs(doc):
        if not picture:
            continue
        tif = (MASTERS_URI, f"{picture[0]}.tif")
        jpg = (DERIVTV_URI, f"{picture[0]}.jpg")

        dims = picture[1]
        digitiser = [dig[1] for dig in contributors if dig[0] == ACDH["hasDigitisingAgent"]]
        g.add((URIRef(os.path.join(tif[0], tif[1])), ACDH['isSource'], URIRef(os.path.join(jpg[0], jpg[1]))))
        g.add((URIRef(os.path.join(jpg[0], jpg[1])), ACDH['isSource'], subj))
        [g.add((URIRef(os.path.join(tif[0], tif[1])), ACDH['hasDigitisingAgent'], dig)) for dig in digitiser]

        for path_file in (tif, jpg):
            resc = URIRef(os.path.join(path_file[0], path_file[1]))
            g.add((resc, RDF.type, ACDH["Resource"]))
            [g.add((resc, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]
            g.add((resc, ACDH["isPartOf"], path_file[0]))
            g.add((resc, ACDH["hasTitle"], Literal(picture)))
            g.add((resc, ACDH["isPartOf"], path_file[0]))
            g.add((resc, ACDH["hasFilename"], Literal(path_file[-1])))
            # The object in the following ones needs to be adapted to meet the actual features
            g.add((resc, ACDH["hasRightsHolder"], RightsHolder))
            g.add((resc, ACDH["hasOwner"], Owner))
            g.add((resc, ACDH["hasMetadataCreator"], MetadataCreator))
            g.add((resc, ACDH["hasDepositor"], Depositor))
            g.add((resc, ACDH["hasCategory"], URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/image")))
            g.add((resc, ACDH["hasLicense"], Licence))
            g.add((resc, ACDH["hasLicensor"], Licensor))
            if picture[1]:
                dims = picture[1]
                g.add((resc, ACDH["hasPixelHeight"], Literal(f"{dims[0]}")))
                g.add((resc, ACDH["hasPixelWidth"], Literal(f"{dims[1]}")))
try:
    g.serialize("ofmgraz.ttl")
except Exception as e:
    print(e)
