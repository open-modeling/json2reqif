"""
JSON to ReqIF Converter
"""

import sys
from jsonpath_ng import DatumInContext
from jsonpath_ng.ext import parse

from typing import Any, Dict, List
from xmlrpc.client import Boolean

from reqif.reqif_bundle import ReqIFBundle
from reqif.models.reqif_core_content import ReqIFCoreContent
from reqif.models.reqif_namespace_info import ReqIFNamespaceInfo
from reqif.models.reqif_req_if_content import ReqIFReqIFContent
from reqif.models.reqif_reqif_header import ReqIFReqIFHeader
from reqif.models.reqif_spec_hierarchy import ReqIFSpecHierarchy
from reqif.models.reqif_spec_object import ReqIFSpecObject, SpecObjectAttribute

from reqif.models.reqif_specification import ReqIFSpecification

from reqif.object_lookup import ReqIFObjectLookup
from reqif.reqif_bundle import ReqIFBundle

from reqif.helpers.lxml import (
    lxml_escape_for_html
)

from json2reqif._types import (
    ReqIFMappingSchema,
    ReqIFMappingSpecification,
    ReqIFMappingVariant
)
from json2reqif.helpers.spec_datatypes import SpecDataTypesHelper

from json2reqif.helpers import (
    _gen_id,
    _get_timestamp
)
from json2reqif.helpers.spec_object import buildAttribute
from json2reqif.helpers.spec_object_types import SpecObjectTypesHelper
from json2reqif.helpers.spec_types import SpecTypesHelper


class ReqIFConverterLib:
    """ReqIF Converter using strictdoc/reqif library"""

    def __init__(self, json: Any, config: ReqIFMappingSchema):
        """Initialize converter with JSON input"""

        self._phase = 0

        self.data = json
        self.config = config

        self.data_types_helper: SpecDataTypesHelper = SpecDataTypesHelper()
        self.types_helper: SpecTypesHelper = SpecTypesHelper(self.config.specification, self.data_types_helper)
        self.object_types_helper: SpecObjectTypesHelper = SpecObjectTypesHelper(self.config.requirements, self.data_types_helper)

        self.timestamp = _get_timestamp()
        self.leaf_objects = []
        self.all_objects = []
        self.hierarchy_data = []

    def phase (self):
        self._phase += 1
        return self._phase 



    def extract_objects(self) -> None:
        """Extract leaf nodes and attributes"""
        print(f"\n[Phase {self.phase()}] Extracting objects...", file=sys.stderr)

        def traverse(node: Dict, req_variant: ReqIFMappingVariant, level = 1) -> ReqIFSpecHierarchy: 
            is_leaf = len(node.get("children", [])) == 0

            obj_data = ReqIFSpecObject(
                identifier       = _gen_id("OBJ"),
                attributes       = [],
                description      = lxml_escape_for_html(node.get("Caption", "..Empty..")),
                spec_object_type = self.object_types_helper.getSpecType(req_variant.type).identifier, 
                last_change      = _get_timestamp(),
            )

            has_table : Boolean = False

            # Extract all attributes
            for attr_key, attr_val in req_variant.attributes:
                if not attr_val: continue

                attr = self.object_types_helper.getSpecAttrType(req_variant.type, attr_key)
                if attr_val.selector:
                    val = buildAttribute(attr, " ".join(map(lambda v: v.value, parse(attr_val.selector).find(node))), self.data_types_helper)
                else:
                    val = buildAttribute(attr, attr_val.literal, self.data_types_helper)

                if val:
                    obj_data.attributes.append(val) 

            if is_leaf:
                self.leaf_objects.append(obj_data)

            self.all_objects.append(obj_data)

            # Intermediate node
            hier_data = ReqIFSpecHierarchy(
                identifier  =_gen_id("HIER"),
                long_name   =lxml_escape_for_html(str(obj_data.description)),
                last_change =_get_timestamp(),
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


        print(f"      ✓ Total nodes:       {len(self.all_objects)}", file=sys.stderr)
        print(f"      ✓ Leaf nodes:        {len(self.leaf_objects)}", file=sys.stderr)
        print(f"      ✓ Hierarchy nodes:   {len(self.hierarchy_data)}", file=sys.stderr)

    def buildSpecifications (self) -> List[ReqIFSpecification]:
        """Build SPECIFICATION with hierarchy"""
        print(f"\n[Phase {self.phase()}] Building specifications...", file=sys.stderr)


        specs: List[DatumInContext] = parse(self.config.specification.selector.root).find(self.data)

        specifications = []

        for match in specs:
            specifications.append(self.buildSpecification(self.config.specification, match))

        print(f"      ✓ Created SPECIFICATIONs: {len(specifications)}", file=sys.stderr)
        return specifications

    def buildSpecification(self, spec: ReqIFMappingSpecification, data: DatumInContext) -> ReqIFSpecification:
        """Build SPECIFICATION entry"""

        attr_objects: List[SpecObjectAttribute] = []

        for key, attr in self.config.specification.attributes: 
            if not attr: continue

            attrType = self.types_helper.getSpecAttrType(spec.type, key)
            val = buildAttribute(attrType, " ".join(map(lambda v: v.value, parse(attr.selector).find(data.value))), self.data_types_helper)

            if val:
                attr_objects.append(val)

        specification = ReqIFSpecification(
            identifier         = _gen_id("SPEC", parse(spec.id.root).find(data.value).pop().value),
            long_name          = parse(spec.attributes.ReqIF_Name.selector).find(data.value).pop().value,
            last_change        = _get_timestamp(),
            children           = self.hierarchy_data,
            values             = [*attr_objects],
            specification_type = self.types_helper.getSpecType(spec.type).identifier
        )

        print(f"      ✓ Created SPECIFICATION with {len(specification.children or [])} children", file=sys.stderr)

        return specification


    def createReqIFHeader(self) -> ReqIFReqIFHeader :
        """Assemble ReqIF Header"""
        print(f"\n[Phase {self.phase()}] Assembling ReqIF Header...", file=sys.stderr)

        reqif_header = ReqIFReqIFHeader(
            identifier     = _gen_id("HDR"),
            creation_time  = self.timestamp,
            repository_id  = self.config.config.repository,
            req_if_tool_id = "JSON to ReqIF Converter",
            req_if_version = "1.0",
            source_tool_id = f'{self.config.config.tool} {self.config.config.toolVersion}',
            title          = "Exported Reqif"
        )

        print(f"      ✓ Header created", file=sys.stderr)
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

        print(f"      ✓ Assembled {len(self.all_objects)} SPEC-OBJECTs", file=sys.stderr)
        print(f"      ✓ Assembled {len(specifications)} SPECIFICATIONs", file=sys.stderr)

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


