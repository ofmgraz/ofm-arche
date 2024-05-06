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

TOP_COL_URI = URIRef("https://id.acdh.oeaw.ac.at/ofm-graz")
MASTERS_URI = URIRef("https://id.acdh.oeaw.ac.at/masters")
DERIVTV_URI = URIRef("https://id.acdh.oeaw.ac.at/derivatives")
TEIDOCS_URI = URIRef("https://id.acdh.oeaw.ac.at/xmltei")

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
        print("TIF_s", tif)
        try:
            dims = get_dims(tif)
        except Exception:
            dims = False
        print(f"TIF:\t{tif}")
        base = re.search("files/images/(.*)/full/full", tif).group(1)
        print("BASE", base)
        print("------------------------")
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
    print("DIMS_d", file_path)
    response = requests.get(file_path)
    img = Image.open(BytesIO(response.content))
    return  img.width, img.height


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
        g.add((SUB_URI, ACDH["hasLicensor"], Licensor))
        g.add((SUB_URI, ACDH["hasOwner"], Owner))
        g.add((SUB_URI, ACDH["hasDepositor"], Depositor))
g.add((MASTERS_URI, ACDH["hasTitle"], Literal("Master Scans")))
g.add((DERIVTV_URI, ACDH["hasTitle"], Literal("Derivatives")))
g.add((TEIDOCS_URI, ACDH["hasTitle"], Literal("TEI Documents")))


first_item = False
for xmlfile in files:
    basename = os.path.basename(xmlfile).split(".")[0]
    doc = TeiReader(xmlfile)
    dates = get_date(doc)
    extent = get_extent(doc)
    hasNextItem = get_nextitem(first_item, doc)
    if not first_item:
        first_item = get_nextitem(first_item, doc)
    subj = URIRef(os.path.join(TEIDOCS_URI, xmlfile))
    g.add((subj, RDF.type, ACDH["Resource"]))
    # Creates collection
    # print(COL_URI)
    if has_title := doc.any_xpath(".//tei:title[@type='main']/text()"):
        has_title = has_title[0]
        g.add((subj, ACDH["hasTitle"], Literal(has_title)))
    else:
        g.add((subj, ACDH["hasTitle"], Literal(basename)))
        has_title = "No title provided"
    # creates resource for the XML
    g.add((subj, ACDH["isPartOf"], TEIDOCS_URI))
    print("SUB:", subj)
    if signature := doc.any_xpath(".//tei:idno[@type='shelfmark']"):
        g.add((subj, ACDH["hasNonLinkedIdentifier"], Literal(signature[0].text)))
    g.add(
        (
            subj,
            ACDH["hasCategory"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"),
        )
    )
    g.add((subj, ACDH["hasTitle"], Literal(has_title)))
    g.add((subj, ACDH["hasFilename"], Literal(f"{basename}.xml")))
    g.add((subj, ACDH["hasFormat"], Literal("application/xml")))
    g.add(
        (
            subj,
            ACDH["hasLanguage"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat"),
        )
    )
    [g.add((subj, x[0], x[1])) for x in get_contributors(doc)]
    g.add((subj, ACDH["hasExtent"], extent))
    g.add((subj, ACDH["hasRightsHolder"], RightsHolder))
    g.add((subj, ACDH["hasOwner"], Owner))
    g.add((subj, ACDH["hasMetadataCreator"], MetadataCreator))
    g.add((subj, ACDH["hasDepositor"], Depositor))
    g.add((subj, ACDH["hasCategory"], Literal("Text")))  # not sure
    g.add((subj, ACDH["hasLicense"], Licence))
    g.add((subj, ACDH["hasLicensor"], Licensor))
    # Add TIFFs to collection
    for picture in get_tifs(doc):
        if not picture:
            continue
        print("PICTURE", picture)
        tif = (MASTERS_URI, f"{picture[0]}.tif")
        jpg = (DERIVTV_URI, f"{picture[0]}.jpg")
        
        dims = picture[1]
        for path_file in (tif, jpg):
            resc = URIRef(os.path.join(path_file[0], path_file[1]))
            print("pic:", resc)
            g.add((resc, RDF.type, ACDH["Resource"]))
            g.add((resc, ACDH["isPartOf"], path_file[0]))
            g.add((resc, ACDH["hasTitle"], Literal(picture)))
            g.add((resc, ACDH["isSourceOf"], subj))
            g.add((resc, ACDH["hasFilename"], Literal(path_file[-1])))
            # The object in the following ones needs to be adapted to meet the actual features
            g.add((resc, ACDH["hasRightsHolder"], RightsHolder))
            g.add((resc, ACDH["hasOwner"], Owner))
            g.add((resc, ACDH["hasMetadataCreator"], MetadataCreator))
            g.add((resc, ACDH["hasDepositor"], Depositor))
            g.add((resc, ACDH["hasCategory"], Literal("Text")))  # not sure
            g.add((resc, ACDH["hasLicense"], Licence))
            g.add((resc, ACDH["hasLicensor"], Licensor))
            if picture[1]:
                dims = picture[1]
                g.add((resc, ACDH["hasExtent"], Literal(f"{dims[0]}x{dims[1]}px")))

try:
    g.serialize("ofmgraz.ttl")
except Exception as e:
    print(e)