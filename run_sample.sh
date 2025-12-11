python -m json2reqif sample/req_in.json sample/req_out.reqif sample/mapping_capella.json
xmllint --schema xml_schema/dtc-11-04-05.xsd --noout sample/req_out.reqif