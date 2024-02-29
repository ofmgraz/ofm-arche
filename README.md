# ofm-arche
Repository to provide ARCHE with data


## collections structure

# TopCollection
* URI: acdhi:ofm-graz
* hasTitle: Choralhandschriften der Zentralbibliothek der Wiener Franziskanerprovinz Graz

## Collection (for each book)
* URI acdhi:ofm-graz/{filename without extension}; acdhi:A63_51
* hasTitle: `<title type="main">A 64/34</title>`
* isPartOf: acdhi:ofm-graz
* hasDescription: ~ Die Sammlung {hasTitle} beinhalte die {len(files)} Digitalisate des Chorbuches {hasTitle} sowie den nach XML/TEI annotierten Volltext.
* hasCreatedOriginalStart / end:  ```<bibl><date notBefore="1625-01-01" notAfter="1650-12-31">16-2/4</date></bibl>```
* hasDigitizingAgent: `<persName role="acdh:hasDigitisingAgent" ref="placeholder">`

### Resource TEI
* URI acdhi:{filename with extension}; acdhi:A67_17.xml
* isPartOf: acdhi:ofm-graz/{filename with extension}
* ...

### Resource Image
`for x in <graphic url=@url/>`
* URI acdhi:{filename with extension} acdhi:ofm-graz/A-Gf_A_67_17-001r.tiff
* isPartOf acdhi:ofm-graz/{filename of the TEI without extension} acdhi:ofm-graz/A67_17
* hasTitle: filename
* isSourceOf related TEI e.g. acdhi:ofm-graz/A67_17.xml
* ...

to be discussed if and how we should duplicate metadata, e.g. hasDigitizingAgent could be applied on collection and on resource level; to consult with ARCHE team
