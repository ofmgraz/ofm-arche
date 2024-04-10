#!/usr/bin/env python3
import glob
import os
import re
from rdflib import Graph, Namespace, URIRef, RDF, Literal, XSD, BNode
from acdh_tei_pyutils.tei import TeiReader, ET

# %%
fails = ('A63_51', 'A64_34', 'A64_37', 'A64_38')

TOP_COL_URI = URIRef("https://id.acdh.oeaw.ac.at/ofm-graz")
ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}
ARCHE = Namespace("https://vocabs.acdh.oeaw.ac.at/acdh#")

##################################################################################################
#                                                                                                #
#                                          CONFIG                                                #
#                                                                                                #
##################################################################################################

RightsHolder = ACDH["ACDH"]
Owner = ACDH["ACDH"]
MetadataCreator = URIRef("https://orcid.org/0000-0002-8815-6741")
Owner = ACDH["ACDH"]
Licensor = URIRef("https://orcid.org/0000-0002-0484-832X")
Depositor = URIRef("https://orcid.org/0000-0002-0484-832X")
Licence = Literal("CC BY-NC-ND 4.0")
##################################################################################################
# %%
# I know an element present in the node wanted (e.g. tei:persName), but it can be in different
# types of nodes (e.g. tei:perStmt vs tei:person). So I get a list of those elements
# and put the parent element into a list if it isn't already there.
def get_parent_node(feat, file_path):
   nodes = []
   root = TeiReader(file_path)
   siblings = root.any_xpath(f".//{feat}")
   [nodes.append(sibling.getparent()) for sibling in siblings if sibling not in nodes]
   return nodes

# %%
# Takes a TEI element (respStmt or person) and returns a tuple of triples to add to the RDF
def make_person(person):
    output = []
    if person.xpath(".//tei:persName/@ref", namespaces=nsmap) and person.xpath(".//tei:persName/@ref", namespaces=nsmap) == "placeholder":
        return output
    elif person.xpath(".//tei:persName/@ref", namespaces=nsmap):
        subject = URIRef(person.xpath(".//tei:persName/@ref", namespaces=nsmap)[0])
        output = [(subject, RDF.type, ACDH["Person"])]
    else:
        ids = person.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
        for i in ids:
            if output:
                output.append((subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()")[0])))
            else:
                subject = URIRef(i.xpath("./text()")[0])
                output = [(subject, RDF.type, ACDH["Person"])]
    first_name = person.xpath(".//tei:persName/tei:forename/text()", namespaces=nsmap)[0]
    last_name = person.xpath(".//tei:persName/tei:surname/text()", namespaces=nsmap)[0]
    return output + [(subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}"))]

# %%
# Takes a tei:place element and returns a tuple of triples to add to the RDF
def make_place(place):
    if place.xpath(".//tei:placeName[@xml:lang='de']", namespaces=nsmap):
        placename = place.xpath(".//tei:placeName[@xml:lang='de']/text()", namespaces=nsmap)[0]
    else:
        placename = place.xpath(".//tei:placeName/text()", namespaces=nsmap)[0]
    i = place.xpath(".//tei:idno[@subtype='GND']", namespaces=nsmap)
    if i:
        subject = URIRef(i[0].xpath("./text()")[0])
        output = [(subject, RDF.type, ACDH["Place"])]
    ids = place.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
    for i in ids:
        if output and i.xpath("./@subtype")[0] != "GND":
            output.append((subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()")[0])))
        else:
            subject = URIRef(i.xpath("./text()")[0])
            output = [(subject, RDF.type, ACDH["Place"])]

    return output + [(subject, ACDH['hasTitle'], Literal(f"{placename}") )]

# %%
def get_persons(tei):
    list_file = glob.glob(tei)[0]
    persons = get_parent_node("tei:persName", list_file)
    return [x for person in persons for x in make_person(person)]

# %%
def get_places(tei):
    list_file = glob.glob(tei)[0]
    # Tries first to get the German name
    places = TeiReader(tei).any_xpath(".//tei:place[@xml:lang='de']")
    if not places:
        places = TeiReader(tei).any_xpath(".//tei:place")
    return [x for place in places for x in make_place(place)]

# %%
def search_editor(tei):
    if ref := tei.any_xpath(".//tei:publisher[@ref]"):
        editor = ref[0].xpath('./text()')[0]
    else:
        editor = False
    return editor

# %%
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

# %%
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

# %%
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

# %%
def get_contributors(tei):
    predobj = []
    contributors = tei.any_xpath(".//tei:respStmt")
    for contributor in contributors:
        pred = contributor.xpath(".//tei:persName/@role", namespaces=nsmap)[0].split(':')[-1]
        obj = contributor.xpath(".//tei:persName/@ref", namespaces=nsmap)[0].lstrip('#')
        # The contributor has a PI
        if obj.startswith('http'):
            obj = URIRef(obj)
            pred = ACDH[pred]
        # The contributor has no PI
        else:
            forename = contributor.xpath(".//tei:forename/text()", namespaces=nsmap)[0]
            surname = contributor.xpath(".//tei:surname/text()", namespaces=nsmap)[0]
            obj = Literal(f"{forename} {surname}")
            pred = ACDH['hasNonLinkedIdentifier']
        predobj.append((pred, obj))
    return predobj

# %%
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

# %%
def get_tifs(tei):
    tifs  = []
    for tif in tei.any_xpath(".//tei:graphic/@url"):
        base =  re.search("files/images/(.*)/full/full", tif).group(1)
        if base not in tifs:
            tifs.append(base)
    return tifs

# %%
g = Graph().parse("arche_seed_files/arche_constants.ttl")
g_repo_objects = Graph().parse("arche_seed_files/repo_objects_constants.ttl")
#g.parse("arche_seed_files/arche_constants.ttl")

# %%
[g.add(x) for x in get_persons("data/indices/listperson.xml")]

# %%
[g.add(x) for x in get_places("data/indices/listplace.xml")]

count = 0
# %%
files = glob.glob("data/editions/*.xml")
[
        g.add((TOP_COL_URI, ACDH["hasRelatedDiscipline"], related))
        for related in [URIRef("https://vocabs.acdh.oeaw.ac.at/oefosdisciplines/605007"),
                        URIRef("https://vocabs.acdh.oeaw.ac.at/oefosdisciplines/605008"),
                        URIRef("https://vocabs.acdh.oeaw.ac.at/oefosdisciplines/604024")]
    ]
for xmlfile in files:
    if not any([x in xmlfile for x in fails]):
        continue
    persons = get_persons(xmlfile)
    basename = os.path.basename(xmlfile).split('.')[0]
    doc = TeiReader(xmlfile)
    COL_URI = URIRef(f"{TOP_COL_URI}/{basename}")
    dates = get_date(doc)
    extent = get_extent(doc)
    ### Creates collection

    g.add((COL_URI, RDF.type, ACDH["Collection"]))
    # g.add((COL_URI, ACDH["hasTitle"], Literal(basename)))
    g.add((COL_URI, ACDH["isPartOf"], TOP_COL_URI))
    g.add((COL_URI, ACDH["hasRightsHolder"], RightsHolder))
    g.add((COL_URI, ACDH["hasMetadataCreator"], MetadataCreator))
    g.add((COL_URI, ACDH["hasLicensor"], Licensor))
    g.add((COL_URI, ACDH["hasOwner"], Owner))
    g.add((COL_URI, ACDH["hasDepositor"], Depositor))
    if has_title := doc.any_xpath(".//tei:title[@type='main']/text()"):
        has_title = has_title[0]
    else:
        has_title = "No title provided"
    print(f'{COL_URI}\thasTitle:\t"{has_title}"')
    # g.add((COL_URI, ACDH["hasTitle"], Literal(has_title)))

    ### creates resource for the XML
    subj = URIRef(f"{COL_URI}/{basename}")
    g.add((subj, RDF.type, ACDH["Resource"]))
    g.add((subj, ACDH["isPartOf"], COL_URI))
    print('SUB:', subj)
    if signature :=  doc.any_xpath(".//tei:idno[@type='shelfmark']"):
        g.add(
            (subj, ACDH["hasNonLinkedIdentifier"], Literal(signature[0].text))
        )
    g.add(
        (subj, ACDH["hasCategory"], URIRef("https://vocabs.acdh.oeaw.ac.at/archecategory/text/tei"))
    )
    # if editor := search_editor(doc):
    #    g.add((COL_URI, ARCHE["hasPublisher"], Literal(editor)))
    #    print((COL_URI, ACDH["hasPublisher"], Literal(editor)))
    g.add((subj, ACDH["hasTitle"], Literal(has_title)))
    g.add((subj, ACDH["hasFilename"], Literal(f"{basename}.xml")))
    g.add((subj, ACDH["hasFormat"], Literal("application/xml")))
    #### g.add((subj, ACDH["hasCreatedStartDateOriginal"], dates[0]))
    #### g.add((subj, ACDH["hasCreatedEndDateOriginal"], dates[1]))
    g.add((subj, ACDH["hasLanguage"], URIRef("https://vocabs.acdh.oeaw.ac.at/iso6393/lat")))
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
    test = []
    for tif in get_tifs(doc):
        if tif not in test:
            test.append(tif)
        else:
            print (f'Duplicado\t{tif}')

        resc = URIRef(f"{COL_URI}/{tif}")
        print('TIF:', resc)
        g.add((resc, RDF.type, ACDH["Resource"]))
        g.add((resc, ACDH["isPartOf"], COL_URI))
        g.add((resc, ACDH["hasTitle"], Literal(tif)))
        g.add((resc, ACDH["isSourceOf"], subj))
        g.add((resc, ACDH["hasFilename"], Literal(f"{tif}.tiff")))
        # The object in the following ones needs to be adapted to meet the actual features 
        g.add((resc, ACDH["hasRightsHolder"], RightsHolder))
        g.add((resc, ACDH["hasOwner"], Owner))
        g.add((resc, ACDH["hasMetadataCreator"], MetadataCreator))
        g.add((resc, ACDH["hasDepositor"], Depositor))
        g.add((resc, ACDH["hasCategory"], Literal("Text")))  # not sure
        g.add((resc, ACDH["hasLicense"], Licence)) 
        g.add((resc, ACDH["hasLicensor"], Licensor))
    #if count > 3:
    #    break
    #else:
    #    count += 1


# %%
try:
    g.serialize("test.ttl")
except Exception as e:
    print(e)

# %%
# %%

# .//sourceDesc/bibl/pubPlace@ref
# .//sourceDesc/bibl/publisher@ref

# .//sourceDesc/msDesc/msIdentifier/institution
# .//sourceDesc/msDesc/msIdentifier/repository/placeName
# .//sourceDesc/msDesc/msIdentifier/repository/idno/@subtype  # GND, Wikidata

# .//sourceDesc/msDesc/msContents/@class
# .//sourceDesc/msDesc/msContents/summary/text()

#hasPublisher


# .//sourceDesc/physDesc/objectDesc/@form


# "hasUsedHardware"
# "hasUsedSoftware"
# .//sourceDesc/history/provenance/placeName/@ref
# .//sourceDesc/history/provenance/placeName/text()


