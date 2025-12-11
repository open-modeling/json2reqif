#!/usr/bin/env python3
"""
JSON to ReqIF Converter - Using strictdoc/reqif Library
"""

from pathlib import Path
import re
import json
from jsonpath_ng import DatumInContext
from jsonpath_ng.ext import parse

import jsonpath
import sys
import pydantic
import shortuuid

from datetime import datetime, timezone
from typing import Any, Dict, List, Union
from xmlrpc.client import Boolean
from reqif.unparser import ReqIFUnparser
from reqif.reqif_bundle import ReqIFBundle
from reqif.models.reqif_core_content import ReqIFCoreContent
from reqif.models.reqif_data_type import (
      ReqIFDataTypeDefinitionInteger,
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

from models import mapping, mapping_capella

class ReqIFConveterHelper:
    @staticmethod
    def _get_timestamp() -> str:
        """Get ISO 8601 timestamp"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000+00:00')

    @staticmethod
    def _gen_id(prefix: str = "ID", name: str|None = None) -> str:
        """Generate unique identifier"""
        return f"{prefix}_{shortuuid.uuid(name)}"

class SpecDataTypesHelper:
    def __init__(self):
        self.data_types: Dict[str, ReqIFDataTypeDefinitionInteger|ReqIFDataTypeDefinitionString|ReqIFDataTypeDefinitionXHTML|ReqIFDataTypeDefinitionEnumeration] = {}
        self.data_typed_by_id: Dict[str, ReqIFDataTypeDefinitionInteger|ReqIFDataTypeDefinitionString|ReqIFDataTypeDefinitionXHTML|ReqIFDataTypeDefinitionEnumeration] = {}
        self.GENERATORS = {
            "INTEGER": self.createIntegerType,
            "STRING": self.createStringType,
            "XHTML": self.createXhtmlType,
            "ENUMERATION": self.createEnumType
        }

    def createType(self, type: str, subType: str, rest):
        t = f"{type}_{subType}"
        if not self.data_types.get(t):
            gen_type = self.GENERATORS[type](subType, rest)
            self.data_types[t] = gen_type
            self.data_typed_by_id[gen_type.identifier] = gen_type

        return self.data_types[t]

    def createIntegerType(self, subType: str, rest):
        type = f"INTEGER_{subType}"
        return ReqIFDataTypeDefinitionInteger(
            identifier  = ReqIFConveterHelper._gen_id("DTD", type),
            long_name   = type,
            last_change = ReqIFConveterHelper._get_timestamp(),
            min_value   = rest.min or "0",
            max_value   = rest.max or "65535"
        )

    def createStringType(self, subType: str, rest):
        type = f"STRING_{subType}"
        return ReqIFDataTypeDefinitionString(
            identifier  = ReqIFConveterHelper._gen_id("DTD", type),
            long_name   = type,
            last_change = ReqIFConveterHelper._get_timestamp(),
            max_length  = rest.maxLength or "255",
        )
    
    def createXhtmlType (self, subType: str, rest):
        type = f"XHTML_{subType}" if subType else "XHTML"
        return ReqIFDataTypeDefinitionXHTML(
            identifier  = ReqIFConveterHelper._gen_id("DTD", type),
            long_name   = type,
            last_change = ReqIFConveterHelper._get_timestamp(),
        )

    def createEnumType (self, subType: str, rest):
        type = f"ENUM_{subType}"
        vals = []
        for val in rest.values:
            vals.append(ReqIFEnumValue(
                identifier    = ReqIFConveterHelper._gen_id("EV", val.value),
                last_change   = ReqIFConveterHelper._get_timestamp(),       
                key           = str(val.key),
                long_name     = val.value,
                other_content = val.content,
            ))

        return ReqIFDataTypeDefinitionEnumeration(
            identifier  = ReqIFConveterHelper._gen_id("DTD", type),
            long_name   = type,
            last_change = ReqIFConveterHelper._get_timestamp(),
            values      = vals
        )

class SpecTypesHelper:
    '''Helper for the specification types operations'''
    def __init__(self, spec: mapping.Specification | mapping_capella.Specification, helper: SpecDataTypesHelper):
        self.data_types_helper = helper

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

        ### Pre-parse specification
        typeName = spec.type
        self.spec_attrs[typeName] = {}
        for key, val in spec.attributes:
            if not val: continue

            attr = SpecAttributeDefinition(
                identifier          = ReqIFConveterHelper._gen_id("SAD", key),
                last_change         = ReqIFConveterHelper._get_timestamp(),
                attribute_type      = self._TYPES[val.attributeType],
                datatype_definition = self.data_types_helper.createType(val.attributeType, val.type, val).identifier,
                long_name           = val.longName,
            )

            self.spec_attrs[typeName][key] = attr

        specification = ReqIFSpecificationType(
            identifier      = ReqIFConveterHelper._gen_id('ST', typeName),
            last_change     = ReqIFConveterHelper._get_timestamp(),
            long_name       = typeName,
            spec_attributes = [*self.spec_attrs[typeName].values()],
        )

        self.spec_types[typeName] = specification

    def getSpecType (self, specType) -> ReqIFSpecificationType:
        """Retrieves or creates specification type based on its name"""

        return self.spec_types[specType]
    
    def getSpecAttrType (self, specType, attrName) -> SpecAttributeDefinition:
        """Retrieves or creates specification attrbiute type based on its name"""

        return self.spec_attrs[specType][attrName]

class SpecObjectTypesHelper:
    '''Helper for the specification object types operations'''
    def __init__(self, object: mapping.Requirements | mapping_capella.Requirements, helper: SpecDataTypesHelper):
        self.data_types_helper = helper

        self.spec_types: Dict[str, ReqIFSpecObjectType] = {}
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

        ### Pre-parse specification object types
        for req in object.variants:
            typeName = req.type
            self.spec_attrs[typeName] = {}
            for key, val in req.attributes:
                if not val: continue

                name = f"{typeName}_{key}"
                attr = SpecAttributeDefinition(
                    identifier          = ReqIFConveterHelper._gen_id("AD", name),
                    attribute_type      = self._TYPES[val.attributeType],
                    datatype_definition = self.data_types_helper.createType(val.attributeType, val.type, val).identifier,
                    long_name           = val.longName,
                    ### Explicitly false, unless someone needs to implement multi choice
                    multi_valued        = False if val.attributeType == "ENUMERATION" else None,
                    last_change         = ReqIFConveterHelper._get_timestamp()
                )

                self.spec_attrs[typeName][key] = attr

            specification = ReqIFSpecObjectType(
                identifier            = ReqIFConveterHelper._gen_id('SOT', typeName),
                long_name             = typeName,
                last_change           = ReqIFConveterHelper._get_timestamp(),
                attribute_definitions = [*self.spec_attrs[typeName].values()],
            )

            self.spec_types[typeName] = specification

    def getSpecType (self, specType) -> ReqIFSpecObjectType:
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

        self.data_types_helper: SpecDataTypesHelper = SpecDataTypesHelper()
        self.types_helper: SpecTypesHelper = SpecTypesHelper(self.config.specification, self.data_types_helper)
        self.object_types_helper: SpecObjectTypesHelper = SpecObjectTypesHelper(self.config.requirements, self.data_types_helper)

        self.timestamp = ReqIFConveterHelper._get_timestamp()
        self.leaf_objects = []
        self.all_objects = []
        self.hierarchy_data = []

    def phase (self):
        self._phase += 1
        return self._phase 

    def buildAttribute(self, attr: SpecAttributeDefinition, val: str):
        type = attr.attribute_type

        new_val: str | List[str] = ""

        if not val:
            return None

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

            new_val = lxml_convert_to_reqif_ns_xhtml_string(f"<div>{val}</div>", False)
        elif type == SpecObjectAttributeType.ENUMERATION:
            enum_type = self.data_types_helper.data_typed_by_id[attr.datatype_definition]
            if isinstance(enum_type, ReqIFDataTypeDefinitionEnumeration):
                vals = enum_type.values
                if vals:
                    filtered = list(filter(lambda v: v.long_name == val, vals)).pop()
                    if filtered:
                        new_val = [filtered.identifier]
        else:
            new_val = val
 
        return SpecObjectAttribute(
                                attribute_type=type,
                                value=new_val,
                                definition_ref=attr.identifier,
                            )

    def extract_objects(self) -> None:
        """Extract leaf nodes and attributes"""
        print(f"\n[Phase {self.phase()}] Extracting objects...")

        def traverse(node: Dict, req_variant: mapping.Variant|mapping_capella.Variant, level = 1) -> ReqIFSpecHierarchy: 
            is_leaf = len(node.get("children", [])) == 0

            obj_data = ReqIFSpecObject(
                identifier       = ReqIFConveterHelper._gen_id("OBJ"),
                attributes       = [],
                description      = lxml_escape_for_html(node.get("Caption", "..Empty..")),
                spec_object_type = self.object_types_helper.getSpecType(req_variant.type).identifier, 
                last_change      = ReqIFConveterHelper._get_timestamp(),
            )

            has_table : Boolean = False

            # Extract all attributes
            for attr_key, attr_val in req_variant.attributes:
                if not attr_val: continue

                attr = self.object_types_helper.getSpecAttrType(req_variant.type, attr_key)
                if attr_val.selector:
                    val = self.buildAttribute(attr, " ".join(map(lambda v: v.value, parse(attr_val.selector).find(node))))
                else:
                    val = self.buildAttribute(attr, attr_val.literal)

                if val:
                    obj_data.attributes.append(val) 

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
            for child in parse(self.config.requirements.selector.root).find(node):
                for req_variant in self.config.requirements.variants: 
                    for match in parse(req_variant.match.root).find(child.value):
                        hier = traverse(match.value, req_variant, level + 1)
                        hier_data.add_child(hier)

            return hier_data

        # Start traversal
        for root in parse(self.config.requirements.selector.root).find(self.data):
            for req_variant in self.config.requirements.variants:
                for match in parse(req_variant.match.root).find(root.value):
                    hier = traverse(match.value, req_variant)
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
            val = self.buildAttribute(attrType, " ".join(map(lambda v: v.value, parse(attr.selector).find(data.value))))

            if val:
                attr_objects.append(val)

        specification = ReqIFSpecification(
            identifier         = ReqIFConveterHelper._gen_id("SPEC", parse(spec.id.root).find(data.value).pop().value),
            long_name          = parse(spec.attributes.ReqIF_Name.selector).find(data.value).pop().value,
            last_change        = ReqIFConveterHelper._get_timestamp(),
            children           = self.hierarchy_data,
            values             = [*attr_objects],
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

        spec_objects = self.all_objects

        core_content = ReqIFCoreContent(
            req_if_content = ReqIFReqIFContent(
                data_types     = [*self.data_types_helper.data_types.values()],
                spec_objects   = spec_objects,
                specifications = specifications,
                spec_types     = [*self.types_helper.spec_types.values(), *self.object_types_helper.spec_types.values()],
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
    
    PossibleConfigs = Union[mapping_capella.ReqifChoiceSchema, mapping.ReqifChoiceSchema]
    adapter = pydantic.TypeAdapter(PossibleConfigs)
    return adapter.validate_json(config)

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

        with open(output_path, "w", encoding="UTF-8") as output_file:
            output_file.write(reqif_xml_output)

        print("\n" + "="*70)
        print("✓ CONVERSION COMPLETE")
        print("="*70)

        return 0

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
