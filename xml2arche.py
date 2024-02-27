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
# Takes a TEI element (respStmt or person) and returns a tuple to add to the RDF 
def parse_person(person):
    person_info = {}
    if person.xpath(".//tei:persName/@role", namespaces=nsmap):
      a = ACDH[person.xpath(".//tei:persName/@role", namespaces=nsmap)[0].split(":")[1]]
      # The  following line is necessary as there are non-empty ref attribs as placeholders 
      if person.xpath(".//tei:persName/@ref", namespaces=nsmap)[0] != "placeholder":
        subject = URIRef(person.xpath(".//tei:persName/@ref", namespaces=nsmap)[0])
      else:
        subject = ACDH["hasNonLinkedContributor"]  ### <- Person  
    else:
      a = ACDH["hasPublisher"] ### <- Person
      try:
         subject = person.xpath("./tei:idno[@subtype='GND']/text()", namespaces=nsmap)[0]
      except Exception:
         subject = person.xpath("./tei:idno[@type='URL']/text()", namespaces=nsmap)[0]
      subject = URIRef(subject)
    first_name = person.xpath(".//tei:persName/tei:forename/text()", namespaces=nsmap)[0]
    last_name = person.xpath(".//tei:persName/tei:surname/text()", namespaces=nsmap)[0]
    return [(subject, RDF.type, a), (subject, ACDH["hasTitle"], Literal(f"{first_name} {last_name}"))]

# %%
g = Graph()
g.parse("arche_seed_files/arche_constants.ttl")
for xmlfile in files:
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
    persons = doc.any_xpath(".//tei:person") + doc.any_xpath(".//tei:respStmt")
    for person in persons:
        [g.add(x) for x in parse_person(person)]
    g.serialize("test.ttl")

# %%


# %%
files = glob.glob("data/editions/*.xml")

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



