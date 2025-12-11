from typing import Any

from reqif.unparser import ReqIFUnparser

from json2reqif._types import ReqIFMappingSchema

from json2reqif.converter import ReqIFConverterLib
from json2reqif.helpers import loadConfigOrExit

def loadMapping(mapping_path: str):
    '''
    Loads mapping from json to reqif
    
    :param mapping_path: path to json with mapping definition
    :type mapping_path: str
    '''
    return loadConfigOrExit(mapping_path)

def convert (json: Any, config: ReqIFMappingSchema, output: str | None = None) -> str:
    '''
    Converts input json according to configuration and optionally writes to output
    
    :param json: Json structure to apply configuration to for target reqif generation
    :type json: Any
    :param config: Configuration aligned with supplied schemas
    :type config: ReqIFRootSchema
    :param output: Optional output target
    :type output: str | None
    :return: Generated reqif xml
    :rtype: str
    '''

    converter = ReqIFConverterLib(json, config)
    bundle = converter.createBundle()

    reqif_xml_output = ReqIFUnparser.unparse(bundle)

    if output:
        with open(output, "w", encoding="UTF-8") as output_file:
            output_file.write(reqif_xml_output)

    return reqif_xml_output