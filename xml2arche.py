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

TOP_COL = "https://id.acdh.oeaw.ac.at/ofmgraz"
MASTERS = "https://id.acdh.oeaw.ac.at/ofmgraz/masters"
DERIVTV = "https://id.acdh.oeaw.ac.at/ofmgraz/derivatives"
TEIDOCS = "https://id.acdh.oeaw.ac.at/ofmgraz/teidocs"

TOP_COL_URI = URIRef(TOP_COL)
MASTERS_URI = URIRef(MASTERS)
DERIVTV_URI =-URIRef(DERIVTV)
TEIDOCS_URI = URIRef(TEIDOCS)


ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
PERIODO = Namespace("http://n2t.net/ark:/99152/p0v#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}


##################################################################################################
#                                                                                                #
#                                          CONFIG                                                #
#                                                                                                #
##################################################################################################

RightsHolder = URIRef("https://id.acdh.oeaw.ac.at/oeaw")
Owner = URIRef("https://d-nb.info/gnd/16174362-6")
MetadataCreator = URIRef("https://orcid.org/0000-0002-8815-6741")
Owner = URIRef("https://id.acdh.oeaw.ac.at/oeaw")
Licensor = URIRef("https://d-nb.info/gnd/16174362-6")
Depositor = URIRef("https://d-nb.info/gnd/16174362-6")
Licence = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/cc-by-nc-sa-4-0")
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


def uriark (uri):
    return  Literal(uri, datatype="http://www.w3.org/2001/XMLSchema#anyURI")

def get_temporalcoverid(year):
    ids = {"13": uriark("http://n2t.net/ark:/99152/p09hq4n"),
           "14": uriark("http://n2t.net/ark:/99152/p09hq4n"),
           "15": uriark("http://n2t.net/ark:/99152/p09hq4nhvcb"),
           "16": uriark("http://n2t.net/ark:/99152/p09hq4nnx95"),
           "17": uriark("http://n2t.net/ark:/99152/p09hq4nfgdb"),
           "18": uriark("http://n2t.net/ark:/99152/p09hq4n58mr")}
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
            pred = ACDH["hasDigitisingAgent"]
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
        if len(tif.split(".")[0]) > 0:
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
    if next_item := doc.any_xpath("//@next"):
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


def make_subcollection(name, parent, title, arrangement=False, subtitle=False):
    subject = URIRef(os.path.join(parent, name))
    g.add((subject, RDF.type, ACDH["Collection"]))
    g.add((subject, ACDH["isPartOf"], URIRef(parent)))
    g.add((subject, ACDH["hasRightsHolder"], RightsHolder))
    g.add((subject, ACDH["hasMetadataCreator"], MetadataCreator))
    g.add((subject, ACDH["hasLicensor"], Franziskanerkloster))
    g.add((subject, ACDH["hasOwner"], Franziskanerkloster))
    g.add((subject, ACDH["hasDepositor"], Franziskanerkloster))
    g.add((subject, ACDH["hasTitle"], Literal(title)))
    if arrangement:
        g.add((subject, ACDH["hasArrangement"], Literal(arrangement)))
    if subtitle:
        g.add((subject, ACDH["hasAlternativeTitle"], Literal(subtitle)))
    return subject

def add_constants(subj):
    g.add((subj, ACDH["hasRightsHolder"], RightsHolder))
    g.add((subj, ACDH["hasOwner"], Owner))
    g.add((subj, ACDH["hasMetadataCreator"], MetadataCreator))
    g.add((subj, ACDH["hasDepositor"], Depositor))
    g.add((subj, ACDH["hasLicense"], Licence))
    g.add((subj, ACDH["hasLicensor"], Licensor))

def add_temporal(resc, start, end):
    g.add((resc, ACDH["hasCoverageStartDate"], start))
    g.add((resc, ACDH["hasCoverageEndDate"], end))
    dateid = get_temporalcoverid(start)
    g.add((resc, ACDH["hasTemporalCoverageIdentifier"], dateid))

g = Graph().parse("arche_seed_files/arche_constants.ttl")

#[g.add(x) for x in get_persons("data/indices/listperson.xml")]

#[g.add(x) for x in get_places("data/indices/listplace.xml")]

count = 0
files = glob.glob("data/editions/*.xml")

xmlarrangement = "Each element represents a physical volume"

# for subcol in (["teidocs", "TEI Documents"], ["masters", "Master Scans"], ["derivatives", "Derivative pictures"]):
#    make_subcollection(subcol[0], TOP_COL, subcol[1], xmlarrangement)


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
    xmlresc = URIRef(os.path.join(TEIDOCS, xmlfile))
    g.add((xmlresc, RDF.type, ACDH["Resource"]))
    add_constants(xmlresc)
    # Creates collection

    # creates resource for the XML
    g.add((xmlresc, ACDH["isPartOf"], TEIDOCS_URI))
    if signature := doc.any_xpath(".//tei:idno[@type='shelfmark']"):
        has_title = signature[0].text
        g.add((xmlresc, ACDH["hasTitle"], Literal(signature[0].text)))
        g.add((xmlresc, ACDH["hasNonLinkedIdentifier"], Literal(signature[0].text)))
    if has_subtitle := doc.any_xpath(".//tei:title[@type='main']/text()"):
        has_subtitle = has_subtitle[0].strip('"')
        if has_subtitle != has_title:
            g.add((xmlresc, ACDH["hasAlternativeTitle"], Literal(has_subtitle)))
        else:
            subtitle = False

    g.add(
        (
            xmlresc,
            ACDH["hasCategory"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"),
        )
    )
    g.add((xmlresc, ACDH["hasFilename"], Literal(f"{basename}.xml")))
    g.add((xmlresc, ACDH["hasFormat"], Literal("application/xml")))
    g.add(
        (
            xmlresc,
            ACDH["hasLanguage"],
            URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat"),
        )
    )
    coverage = get_coverage(doc)
    [g.add((xmlresc, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]
    contributors = get_contributors(doc)
    [g.add((xmlresc, x[0], x[1])) for x in contributors]
    g.add((xmlresc, ACDH["hasExtent"], extent))
    add_temporal(xmlresc, dates[0], dates[1])
    g.add((xmlresc, ACDH["hasUsedSoftware"], Literal("Transkribus")))

    # Add TIFFs to collection
    picarrangement = "Each element is a page or a side of folio"
    ## Make subcollections for each book
    device = get_used_device(doc)
    digitiser = [dig[1] for dig in contributors if dig[0] == ACDH["hasDigitisingAgent"]]
    subcollections = [make_subcollection(basename, parent, has_title, picarrangement, has_subtitle) for parent in (MASTERS, DERIVTV)]
    for subcollection in subcollections:
        [g.add((subcollection, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]
        g.add((subcollection, ACDH['hasUsedHardware'], device))
        [g.add((subcollection, ACDH['hasDigitisingAgent'], dig)) for dig in digitiser]
        add_temporal(subcollection, dates[0], dates[1])


    for picture in get_tifs(doc):
        if not picture:
            continue
        tiffile = f"{picture[0]}.tif"
        jpgfile = f"{picture[0]}.jpg"
        tifresc = URIRef(os.path.join(MASTERS, tiffile))
        jpgresc = URIRef(os.path.join(DERIVTV, jpgfile))

        g.add((tifresc, ACDH['isSourceOf'], jpgresc))
        g.add((jpgresc, ACDH['isSourceOf'], xmlresc))
        dims = picture[1]

        tif = (tifresc, subcollections[0], tiffile)
        jpg = (jpgresc, subcollections[1], jpgfile)

        for picresc in (tif, jpg):
            resc = picresc[0]
            g.add((resc, RDF.type, ACDH["Resource"]))
            add_constants(resc)
            g.add((resc, ACDH["isPartOf"], URIRef(picresc[1])))
            g.add((resc, ACDH["hasTitle"], Literal(picture[0])))
            g.add((resc, ACDH["hasFilename"], Literal(picresc[2])))
            # The object in the following ones needs to be adapted to meet the actual features
            g.add((resc, ACDH["hasCategory"], URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/image")))
            if False: # picture[1]:
                dims = picture[1]
                g.add((resc, ACDH["hasPixelHeight"], Literal(f"{dims[0]}")))
                g.add((resc, ACDH["hasPixelWidth"], Literal(f"{dims[1]}")))
    for idx, picture in reversed(list(enumerate(get_tifs(doc)))):
        tiffile = f"{picture[0]}.tif"
        jpgfile = f"{picture[0]}.jpg"
        tifresc = URIRef(os.path.join(MASTERS, tiffile))
        jpgresc = URIRef(os.path.join(DERIVTV, jpgfile))
        # if idx < len(list(enumerate(get_tifs(doc)))) - 1:
        #    g.add((tifresc, ACDH['hasNextItem'], prevtifresc))
        #    g.add((jpgresc, ACDH['hasNextItem'], prevjpgresc))
        prevtiffile = f"{picture[0]}.tif"
        prevjpgfile = f"{picture[0]}.jpg"
        prevtifresc = URIRef(os.path.join(MASTERS, prevtiffile))
        prevjpgresc = URIRef(os.path.join(DERIVTV, prevjpgfile))


try:
    g.serialize("ofmgraz.ttl")
except Exception as e:
    print(e)
