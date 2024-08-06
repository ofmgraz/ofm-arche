#!/usr/bin/env python3
import glob
import os
import re
from rdflib import Graph, Namespace, URIRef, RDF, Literal, XSD
from acdh_tei_pyutils.tei import TeiReader, ET
# from PIL import Image
# import requests
# from io import BytesIO

fails = ("A63_51", "A64_34", "A64_37", "A64_38")
ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
ACDHI = Namespace("https://id.acdh.oeaw.ac.at/")
PERIODO = Namespace("http://n2t.net/ark:/99152/p0v#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}


TOP_COL = ACDHI["ofmgraz"]
MASTERS = ACDHI["ofmgraz/masters"]
DERIVTV = ACDHI["ofmgraz/derivatives"]
TEIDOCS = ACDHI["ofmgraz/teidocs"]

rdfconstants = "arche_seed_files/arche_constants.ttl"


##################################################################################################
#                                                                                                #
#                                          CONFIG                                                #
#                                                                                                #
##################################################################################################
Franziskanerkloster = ACDHI["franziskanerklostergraz"]
OeAW = ACDHI["oeaw"]
ACDHCH = ACDHI["acdh-ch"]
Sanz = ACDHI["fsanzlazaro"]
Klugseder = ACDHI["rklugseder"]
Andorfer = ACDHI["pandorfer"]
Schopper = ACDH["dschopper"]
Licence = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/cc-by-nc-sa-4-0")
categories = {"tei": URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"),
              "image": URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/image")}
language = URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat")

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


def uriark(uri):
    return Literal(uri, datatype="http://www.w3.org/2001/XMLSchema#anyURI")


def get_temporalcoverid(year):
    ids = {
        "13": uriark("http://n2t.net/ark:/99152/p09hq4n"),
        "14": uriark("http://n2t.net/ark:/99152/p09hq4n"),
        "15": uriark("http://n2t.net/ark:/99152/p09hq4nhvcb"),
        "16": uriark("http://n2t.net/ark:/99152/p09hq4nnx95"),
        "17": uriark("http://n2t.net/ark:/99152/p09hq4nfgdb"),
        "18": uriark("http://n2t.net/ark:/99152/p09hq4n58mr"),
    }
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
    return output + [(subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}", lang="und"))]


# Takes a tei:place element and returns a tuple of triples to add to the RDF
def make_place(place):
    if place.xpath(".//tei:placeName[@xml:lang='de']", namespaces=nsmap):
        placename = place.xpath(
            ".//tei:placeName[@xml:lang='de']/text()", namespaces=nsmap
        )[0]
    else:
        placename = place.xpath(".//tei:placeName/text()", namespaces=nsmap)[0]
    i = place.xpath(".//tei:idno[@subtype='GEONAMES']", namespaces=nsmap)
    if i:
        subject = URIRef(i[0].xpath("./text()")[0])
        output = [(subject, RDF.type, ACDH["Place"])]
    ids = place.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
    for i in ids:
        if output and i.xpath("./@subtype")[0] != "GEONAMES":
            output.append(
                (subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()")[0]))
            )
        else:
            subject = URIRef(i.xpath("./text()")[0])
            output = [(subject, RDF.type, ACDH["Place"])]

    return output + [(subject, ACDH["hasTitle"], Literal(f"{placename}", lang="de"))]


def get_persons(rdfconstants):
    persons = {}
    q = """
    PREFIX acdh: <https://vocabs.acdh.oeaw.ac.at/schema#>

    SELECT ?subject ?identifier
    WHERE {
        ?subject rdf:type acdh:Person .
        ?subject acdh:hasIdentifier ?identifier .
    }
    """
    for r in g.query(q):
        persons[
            str(r["identifier"])
        ] = r["subject"]
    return persons


def get_places(tei):
    places = {}
    q = """
    PREFIX acdh: <https://vocabs.acdh.oeaw.ac.at/schema#>

    SELECT ?subject ?identifier
    WHERE {
        ?subject rdf:type acdh:Place .
        ?subject acdh:hasIdentifier ?identifier .
    }
    """
    for r in g.query(q):
        places[
            str(r["identifier"])
        ] = r["subject"]
    return places
    # Tries first to get the German name


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
        preds = contributor.xpath(".//tei:persName/@role", namespaces=nsmap)[0].split(" ")
        if preds[0] != "Transcriptor":
            obj = persons[contributor.xpath(".//tei:persName/@ref", namespaces=nsmap)[0]]
        else:
            obj = "".join(x[0] for x in
                          contributor.xpath(".//tei:persName/tei:forename/text()", namespaces=nsmap)[0].split("-")) + contributor.xpath(".//tei:persName/tei:surname/text()", namespaces=nsmap)[0][0]
            obj = ACDHI[obj]
        for pred in preds:
            # pred = pred[5:]
            predobj.append((ACDH[pred], obj))
    return predobj


def get_used_device(tei):
    device = tei.any_xpath(".//tei:notesStmt/tei:note/text()")
    if device:
        return Literal(
            re.match(r"Originals digitised with a (\w+) device", device[0]).group(1)
        )
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
            pagination = "Folia"
        else:
            pagination = "Seiten"
        measures.append(f"{extent} {pagination}")
    return Literal("; ".join(measures), lang="de")


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


# It does not get ingested if dimensions are provided
# def get_dims(file_path):
#    response = requests.get(file_path)
#    img = Image.open(BytesIO(response.content))
#    return img.width, img.height


# To test, so it does not have to fetch the file and calculate them
def get_dims(file_path):
    return 0, 0


def get_coverage(doc):
    locations = doc.any_xpath(
        './/tei:standOff/tei:listPlace/tei:place/tei:idno[@subtype="GEONAMES"]/text()'
    )
    # return [places[place] for place in locations]
    return [URIRef(place) for place in locations]


# This creates subcollections. In this case, for each set of tiffs and of jpgs
def make_subcollection(name, parent, title, arrangement=False, subtitle=False):
    subject = URIRef(os.path.join(parent, name))
    g.add((subject, RDF.type, ACDH["Collection"]))
    g.add((subject, ACDH["isPartOf"], URIRef(parent)))
    g.add((subject, ACDH["hasTitle"], Literal(title, lang="de")))
    if arrangement:
        g.add((subject, ACDH["hasArrangement"], Literal(arrangement, lang="en")))
    if subtitle:
        g.add((subject, ACDH["hasAlternativeTitle"], Literal(subtitle, lang="la")))
    add_constants(subject)
    return subject


# Add constant properties to resource
def add_constants(subj, rights=OeAW, owner=Franziskanerkloster, depositor=Franziskanerkloster, licence=Licence, creator=[Klugseder]):
    g.add((subj, ACDH["hasRightsHolder"], rights))
    g.add((subj, ACDH["hasOwner"], owner))
    for crt in creator:
        g.add((subj, ACDH["Creator"], crt))
    g.add((subj, ACDH["hasMetadataCreator"], Sanz))
    g.add((subj, ACDH["hasDepositor"], depositor))
    g.add((subj, ACDH["hasLicense"], licence))
    g.add((subj, ACDH["hasLicensor"], owner))
    


def add_temporal(resc, start, end):
    g.add((resc, ACDH["hasCoverageStartDate"], start))
    g.add((resc, ACDH["hasCoverageEndDate"], end))
    dateid = get_temporalcoverid(start)
    g.add((resc, ACDH["hasTemporalCoverageIdentifier"], dateid))


# Load the predefined constants: TopCollection, Collections, Persons, Places, and Organisations
g = Graph().parse(rdfconstants, format("turtle"))

persons = get_persons(g)
places = get_places(g)

# [g.add(x) for x in get_persons("data/indices/listperson.xml")]

# [g.add(x) for x in get_places("data/indices/listplace.xml")]

count = 0
files = glob.glob("data/editions/*.xml")

xmlarrangement = "Each element represents a physical volume"

# for subcol in (["teidocs", "TEI Documents"], ["masters", "Master Scans"], ["derivatives", "Derivative pictures"]):
#    make_subcollection(subcol[0], TOP_COL, subcol[1], xmlarrangement)


first_item = False
# Loops over the xml files to get the names and the pictures referred in them
for xmlfilepath in files:
    xmlfile = os.path.basename(xmlfilepath)
    basename = xmlfile.split(".")[0]
    doc = TeiReader(xmlfilepath)
    dates = get_date(doc)
    extent = get_extent(doc)
    hasNextItem = get_nextitem(first_item, doc)
    if not first_item:
        first_item = get_nextitem(first_item, doc)
    xmlresc = ACDHI[f"ofmgraz/teidocs/{xmlfile}"]
    # creates resource for the XML file
    g.add((xmlresc, RDF.type, ACDH["Resource"]))
    add_constants(xmlresc, creator=[Sanz, Klugseder], owner=ACDHCH, rights=OeAW)
    # Looks for next XML file. They are here attributes of the top structure
    if hasNextItem:
        g.add(
            (xmlresc, ACDH["hasNextItem"], ACDHI[f"ofmgraz/teidocs/{hasNextItem}"])
        )
    g.add((xmlresc, ACDH["isPartOf"], ACDHI["ofmgraz/teidocs"]))
    if signature := doc.any_xpath(".//tei:idno[@type='shelfmark']"):
        has_title = signature[0].text
        g.add((xmlresc, ACDH["hasTitle"], Literal(signature[0].text, lang="und")))
        g.add((xmlresc, ACDH["hasNonLinkedIdentifier"], Literal(signature[0].text)))
    if has_subtitle := doc.any_xpath(".//tei:title[@type='main']/text()"):
        has_subtitle = has_subtitle[0].strip('"')
        if has_subtitle != has_title:
            g.add((xmlresc, ACDH["hasAlternativeTitle"], Literal(has_subtitle, lang="la")))
        else:
            subtitle = False

    g.add(
        (
            xmlresc,
            ACDH["hasCategory"],
            categories["tei"],
        )
    )
    g.add((xmlresc, ACDH["hasFilename"], Literal(f"{basename}.xml")))
    g.add((xmlresc, ACDH["hasFormat"], Literal("application/xml")))
    g.add(
        (
            xmlresc,
            ACDH["hasLanguage"],
            language,
        )
    )
    coverage = get_coverage(doc)
    [g.add((xmlresc, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]
    contributors = get_contributors(doc)
    [g.add((xmlresc, ACDH["hasContributor"], contributor)) for contributor in (Andorfer, Schopper)]
    g.add((xmlresc, ACDH["hasExtent"], extent))
    add_temporal(xmlresc, dates[0], dates[1])
    g.add((xmlresc, ACDH["hasUsedSoftware"], Literal("Transkribus")))

    picarrangement = "Each element is a page or a side of folio"

    device = get_used_device(doc)
    digitiser = [dig[1] for dig in contributors if dig[0] == ACDH["hasDigitisingAgent"]]

  
    # Creates a list of pictures in the file, excluding empty refs
    pictures = [picture for picture in get_tifs(doc) if picture[0]]

    # Make subcollections for each book
    subcollections = [
        make_subcollection(basename, parent, has_title, picarrangement, has_subtitle)
        for parent in (MASTERS, DERIVTV)
    ]
    for subcollection in subcollections:
        [
            g.add((subcollection, ACDH["hasSpatialCoverage"], scover))
            for scover in coverage
        ]
        add_temporal(subcollection, dates[0], dates[1])
        g.add((subcollection, ACDH["hasArrangement"], Literal(f"The colllection contains {len(pictures)} image files.", lang="en")))
        g.add((subcollection, ACDH["hasArrangement"], Literal(f"Die Sammlung enthaltet {len(pictures)} Bilddateien.", lang="de")))



    # Loops over the pics in inverted order so we know beforehand which picture is the next

    for idx, picture in enumerate(reversed(pictures)):
        tiffile = f"{picture[0]}.tif"
        jpgfile = f"{picture[0]}.jpg"
        tifresc = ACDHI[f"ofmgraz/masters/{basename}/{tiffile}"]
        jpgresc = ACDHI[f"ofmgraz/derivatives/{basename}/{jpgfile}"]

        g.add((jpgresc, ACDH["hasCreator"], Klugseder))
        [g.add((tifresc, ACDH["hasDigitisingAgent"], dig)) for dig in digitiser]
        g.add((tifresc, ACDH["isSourceOf"], jpgresc))
        dims = picture[1]
        tif = (tifresc, subcollections[0], tiffile)
        jpg = (jpgresc, subcollections[1], jpgfile)

        for picresc in (tif, jpg):
            filetype = tif[2][-3:].upper()
            resc = picresc[0]
            g.add((resc, RDF.type, ACDH["Resource"]))
            g.add((resc, ACDH["hasUsedHardware"], device))
            add_constants(resc)
            g.add((resc, ACDH["isPartOf"], URIRef(picresc[1])))
            g.add((resc, ACDH["hasTitle"], Literal(picture[0], lang="und")))
            g.add((resc, ACDH["hasFilename"], Literal(f"{picresc[2]} ({filetype}-Datei)")))
            # The object in the following ones needs to be adapted to meet the actual features
            g.add(
                (
                    resc,
                    ACDH["hasCategory"],
                    categories["image"],
                )
            )
            if False:  # picture[1]:
                dims = picture[1]
                g.add((resc, ACDH["hasPixelHeight"], Literal(f"{dims[0]}")))
                g.add((resc, ACDH["hasPixelWidth"], Literal(f"{dims[1]}")))
        # If we are not in the last picture....
        if idx > 0:
            g.add((tifresc, ACDH["hasNextItem"], prevtifresc))
            g.add((jpgresc, ACDH["hasNextItem"], prevjpgresc))
        prevtifresc = tifresc
        prevjpgresc = jpgresc

try:
    g.serialize("ofmgraz.ttl", format="ttl")
except Exception as e:
    print(e)