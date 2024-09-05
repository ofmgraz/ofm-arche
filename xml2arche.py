#!/usr/bin/env python3

import os
import csv
import re
from rdflib import Graph, Namespace, URIRef, RDF, Literal, XSD
from acdh_tei_pyutils.tei import TeiReader
from PIL import Image
import requests
from io import BytesIO

# Namespaces
ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
ACDHI = Namespace("https://id.acdh.oeaw.ac.at/")
PERIODO = Namespace("http://n2t.net/ark:/99152/p0v#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}

# Constants
TOP_COL = ACDHI["ofmgraz"]
MASTERS = ACDHI["ofmgraz/masters"]
DERIVTV = ACDHI["ofmgraz/derivatives"]
TEIDOCS = ACDHI["ofmgraz/teidocs"]

rdfconstants = "arche_seed_files/arche_constants.ttl"
CSV_FILE = "handles.csv"

# Configuration Variables
Franziskanerkloster = ACDHI["franziskanerklostergraz"]
OeAW = ACDHI["oeaw"]
ACDHCH = ACDHI["acdh"]
Sanz = ACDHI["fsanzlazaro"]
Klugseder = ACDHI["rklugseder"]
ccbyna = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/cc-by-sa-4-0")
publicdomain = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/publicdomain-1-0")
cc0 = URIRef("https://vocabs.acdh.oeaw.ac.at/archelicenses/cc0-1-0")
categories = {
    "tei": URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"),
    "image": URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/image"),
}
language = URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat")

# Handle Mapping
handles = {}
with open(CSV_FILE) as f:
    reader = csv.DictReader(f, delimiter=",")
    for row in reader:
        handles[row["arche_id"].split("/")[-1]] = row["handle_id"]


def get_parent_node(feat, file_path):
    """
    Extracts the parent node of a specified feature in a TEI XML file.

    Args:
        feat (str): The TEI feature to find.
        file_path (str): The path to the TEI file.

    Returns:
        list: A list of parent nodes containing the feature.
    """
    nodes = []
    root = TeiReader(file_path)
    siblings = root.any_xpath(f".//{feat}")
    nodes = list(set([sibling.getparent() for sibling in siblings]))
    return nodes


def uriark(uri):
    """Returns a Literal URI with the specified datatype."""
    return Literal(uri, datatype=XSD.anyURI)


def get_temporalcoverid(year):
    """
    Maps a century to its corresponding temporal coverage URI.

    Args:
        year (str): The year string.

    Returns:
        Literal: The corresponding temporal coverage URI.
    """
    ids = {
        "13": uriark("http://n2t.net/ark:/99152/p09hq4n"),
        "14": uriark("http://n2t.net/ark:/99152/p09hq4n"),
        "15": uriark("http://n2t.net/ark:/99152/p09hq4nhvcb"),
        "16": uriark("http://n2t.net/ark:/99152/p09hq4nnx95"),
        "17": uriark("http://n2t.net/ark:/99152/p09hq4nfgdb"),
        "18": uriark("http://n2t.net/ark:/99152/p09hq4n58mr"),
    }
    return ids.get(year[0:2])


def make_person(person):
    """
    Extracts and creates RDF triples for a person element in a TEI file.

    Args:
        person (Element): The TEI element representing a person.

    Returns:
        list: A list of RDF triples related to the person.
    """
    output = []
    ref = person.xpath(".//tei:persName/@ref", namespaces=nsmap)
    if ref and ref[0] == "placeholder":
        return output
    elif ref:
        subject = URIRef(ref[0])
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
    return output + [
        (subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}", lang="und"))
    ]


def make_place(place):
    """
    Extracts and creates RDF triples for a place element in a TEI file.

    Args:
        place (Element): The TEI element representing a place.

    Returns:
        list: A list of RDF triples related to the place.
    """
    placename = place.xpath(".//tei:placeName[@xml:lang='de']/text()", namespaces=nsmap)
    placename = (
        placename[0]
        if placename
        else place.xpath(".//tei:placeName/text()", namespaces=nsmap)[0]
    )
    subject = None
    output = []
    geonames_id = place.xpath(
        ".//tei:idno[@subtype='GEONAMES']/text()", namespaces=nsmap
    )

    if geonames_id:
        subject = URIRef(geonames_id[0])
        output.append((subject, RDF.type, ACDH["Place"]))

    ids = place.xpath(".//tei:idno[@type='URL']/text()", namespaces=nsmap)
    for i in ids:
        if output and "GEONAMES" not in i:
            output.append((subject, ACDH["hasIdentifier"], URIRef(i)))
        else:
            subject = URIRef(i)
            output = [(subject, RDF.type, ACDH["Place"])]

    return output + [(subject, ACDH["hasTitle"], Literal(placename, lang="de"))]


def get_persons(graph):
    """
    Queries the graph for persons and returns a dictionary of identifiers to subjects.

    Args:
        graph (Graph): The RDF graph.

    Returns:
        dict: A dictionary of person identifiers mapped to RDF subjects.
    """
    persons = {}
    query = """
    PREFIX acdh: <https://vocabs.acdh.oeaw.ac.at/schema#>
    SELECT ?subject ?identifier
    WHERE {
        ?subject rdf:type acdh:Person .
        ?subject acdh:hasIdentifier ?identifier .
    }
    """
    for r in graph.query(query):
        persons[str(r["identifier"])] = r["subject"]
    return persons


def get_places(graph):
    """
    Queries the graph for places and returns a dictionary of identifiers to subjects.

    Args:
        graph (Graph): The RDF graph.

    Returns:
        dict: A dictionary of place identifiers mapped to RDF subjects.
    """
    places = {}
    query = """
    PREFIX acdh: <https://vocabs.acdh.oeaw.ac.at/schema#>
    SELECT ?subject ?identifier
    WHERE {
        ?subject rdf:type acdh:Place .
        ?subject acdh:hasIdentifier ?identifier .
    }
    """
    for r in graph.query(query):
        places[str(r["identifier"])] = r["subject"]
    return places


def search_editor(tei):
    """
    Searches for the editor in the TEI file.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        str or bool: The editor's name or False if not found.
    """
    editor_ref = tei.any_xpath(".//tei:publisher[@ref]")
    return editor_ref[0].xpath("./text()")[0] if editor_ref else False


def get_date(tei):
    """
    Extracts the date range from a TEI file.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        tuple: A tuple containing the notBefore and notAfter dates as Literals.
    """
    dates = tei.any_xpath(".//tei:bibl/tei:date")[0]
    not_before = dates.xpath("./@notBefore", namespaces=nsmap)
    not_after = (
        dates.xpath("./@notAfter", namespaces=nsmap)[0] if not_before else "1800-01-01"
    )
    not_before = not_before[0] if not_before else "1300-01-01"
    return (
        Literal(not_before, datatype=XSD.date),
        Literal(not_after, datatype=XSD.date),
    )


def get_contributors(tei):
    """
    Extracts contributors from a TEI file and returns them as predicate-object pairs.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        list: A list of tuples representing predicate-object pairs.
    """
    predobj = []
    contributors = tei.any_xpath(".//tei:respStmt")
    for contributor in contributors:
        role = contributor.xpath(".//tei:persName/@role", namespaces=nsmap)[0]
        obj = (
            contributor.xpath(".//tei:persName/@ref", namespaces=nsmap)[0]
            if role != "Transcriptor"
            else None
        )

        if obj:
            obj = persons.get(obj)
        else:
            obj = ACDHI[
                "".join(
                    x[0]
                    for x in contributor.xpath(
                        ".//tei:persName/tei:forename/text()", namespaces=nsmap
                    )[0].split("-")
                ).lower()
                + contributor.xpath(
                    ".//tei:persName/tei:surname/text()", namespaces=nsmap
                )[0].lower()
            ]
            role = "Contributor"

        predobj.append((ACDH[f"has{role}"], obj))
    return predobj


def get_used_device(tei):
    """
    Extracts the device used for digitization from a TEI file.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        Literal: A Literal representing the device used.
    """
    device_note = tei.any_xpath(".//tei:notesStmt/tei:note/text()")
    device = (
        re.match(r"Originals digitised with a (\w+) device", device_note[0]).group(1)
        if device_note
        else "Unknown"
    )
    return Literal(device)


def get_extent(tei):
    """
    Extracts the physical extent of the document from a TEI file.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        Literal: A Literal representing the extent of the document.
    """
    description = tei.any_xpath(".//tei:supportDesc")[0]
    measures = []

    height = description.xpath(".//tei:height/text()", namespaces=nsmap)
    width = description.xpath(".//tei:width/text()", namespaces=nsmap)
    unit = (
        description.xpath(".//tei:dimensions/@unit", namespaces=nsmap)[0]
        if height and width
        else None
    )
    if height and width:
        measures.append(f"{height[0]}x{width[0]} {unit}")

    extent = description.xpath(".//tei:measure/@quantity", namespaces=nsmap)
    pagination = (
        description.xpath(".//tei:measure/@unit", namespaces=nsmap)[0]
        if extent
        else None
    )
    if extent:
        pagination = "Folia" if pagination == "leaf" else "Seiten"
        measures.append(f"{extent[0]} {pagination}")

    return Literal("; ".join(measures), lang="de")


def get_tifs(tei):
    """
    Extracts TIFF image information from a TEI file.

    Args:
        tei (TeiReader): The TEI reader object.

    Returns:
        list: A list of tuples representing TIFF file names and dimensions.
    """
    tifs = []
    for tif in tei.any_xpath(".//tei:graphic/@url"):
        base = re.search("files/images/(.*)/full/full", tif).group(1)
        if base not in tifs:
            dims = get_dims(tif)
            tifs.append((base, dims))
    return tifs


def get_dims(file_path, for_real=False):
    """
    Function for retrieving image dimensions. It would take a lot of time if it has to test each single file, so we use
    a dummy function if possible.

    Args:
        file_path (str): The path to the image file.

    Returns:
        tuple: A tuple of width and height (both set to 0).
    """
    dims = (0, 0)
    if for_real:
        response = requests.get(file_path)
        img = Image.open(BytesIO(response.content))
        dims = (img.width, img.height)
    return dims


def get_coverage(doc):
    """
    Extracts coverage information from a TEI document.

    Args:
        doc (TeiReader): The TEI reader object.

    Returns:
        list: A list of URIs representing spatial coverage.
    """
    locations = doc.any_xpath(
        './/tei:standOff/tei:listPlace/tei:place/tei:placeName[@xml:lang="en"]/text()'
    )
    return [
        ACDHI[f"ofmgraz/{'-'.join(x.lower().replace('ö', 'oe').split())}"]
        for x in locations
    ]


def make_subcollection(
    name, parent, title, arrangement=False, subtitle=False, issource=False
):
    """
    Creates a subcollection in the RDF graph.

    Args:
        name (str): The name of the subcollection.
        parent (URIRef): The parent collection URI.
        title (str): The title of the subcollection.
        arrangement (str, optional): The arrangement of the subcollection. Defaults to False.
        subtitle (str, optional): The subtitle of the subcollection. Defaults to False.
        issource (URIRef, optional): The source of the subcollection. Defaults to False.

    Returns:
        URIRef: The URI of the created subcollection.
    """
    subject = URIRef(os.path.join(parent, name))
    g.add((subject, RDF.type, ACDH["Collection"]))
    g.add((subject, ACDH["isPartOf"], URIRef(parent)))
    g.add((subject, ACDH["hasTitle"], Literal(title, lang="de")))

    if arrangement:
        g.add((subject, ACDH["hasArrangement"], Literal(arrangement, lang="en")))
    if subtitle:
        g.add((subject, ACDH["hasAlternativeTitle"], Literal(subtitle, lang="la")))
    if issource:
        g.add((subject, ACDH["isSourceOf"], issource))

    return subject


def add_constants(subj, rights, owner, licensor, creator, licence=False):
    """
    Adds constant properties to a resource.

    Args:
        subj (URIRef): The subject URI of the resource.
        rights (list): List of rights holders.
        owner (list): List of owners.
        licensor (list): List of licensors.
        creator (list): List of creators.
        licence (URIRef, optional): The license URI. Defaults to False.
    """
    for r in rights:
        g.add((subj, ACDH["hasRightsHolder"], r))
    for o in owner:
        g.add((subj, ACDH["hasOwner"], o))
    for l in licensor:
        g.add((subj, ACDH["hasLicensor"], l))
    for crt in creator:
        g.add((subj, ACDH["hasCreator"], crt))

    g.add((subj, ACDH["hasMetadataCreator"], Sanz))
    g.add((subj, ACDH["hasDepositor"], Franziskanerkloster))

    if licence:
        g.add((subj, ACDH["hasLicense"], licence))


def add_temporal(resc, start, end):
    """
    Adds temporal coverage information to a resource.

    Args:
        resc (URIRef): The subject URI of the resource.
        start (Literal): The start date of the coverage.
        end (Literal): The end date of the coverage.
    """
    g.add((resc, ACDH["hasCoverageStartDate"], start))
    g.add((resc, ACDH["hasCoverageEndDate"], end))


def process_file_list(filelist):
    """
    Processes a list of files and organizes them into collections and subcollections.

    Args:
        filelist (str): Path to the file containing the list of files.

    Returns:
        dict: A dictionary representing the file structure.
    """
    tree = {"teidocs": [], "masters": {}, "derivatives": {}}
    with open(filelist) as f:
        lines = [line.strip() for line in f]

    for line in lines:
        parts = line.split("/")[1:]
        if len(parts) < 2:
            continue
        collection, subcollection, filename = parts[0], parts[1], parts[-1]

        if collection == "teidocs":
            tree["teidocs"].append(filename)
        else:
            if subcollection in tree[collection]:
                tree[collection][subcollection].append(filename)
            else:
                tree[collection][subcollection] = [filename]

    return tree


# Load RDF graph and persons/places dictionaries
g = Graph().parse(rdfconstants, format="turtle")
persons = get_persons(g)
places = get_places(g)

# Process file list
filelist = "list_files.txt"
files = process_file_list(filelist)

prevresc = ACDHI["ofmgraz"]
digitiser = {}
# Iterate through collections
for collection in files:
    col = files[collection]
    if collection == "teidocs":
        col.reverse()
        for idx, xmlfile in enumerate(col):
            print(xmlfile)
            resc = ACDHI[f"ofmgraz/teidocs/{xmlfile}"]
            g.add((resc, RDF.type, ACDH["Resource"]))

            basename = xmlfile.split(".")[0]
            doc = TeiReader(f"data/editions/{xmlfile}")
            [
                g.add((resc, ACDH["hasPid"], Literal(xmlpid)))
                for xmlpid in doc.any_xpath(
                    './/tei:publicationStmt/tei:idno[@type="handle"]/text()'
                )
            ]

            if idx > 0:
                g.add((resc, ACDH["hasNextItem"], prevresc))
            else:
                g.add((ACDHI["ofmgraz/teidocs"], ACDH["hasNextItem"], prevresc))
            prevresc = resc

            dates = get_date(doc)
            extent = get_extent(doc)
            add_constants(resc, [OeAW], [ACDHCH], [ACDHCH], [Sanz], ccbyna)
            g.add((resc, ACDH["isPartOf"], ACDHI["ofmgraz/teidocs"]))

            signature = doc.any_xpath(".//tei:idno[@type='shelfmark']")
            has_title = signature[0].text if signature else None
            if has_title:
                g.add(
                    (
                        resc,
                        ACDH["hasTitle"],
                        Literal(f"{has_title} (XML-TEI)", lang="und"),
                    )
                )
                g.add((resc, ACDH["hasNonLinkedIdentifier"], Literal(has_title)))

            has_subtitle = doc.any_xpath(".//tei:title[@type='main']/text()")
            if has_subtitle:
                has_subtitle = has_subtitle[0].strip('"')
                if has_subtitle != has_title:
                    g.add(
                        (
                            resc,
                            ACDH["hasAlternativeTitle"],
                            Literal(has_subtitle, lang="la"),
                        )
                    )

            g.add((resc, ACDH["hasCategory"], categories["tei"]))
            g.add((resc, ACDH["hasFilename"], Literal(f"{basename}.xml")))
            g.add((resc, ACDH["hasFormat"], Literal("application/xml")))
            g.add((resc, ACDH["hasLanguage"], language))

            coverage = get_coverage(doc)
            [g.add((resc, ACDH["hasSpatialCoverage"], scover)) for scover in coverage]

            contributors = get_contributors(doc)
            for contributor in contributors:
                if contributor[0] != ACDH["hasDigitisingAgent"]:
                    g.add((resc, contributor[0], contributor[1]))

            g.add((resc, ACDH["hasExtent"], extent))
            add_temporal(resc, dates[0], dates[1])
            g.add((resc, ACDH["hasUsedSoftware"], Literal("Transkribus")))

            subcollections = [
                make_subcollection(
                    basename, MASTERS, has_title, False, has_subtitle, resc
                )
            ]
            subcollections.append(
                make_subcollection(basename, DERIVTV, has_title, False, has_subtitle)
            )
            for sc in subcollections:
                for scover in coverage:
                    g.add((sc, ACDH["hasSpatialCoverage"], scover))
                add_temporal(sc, dates[0], dates[1])

            digitiser[basename] = (
                    [
                        dig[1]
                        for dig in contributors
                        if dig[0] == ACDH["hasDigitisingAgent"]
                    ],
                    get_used_device(doc),
                )
    else:
        for subcollection in col:
            subcol = col[subcollection]
            rescpath = f"ofmgraz/{collection}/{subcollection}"
            jpgpath = f"ofmgraz/derivatives/{subcollection}"
            tifpath = f"ofmgraz/masters/{subcollection}"
            teiresc = ACDHI[f"ofmgraz/teidocs/{subcollection}.xml"]

            g.add(
                (
                    ACDHI[rescpath],
                    ACDH["hasArrangement"],
                    Literal(
                        f"The collection contains {len(subcol)} image files.", lang="en"
                    ),
                )
            )
            g.add(
                (
                    ACDHI[rescpath],
                    ACDH["hasArrangement"],
                    Literal(
                        f"Die Sammlung enthaltet {len(subcol)} Bilddateien.", lang="de"
                    ),
                )
            )

            if collection == "masters":
                lic = publicdomain
            else:
                lic = cc0

            subcol.reverse()
            for idx, image in enumerate(subcol):
                basename = image.split(".")[0]
                filetype = image.split(".")[1].upper()
                jpgresc = ACDHI[f"{jpgpath}/{image}.jpg"]
                resc = ACDHI[f"{rescpath}/{image}"]

                g.add((resc, RDF.type, ACDH["Resource"]))
                g.add((resc, ACDH["isPartOf"], ACDHI[rescpath]))

                if image in handles:
                    g.add((resc, ACDH["hasPid"], Literal(handles[image])))

                g.add(
                    (
                        resc,
                        ACDH["hasTitle"],
                        Literal(f"{basename} ({filetype})", lang="und"),
                    )
                )
                g.add((resc, ACDH["hasFilename"], Literal(image)))
                if collection == "masters":
                    g.add((resc, ACDH["isSourceOf"], jpgresc))
                    for dig in digitiser[subcollection][0]:
                        g.add((resc, ACDH["hasDigitisingAgent"], dig))
                    g.add(
                        (resc, ACDH["hasUsedHardware"], digitiser[subcollection][1])
                    )
                else:
                    g.add((resc, ACDH["hasCreator"], Klugseder))
                    g.add(
                        (
                            resc,
                            ACDH["hasRightsInformation"],
                            Literal(
                                "Related rights: ÖAW und Franziskanerkloster Graz",
                                lang="en",
                            ),
                        )
                    )
                    g.add(
                        (
                            resc,
                            ACDH["hasRightsInformation"],
                            Literal(
                                "Verwandte Schutzrechte der bearbeiteteten Dateien: ÖAW und Franziskanerkloster Graz",
                                lang="de",
                            ),
                        )
                    )
                add_constants(
                    resc,
                    [Franziskanerkloster, OeAW],
                    [Franziskanerkloster],
                    [Franziskanerkloster],
                    [Klugseder],
                    lic,
                    )

                g.add(
                    (
                        resc,
                        ACDH["hasOaiSet"],
                        URIRef(
                            "https://vocabs.acdh.oeaw.ac.at/archeoaisets/kulturpool"
                        ),
                    )
                )
                g.add((resc, ACDH["hasCategory"], categories["image"]))

                if idx > 0:
                    g.add((resc, ACDH["hasNextItem"], prevresc))
                else:
                    g.add((ACDHI[rescpath], ACDH["hasNextItem"], prevresc))

                prevresc = resc

# Serialize the RDF graph to a Turtle file
try:
    g.serialize("ofmgraz.ttl", format="ttl")
except Exception as e:
    print(e)
