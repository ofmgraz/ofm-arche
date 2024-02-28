# %%
import glob
import os
from rdflib import Graph, Namespace, URIRef, RDF, Literal, XSD, BNode
from acdh_tei_pyutils.tei import TeiReader, ET

# %%
TOP_COL_URI = URIRef("https://id.acdh.oeaw.ac.at/ofm-graz")
ACDH = Namespace("https://vocabs.acdh.oeaw.ac.at/schema#")
nsmap = {"tei": "http://www.tei-c.org/ns/1.0"}

# %%
# I know an element present in the node wanted (e.g. tei:persName), but it can be in different
# types of nodes (e.g. tei:persStmt vs tei:person). So I get a list of those elements
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
                output.append((subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()"))))
            else:
                subject = URIRef(i.xpath("./text()"))
                output = [(subject, RDF.type, ACDH["Person"])]
    first_name = person.xpath(".//tei:persName/tei:forename/text()", namespaces=nsmap)[0]
    last_name = person.xpath(".//tei:persName/tei:surname/text()", namespaces=nsmap)[0]
    return output + [(subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}"))]

# %%
# Takes a tei:place element and returns a tuple of triples to add to the RDF 
def make_place(place):
    if place.xpath(".//tei:placename[@xml:lang='de']", namespaces=nsmap):
        placename = place.xpath(".//tei:placeName[@xml:lang='de']", namespaces=nsmap)[0]
    else:
        placename = place.xpath(".//tei:placeName", namespaces=nsmap)[0]
    i = place.xpath(".//tei:idno[@subtype='GND']", namespaces=nsmap)
    if i:
        subject = URIRef(i[0].xpath("./text()"))
        output = [(subject, RDF.type, ACDH["Place"])]
    ids = place.xpath(".//tei:idno[@type='URL']", namespaces=nsmap)
    for i in ids:
        if output and i.xpath("./@subtype")[0] != "GND":
            output.append((subject, ACDH["hasIdentifier"], URIRef(i.xpath("./text()"))))
        else:
            subject = URIRef(i.xpath("./text()"))
            output = [(subject, RDF.type, ACDH["Place"])]
    return output + [(subject, RDF.type, Literal(f"{placename}") )]

# %%
def get_persons(tei):
    list_file = glob.glob(tei)[0]
    persons = get_parent_node("tei:persName", list_file)
    for person in persons:
        [g.add(x) for x in make_person(person)]

# %%
def get_places(tei):
    list_file = glob.glob(tei)[0]
    places = TeiReader(tei).any_xpath(".//tei:place")
    for place in places:
        [g.add(x) for x in make_place(place)]

# %%
g = Graph()
g.parse("arche_seed_files/arche_constants.ttl")

# %%
### Get Persons
get_persons("data/indices/listperson.xml")

### Get places
get_places("data/indices/listplace.xml")


# %%
files = glob.glob("data/editions/*.xml")
for xmlfile in files:
    get_persons(xmlfile)
    basename = os.path.basename(xmlfile)
    doc = TeiReader(xmlfile)
    subj = URIRef(f"{TOP_COL_URI}/{basename}")
    g.add(
        (subj, RDF.type, ACDH["Resource"])
    )
    try:
        has_title = doc.any_xpath('.//tei:title')[0].text   
    except AttributeError:
        has_title = 'No title provided'
    g.add(
        (subj, ACDH["hasTitle"], Literal(has_title, lang="la"))
    )
    g.add(
        (subj, ACDH["hasCreatedStartDateOriginal"], Literal('2024-02-27', datatype=XSD.date))
    )
    g.add(
        (subj, ACDH["hasCreatedEndDateOriginal"], Literal('2024-02-27', datatype=XSD.date))
    )
try:
    g.serialize("test.ttl")
except Exception as e:
    print(e)

    

# %%


# %%
# .//titleStmt/title[main]/text(): "hasTitle",
# .//sourceDesc/msDesc/msIdentifier/idno[type="shelfmark]: "hasNonLinkedIdentifier"
 
#Document hasXXXX object

# Subject xx Xxxx

# "hasPrincipalInvestigator"
# "hasDigitisingAgent"
# respStmt
# publicationStm
# hasContributor
# hasCategory XML/TEI
#hasMetadataCreator
# hasNonLinkedContributor JL

# .//sourceDesc/bibl/date/@notBefore: "hasCreatedStartDateOriginal"
# .//sourceDesc/bibl/date/@notAfter: "hasCreatedEndDateOriginal"

# .//sourceDesc/bibl/pubPlace@ref
# .//sourceDesc/bibl/publisher@ref

# .//sourceDesc/msDesc/msIdentifier/institution
# .//sourceDesc/msDesc/msIdentifier/repository/placeName
# .//sourceDesc/msDesc/msIdentifier/repository/idno/@subtype  # GND, Wikidata

# .//sourceDesc/msDesc/msContents/@class
# .//sourceDesc/msDesc/msContents/summary/text()

#hasPublisher


# .//sourceDesc/physDesc/objectDesc/@form

# .//sourceDesc/physDesc/objectDesc/supportDes/support/dimensions/@unit   "hasExtent"
# .//sourceDesc/physDesc/objectDesc/supportDes/support/dimensions/height
# .//sourceDesc/physDesc/objectDesc/supportDes/support/dimensions/width

# .//sourceDesc/physDesc/objectDesc/supportDes/support/extent/@measure unit     : "hasExtent"
# .//sourceDesc/physDesc/objectDesc/supportDes/support/extent/@quantity
# .//sourceDesc/physDesc/objectDesc/supportDes/support/extent.text()



# "hasUsedHardware"
# "hasUsedSoftware"
# .//sourceDesc/history/provenance/placeName/@ref
# .//sourceDesc/history/provenance/placeName/text()

# encodingDesc/editorialDecl
# profileDesc/langUsage/language/@ident : "lang"
# profileDesc/langUsage/language/@ident : "hasLanguage"
# hasPersonalTitle
# hasFirstName
# hasLastName
# hasAddress

# %%


# %%



