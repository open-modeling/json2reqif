#!/usr/bin/env python3
"""
JSON to ReqIF Converter - Using strictdoc/reqif Library
"""

from ast import Constant
from hmac import new
from logging import config
from pathlib import Path
from pickletools import StackObject
import re
import json
from jsonpath_ng import parse, JSONPath, DatumInContext
import sys
import reqif
import reqif.models
import shortuuid

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, cast
from xmlrpc.client import Boolean
from reqif.unparser import ReqIFUnparser
from reqif.reqif_bundle import ReqIFBundle
from reqif.models.reqif_core_content import ReqIFCoreContent
from reqif.models.reqif_data_type import (
      ReqIFDataTypeDefinitionString,
      ReqIFDataTypeDefinitionXHTML,
      ReqIFDataTypeDefinitionEnumeration,
      ReqIFEnumValue
)
from reqif.models.reqif_namespace_info import ReqIFNamespaceInfo
from reqif.models.reqif_req_if_content import ReqIFReqIFContent
from reqif.models.reqif_reqif_header import ReqIFReqIFHeader
from reqif.models.reqif_spec_hierarchy import ReqIFSpecHierarchy
from reqif.models.reqif_spec_object import ReqIFSpecObject, SpecObjectAttribute
from reqif.models.reqif_spec_object_type import (
    ReqIFSpecObjectType,
    SpecAttributeDefinition,

)
from reqif.models.reqif_specification import ReqIFSpecification
from reqif.models.reqif_specification_type import ReqIFSpecificationType
from reqif.models.reqif_types import (
      SpecObjectAttributeType,
        
)
from reqif.object_lookup import ReqIFObjectLookup
from reqif.reqif_bundle import ReqIFBundle
from reqif.unparser import ReqIFUnparser

from reqif.helpers.lxml import (
    lxml_convert_to_reqif_ns_xhtml_string,
    lxml_escape_for_html
)

from models import (
    mapping_capella,
    mapping
)
from models.defs import specification
from models.defs.types.types import EnumerationAttribute, EnumerationAttributeValue, ReqifAttributeTypeDefinitions

class ReqIFConveterHelper:
    @staticmethod
    def _get_timestamp() -> str:
        """Get ISO 8601 timestamp"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000+00:00')

    @staticmethod
    def _gen_id(prefix: str = "ID", name: str|None = None) -> str:
        """Generate unique identifier"""
        return f"{prefix}_{shortuuid.uuid(name)}"

EOTV = [
    ReqIFEnumValue(identifier=ReqIFConveterHelper._gen_id("EV", "ENUM_VALUE_REQ"), key="0", long_name="Requirement", other_content="Requirement", last_change=ReqIFConveterHelper._get_timestamp()),
    ReqIFEnumValue(identifier=ReqIFConveterHelper._gen_id("EV", "ENUM_VALUE_FUN"), key="1", long_name="Function",    other_content="Function",    last_change=ReqIFConveterHelper._get_timestamp()),        
    ReqIFEnumValue(identifier=ReqIFConveterHelper._gen_id("EV", "ENUM_VALUE_CAP"), key="2", long_name="Capability",  other_content="Capability",  last_change=ReqIFConveterHelper._get_timestamp()),        
    ReqIFEnumValue(identifier=ReqIFConveterHelper._gen_id("EV", "ENUM_VALUE_MIS"), key="3", long_name="Mission",     other_content="Mission",     last_change=ReqIFConveterHelper._get_timestamp()),        
]


DATA_TYPES : Dict[str, ReqIFDataTypeDefinitionXHTML|ReqIFDataTypeDefinitionString|ReqIFDataTypeDefinitionEnumeration]= {
    "XHTML":            ReqIFDataTypeDefinitionXHTML      (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_XHTML"),    description="Default XHTML",    long_name="DEF_XHTML",                       last_change=ReqIFConveterHelper._get_timestamp()),
    "STRING_VERSION":   ReqIFDataTypeDefinitionString     (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_VERSION"),  description="Document Version", long_name="DEF_VERSION",  max_length="50",   last_change=ReqIFConveterHelper._get_timestamp()),
    "STRING_ID":        ReqIFDataTypeDefinitionString     (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_ID"),       description="Requirement Id",   long_name="DEF_ID",       max_length="15",   last_change=ReqIFConveterHelper._get_timestamp()),
    "STRING_SECTION":   ReqIFDataTypeDefinitionString     (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_SECTION"),  description="Section Number",   long_name="DEF_SECTION",  max_length="30",   last_change=ReqIFConveterHelper._get_timestamp()),
    "STRING_UID":       ReqIFDataTypeDefinitionString     (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_UID"),      description="Unique Id",        long_name="DEF_UID",      max_length="30",   last_change=ReqIFConveterHelper._get_timestamp()),
    "STRING_URL":       ReqIFDataTypeDefinitionString     (identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_URL"),      description="Requirements URL", long_name="DEF_URL",      max_length="2048", last_change=ReqIFConveterHelper._get_timestamp()),
    "ENUM_OBJ_TYPE":    ReqIFDataTypeDefinitionEnumeration(identifier=ReqIFConveterHelper._gen_id("DTD", "DEF_OBJ_TYPE"), description="Object Type",      long_name="DEF_OBJ_TYPE", values    =EOTV,   last_change=ReqIFConveterHelper._get_timestamp())
}

ATTRIBUTES : Dict[str, SpecAttributeDefinition]= {
    "ReqIF.Name":            SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.XHTML,       datatype_definition=DATA_TYPES['XHTML'].identifier,          long_name="ReqIF.Name",                                last_change=ReqIFConveterHelper._get_timestamp()),
    "ReqIF.Text":            SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.XHTML,       datatype_definition=DATA_TYPES['XHTML'].identifier,          long_name="ReqIF.Text",                                last_change=ReqIFConveterHelper._get_timestamp()),
    "ReqIF.ForeignRevision": SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.STRING,      datatype_definition=DATA_TYPES['STRING_VERSION'].identifier, long_name="ReqIF.ForeignRevision",                     last_change=ReqIFConveterHelper._get_timestamp()),
    "ReqIF.ForeignId":       SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.STRING,      datatype_definition=DATA_TYPES['STRING_ID'].identifier,      long_name="ReqIF.ForeignId",                           last_change=ReqIFConveterHelper._get_timestamp()),
    "ReqIF.ChapterName":     SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.STRING,      datatype_definition=DATA_TYPES['STRING_SECTION'].identifier, long_name="ReqIF.ChapterName",                         last_change=ReqIFConveterHelper._get_timestamp()),
    "IE PUID":               SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.STRING,      datatype_definition=DATA_TYPES['STRING_UID'].identifier,     long_name="IE PUID",                                   last_change=ReqIFConveterHelper._get_timestamp()),
    "URL":                   SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.STRING,      datatype_definition=DATA_TYPES['STRING_URL'].identifier,     long_name="URL",                                       last_change=ReqIFConveterHelper._get_timestamp()),
    "IE Object Type":        SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("AD"), attribute_type=SpecObjectAttributeType.ENUMERATION, datatype_definition=DATA_TYPES['ENUM_OBJ_TYPE'].identifier,  long_name="IE Object Type",        multi_valued=False, last_change=ReqIFConveterHelper._get_timestamp()),
}

SPEC_ATTRIBUTES : Dict[str, SpecAttributeDefinition]= {
    "Id":              SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("SAD"), attribute_type=SpecObjectAttributeType.STRING, datatype_definition=DATA_TYPES['STRING_ID'].identifier,      long_name="ReqIF.ForeignId",       last_change=ReqIFConveterHelper._get_timestamp()),
    "UID":             SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("SAD"), attribute_type=SpecObjectAttributeType.STRING, datatype_definition=DATA_TYPES['STRING_UID'].identifier,     long_name="IE PUID",               last_change=ReqIFConveterHelper._get_timestamp()),
    "URL":             SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id("SAD"), attribute_type=SpecObjectAttributeType.STRING, datatype_definition=DATA_TYPES['STRING_URL'].identifier,     long_name="URL",                   last_change=ReqIFConveterHelper._get_timestamp()),
    "SpecName":        SpecAttributeDefinition(identifier=ReqIFConveterHelper._gen_id('SAD'), attribute_type=SpecObjectAttributeType.XHTML,  datatype_definition=DATA_TYPES["XHTML"].identifier,          long_name="ReqIF.Name",            last_change=ReqIFConveterHelper._get_timestamp()),
}

SPEC_OBJECT_TYPES : Dict[str, ReqIFSpecObjectType]= {
    "Functional": ReqIFSpecObjectType.create(
        description="Requirement",
        identifier=ReqIFConveterHelper._gen_id("SOT"),
        last_change=ReqIFConveterHelper._get_timestamp(),
        attribute_definitions=list(ATTRIBUTES.values())
    )
}

SPEC_TYPES = {
    "Stakeholder Requirements":  ReqIFSpecificationType(
            identifier      = ReqIFConveterHelper._gen_id('SPEC-TYPE'),
            long_name       = "Stakeholder Requirements",
            last_change     = ReqIFConveterHelper._get_timestamp(),
            spec_attributes = list(SPEC_ATTRIBUTES.values())
        )
}

class SpecDataTypesHelper:
    def __init__(self):
        self.data_types: Dict[str, ReqIFDataTypeDefinitionString|ReqIFDataTypeDefinitionXHTML|ReqIFDataTypeDefinitionEnumeration] = {}
        self.GENERATORS = {
            "STRING": self.createStringType,
            "XHTML": self.createXhtmlType,
            "ENUM": self.createEnumType
        }

    def createType(self, type: str, subType: str, rest):
        t = f"{type}_{subType}"
        if not self.data_types.get(t):
            self.data_types[t] = self.GENERATORS[type](subType, rest)

        return self.data_types[t]

    def createStringType(self, subType: str, rest):
        type = f"STRING_{subType}"
        return ReqIFDataTypeDefinitionString(
            identifier=ReqIFConveterHelper._gen_id("DTD", type),
            # long_name=subType,
            last_change=ReqIFConveterHelper._get_timestamp(),
            max_length=rest.maxLength or "255",
        )
    
    def createXhtmlType (self, subType: str, rest):
        type = f"XHTML_{subType}"
        return ReqIFDataTypeDefinitionXHTML(
            identifier=ReqIFConveterHelper._gen_id("DTD", type),
            # long_name=subType,
            last_change=ReqIFConveterHelper._get_timestamp(),
        )

    def createEnumType (self, subType: str, rest):
        type = f"ENUM_{subType}"
        vals = []
        for val in rest.values:
            vals.append(ReqIFEnumValue(
                identifier=ReqIFConveterHelper._gen_id("EV", val.value),
                last_change=ReqIFConveterHelper._get_timestamp(),       
                key=str(val.key),
                long_name=val.value,
                other_content=val.content,
            ))

        return ReqIFDataTypeDefinitionEnumeration(
            identifier=ReqIFConveterHelper._gen_id("DTD", type),
            long_name=subType,
            last_change=ReqIFConveterHelper._get_timestamp(),
            values=vals
        )


class SpecTypesHelper:
    def __init__(self, spec: mapping.Specification | mapping_capella.Specification):
        self.data_types_helper = SpecDataTypesHelper()

        self.spec_attr_types: Dict[str, ReqIFSpecificationType] = {}
        self.spec_types: Dict[str, ReqIFSpecificationType] = {}
        self.spec_attrs: Dict[str, Dict[str, SpecAttributeDefinition]] = {}

        self._TYPES: Dict[str, SpecObjectAttributeType] = {
            'STRING': SpecObjectAttributeType.STRING,
            'ENUMERATION': SpecObjectAttributeType.ENUMERATION,
            'INTEGER': SpecObjectAttributeType.INTEGER,
            'REAL': SpecObjectAttributeType.REAL,
            'BOOLEAN': SpecObjectAttributeType.BOOLEAN,
            'DATE': SpecObjectAttributeType.DATE,
            'XHTML': SpecObjectAttributeType.XHTML
        }

        typeName = spec.type


        self.spec_attrs[typeName] = {}

        print(spec.attributes)

        for key, val in spec.attributes:
            if not val: continue

            print(key, "====", val)
            attr = SpecAttributeDefinition(
                identifier=ReqIFConveterHelper._gen_id("SAD", key),
                attribute_type=self._TYPES[val.attributeType],
                datatype_definition=self.data_types_helper.createType(val.attributeType, "", val).identifier,
                long_name=val.longName,
                last_change=ReqIFConveterHelper._get_timestamp()
            )

            self.spec_attrs[typeName][key] = attr

        specification = ReqIFSpecificationType(
            identifier      = ReqIFConveterHelper._gen_id('ST', typeName),
            long_name       = typeName,
            last_change     = ReqIFConveterHelper._get_timestamp(),
            spec_attributes = [*self.spec_attrs[typeName].values()]
        )

        self.spec_types[typeName] = specification

    def getSpecType (self, specType) -> ReqIFSpecificationType:
        """Retrieves or creates specification type based on its name"""

        return self.spec_types[specType]
    
    def getSpecAttrType (self, specType, attrName) -> SpecAttributeDefinition:
        """Retrieves or creates specification attrbiute type based on its name"""

        return self.spec_attrs[specType][attrName]


class ReqIFConverterLib:
    """ReqIF Converter using strictdoc/reqif library"""

    def __init__(self, json: Any, config: mapping.ReqifChoiceSchema|mapping_capella.ReqifChoiceSchema):
        """Initialize converter with JSON input"""

        self._phase = 0

        self.data = json
        self.config = config

        self.types_helper: SpecTypesHelper = SpecTypesHelper(self.config.specification)

        self.timestamp = ReqIFConveterHelper._get_timestamp()
        self.leaf_objects = []
        self.all_objects = []
        self.hierarchy_data = []

    def phase (self):
        self._phase += 1
        return self._phase 

    def buildAttribute(self, attr: SpecAttributeDefinition, val: str):
        type = attr.attribute_type
        if type == SpecObjectAttributeType.XHTML:
            # Random rich text issues breaking xml validator
            val = re.sub(r'(</?)s(?:trike)?(\s+|>)',                                   "\\1del\\2",                     val)
            val = re.sub(r'(<(meta|map)[^>]+>)',                                       "",                              val)
            val = re.sub(r'(<(?:font)\s*[^>]+>.+?</font>)',                            "",                              val)
            val = re.sub(r'(<(?:a)\s+[^>]*?)tabindex=[^\s>]+',                         "\\1",                           val)
            val = re.sub(r'(<(?:a|p|span|table)\s+[^>]*?)align=[^\s>]+',               "\\1",                           val)
            val = re.sub(r'(<(?:a|p|span|table)\s+[^>]*?)lang=[^\s>]+',                "\\1",                           val)
            val = re.sub(r'(<(?:a|p|span|table)\s+[^>]*?)info=[^\s>]+',                "\\1",                           val)
            val = re.sub(r'(<(?:a|p|span|table)\s+[^>]*?)target=[^\s>]+',              "\\1",                           val)
            val = re.sub(r'(<(?:a|p|span|table)\s+[^>]*?)(data-[^=]+=[^\s>]+\s*)+',    "\\1",                           val)
            val = re.sub(r'(<(?:a|p|table|tr|td|th|del)\s+[^>]*?)nativestyle=[^\s>]+', "\\1",                           val)
            val = re.sub(r'(<(?:table|tr|td|th)\s+[^>]*?)id=[^\s>]+',                  "\\1",                           val)
            val = re.sub(r'(<(?:td|th)\s+[^>]*?)width=[^\s>]+',                        "\\1",                           val)
            val = re.sub(r'(?<=/thead>)[\s\r\n]*(?=</table)',                          "<tbody><tr><td/></tr></tbody>", val)

            has_table = re.match(r'<table', val) != None

            def img2obj (img: re.Match) -> str:
                m = re.match(r'(?:.*?data:)([^;]+)', img.group(2))
                return f'<object type="{m.group(1) if m else ""}" data{img.group(2)} ></object>'

            # img is not supported by xhtml schema, replace with object and hope for the best
            val = re.sub(r'(<(?:img\s+)[^>]+?src([^\s>]+)[^>]*>)',                         img2obj,     val)

            val = lxml_convert_to_reqif_ns_xhtml_string(f"<div>{val}</div>", False)

        return SpecObjectAttribute(
                                attribute_type=type,
                                value=val,
                                definition_ref=attr.identifier,
                            )

    def extract_objects(self) -> None:
        """Extract leaf nodes and attributes"""
        print(f"\n[Phase {self.phase()}] Extracting objects...")

        def traverse(node: Dict, path: str = "", level = 1) -> ReqIFSpecHierarchy: 
            is_leaf = len(node.get("children", [])) == 0

            obj_data = ReqIFSpecObject(
                identifier       =ReqIFConveterHelper._gen_id("OBJ"),
                attributes       =[],
                description      =lxml_escape_for_html(node.get("Caption", "..Empty..")),
                spec_object_type =SPEC_OBJECT_TYPES['Functional'].identifier,
                last_change      =ReqIFConveterHelper._get_timestamp(),
            )

            has_table : Boolean = False

            # Extract all attributes
            for attr_key in ATTRIBUTES.keys():
                attr = ATTRIBUTES[attr_key]
                val = node.get(attr_key, "")

                if val:
                    obj_data.attributes.append(self.buildAttribute(attr, node.get(attr_key, ""))) 

            obj_data.attributes.append(
                SpecObjectAttribute(
                    attribute_type=ATTRIBUTES["IE Object Type"].attribute_type,
                    definition_ref=ATTRIBUTES["IE Object Type"].identifier,
                    value=[EOTV[0].identifier],
                )
            )

            if is_leaf:
                self.leaf_objects.append(obj_data)

            self.all_objects.append(obj_data)

            # Intermediate node
            hier_data = ReqIFSpecHierarchy(
                identifier  =ReqIFConveterHelper._gen_id("HIER"),
                long_name   =lxml_escape_for_html(str(obj_data.description)),
                last_change =ReqIFConveterHelper._get_timestamp(),
                spec_object =obj_data.identifier,
                children    =[],
                level       =level
            )

            if has_table:
                hier_data.is_table_internal = True

            # Recurse
            for child in node.get("children", []):
                child = traverse(child, path + " > " + node.get("Caption", ""), level + 1)
                hier_data.add_child(child)

            return hier_data

        # Start traversal
        for child in self.data.get("children", []):
            hier = traverse(child)
            self.hierarchy_data.append(hier)


        print(f"      ✓ Total nodes:       {len(self.all_objects)}")
        print(f"      ✓ Leaf nodes:        {len(self.leaf_objects)}")
        print(f"      ✓ Hierarchy nodes:   {len(self.hierarchy_data)}")

    def buildSpecifications (self) -> List[ReqIFSpecification]:
        """Build SPECIFICATION with hierarchy"""
        print(f"\n[Phase {self.phase()}] Building specifications...")


        specs: List[DatumInContext] = parse(self.config.specification.selector.root).find(self.data)

        specifications = []

        for match in specs:
            specifications.append(self.buildSpecification(self.config.specification, match))

        print(f"      ✓ Created SPECIFICATIONs: {len(specifications)}")
        return specifications

    def buildSpecification(self, spec: mapping.Specification | mapping_capella.Specification, data: DatumInContext) -> ReqIFSpecification:
        """Build SPECIFICATION entry"""

        attr_objects: List[SpecObjectAttribute] = []

        for key, attr in self.config.specification.attributes: 
            if not attr: continue

            attrType = self.types_helper.getSpecAttrType(spec.type, key)
            attr_objects.append(
                self.buildAttribute(attrType, " ".join(map(lambda v: v.value, parse(attr.selector).find(data.value))))
            )

        specification = ReqIFSpecification(
            identifier         = ReqIFConveterHelper._gen_id("SPEC", parse(spec.id.root).find(data.value).pop().value),
            long_name          = parse(spec.attributes.ReqIF_Name.selector).find(data.value).pop().value,
            last_change        = ReqIFConveterHelper._get_timestamp(),
            children           = self.hierarchy_data,
            values             = attr_objects,
            specification_type = self.types_helper.getSpecType(spec.type).identifier
        )

        print(f"      ✓ Created SPECIFICATION with {len(specification.children or [])} children")

        return specification


    def createReqIFHeader(self) -> ReqIFReqIFHeader :
        """Assemble ReqIF Header"""
        print(f"\n[Phase {self.phase()}] Assembling ReqIF Header...")

        reqif_header = ReqIFReqIFHeader(
            identifier     = ReqIFConveterHelper._gen_id("HDR"),
            creation_time  = self.timestamp,
            repository_id  = self.config.config.repository,
            req_if_tool_id = "JSON to ReqIF Converter",
            req_if_version = "1.0",
            source_tool_id = f'{self.config.config.tool} {self.config.config.toolVersion}',
            title          = "Exported Reqif"
        )

        print(f"      ✓ Header created")
        return reqif_header
    
    def createCoreContent(self, b: ReqIFBundle, data) -> ReqIFCoreContent:
        """Assemble ReqIf core content"""

        specifications = self.buildSpecifications()

        spec_objects   = self.all_objects


        core_content = ReqIFCoreContent(
            req_if_content = ReqIFReqIFContent(
                data_types     = [*DATA_TYPES.values(), *self.types_helper.data_types_helper.data_types.values()],
                spec_objects   = spec_objects,
                specifications = specifications,
                spec_types     = [*self.types_helper.spec_types.values()],
            )
        )

        print(f"      ✓ Assembled {len(self.all_objects)} SPEC-OBJECTs")
        print(f"      ✓ Assembled {len(specifications)} SPECIFICATIONs")

        return core_content

    def createBundle (self) -> ReqIFBundle:
        """Main conversion process"""

        self.extract_objects()

        b = ReqIFBundle(
            namespace_info=ReqIFNamespaceInfo.create_default(),
            req_if_header=None,
            core_content=None,
            tool_extensions_tag_exists=False,
            lookup=ReqIFObjectLookup.empty(),
            exceptions=[],
        )

        b.req_if_header = self.createReqIFHeader()
        b.core_content = self.createCoreContent(b, self.data);
        
        return b

def loadOrExit (path, role, plaintext=False) -> Any | None:
    """Loads resources"""
    if not Path(path).exists():
        print(f"Error: {role} file not found: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        if plaintext:
            return f.read()
        else:
            return json.load(f)

def loadConfigOrExit (path, role) -> mapping.ReqifChoiceSchema|mapping_capella.ReqifChoiceSchema:
    """Returns config cast to approptiate type"""
    config = loadOrExit(path, role, True)
    if (config == None):
        sys.exit(1)
    if (re.match(r'mapping_capella', config)):
        return mapping_capella.ReqifChoiceSchema.model_validate_json(config)
        # return mapping_capella.ReqifChoiceSchema(config['config'], config['specification'], config['requirements'], config.get('relations') or None)
        # return cast(mapping_capella.ReqifChoiceSchema, config)
    else:
        return mapping.ReqifChoiceSchema.model_validate_json(config)
        # return mapping.ReqifChoiceSchema(config['config'], config['specification'], config['requirements'], config.get('relations') or None)
        # return cast(mapping.ReqifChoiceSchema, config)
    


def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("Usage: python json_to_reqif.py <input.json> <output.reqif> [config.yaml]")
        print()
        print("Arguments:")
        print("  input.json    - JSON file to convert")
        print("  output.reqif  - Output ReqIF file")
        print("  config.yaml   - Mapping configuration (default: mapping_config.json)")
        sys.exit(1)

    json_path = sys.argv[1]
    output_path = sys.argv[2]
    config_path = len(sys.argv) > 3 and sys.argv[3] or "mapping_config.json"

    # Validate input files exist
    print("[Init] Loading JSON...")

    json   = loadOrExit(json_path,   "Input")
    config = loadConfigOrExit(config_path, "Config")


    try:
        print("="*70)
        print("JSON TO REQIF CONVERTER")
        print("="*70)

        if json:
            print(f"      ✓ JSON loaded: {len(json.get('children', []))} top-level nodes")
        else:
            print("          JSON load failed")
            sys.exit(1)


        converter = ReqIFConverterLib(json, config)
        b = converter.createBundle()

        reqif_xml_output = ReqIFUnparser.unparse(b)

        # print(reqif_xml_output)
        # from lxml import etree

        # tree = etree.fromstring('<?xml version="1.0" encoding="UTF-8"?>' + reqif_xml_output);

        with open(output_path, "w", encoding="UTF-8") as output_file:
            output_file.write(reqif_xml_output)

        print("\n" + "="*70)
        print("✓ CONVERSION COMPLETE - Ready for ReqIFUnparser")
        print("="*70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
