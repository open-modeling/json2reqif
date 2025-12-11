
from typing import Dict

from reqif.models.reqif_data_type import (
      ReqIFDataTypeDefinitionInteger,
      ReqIFDataTypeDefinitionString,
      ReqIFDataTypeDefinitionXHTML,
      ReqIFDataTypeDefinitionEnumeration,
      ReqIFEnumValue
)

from json2reqif.helpers import (
    _gen_id,
    _get_timestamp
)

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
            identifier  = _gen_id("DTD", type),
            long_name   = type,
            last_change = _get_timestamp(),
            min_value   = rest.min or "0",
            max_value   = rest.max or "65535"
        )

    def createStringType(self, subType: str, rest):
        type = f"STRING_{subType}"
        return ReqIFDataTypeDefinitionString(
            identifier  = _gen_id("DTD", type),
            long_name   = type,
            last_change = _get_timestamp(),
            max_length  = rest.maxLength or "255",
        )
    
    def createXhtmlType (self, subType: str, rest):
        type = f"XHTML_{subType}" if subType else "XHTML"
        return ReqIFDataTypeDefinitionXHTML(
            identifier  = _gen_id("DTD", type),
            long_name   = type,
            last_change = _get_timestamp(),
        )

    def createEnumType (self, subType: str, rest):
        type = f"ENUM_{subType}"
        vals = []
        for val in rest.values:
            vals.append(ReqIFEnumValue(
                identifier    = _gen_id("EV", val.value),
                last_change   = _get_timestamp(),       
                key           = str(val.key),
                long_name     = val.value,
                other_content = val.content,
            ))

        return ReqIFDataTypeDefinitionEnumeration(
            identifier  = _gen_id("DTD", type),
            long_name   = type,
            last_change = _get_timestamp(),
            values      = vals
        )