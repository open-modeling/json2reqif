import re
from typing import List
from reqif.helpers.lxml import lxml_convert_to_reqif_ns_xhtml_string
from reqif.models.reqif_data_type import ReqIFDataTypeDefinitionEnumeration
from reqif.models.reqif_spec_object_type import SpecAttributeDefinition
from reqif.models.reqif_types import SpecObjectAttributeType
from reqif.models.reqif_spec_object import SpecObjectAttribute

from json2reqif.helpers.spec_datatypes import SpecDataTypesHelper

def buildAttribute(attr: SpecAttributeDefinition, val: str, data_types_helper: SpecDataTypesHelper):
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
        enum_type = data_types_helper.data_typed_by_id[attr.datatype_definition]
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