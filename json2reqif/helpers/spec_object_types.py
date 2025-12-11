from typing import Dict
from reqif.models.reqif_spec_object_type import (
    ReqIFSpecObjectType,
    SpecAttributeDefinition
)
from reqif.models.reqif_types import SpecObjectAttributeType

from json2reqif._types import ReqIFMappingRequirement
from json2reqif.helpers.spec_datatypes import SpecDataTypesHelper

from json2reqif.helpers import (
    _gen_id,
    _get_timestamp
)

class SpecObjectTypesHelper:
    '''Helper for the specification object types operations'''
    def __init__(self, object: ReqIFMappingRequirement, helper: SpecDataTypesHelper):
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
                    identifier          = _gen_id("AD", name),
                    attribute_type      = self._TYPES[val.attributeType],
                    datatype_definition = self.data_types_helper.createType(val.attributeType, val.type, val).identifier,
                    long_name           = val.longName,
                    ### Explicitly false, unless someone needs to implement multi choice
                    multi_valued        = False if val.attributeType == "ENUMERATION" else None,
                    last_change         = _get_timestamp()
                )

                self.spec_attrs[typeName][key] = attr

            specification = ReqIFSpecObjectType(
                identifier            = _gen_id('SOT', typeName),
                long_name             = typeName,
                last_change           = _get_timestamp(),
                attribute_definitions = [*self.spec_attrs[typeName].values()],
            )

            self.spec_types[typeName] = specification

    def getSpecType (self, specType) -> ReqIFSpecObjectType:
        """Retrieves or creates specification type based on its name"""

        return self.spec_types[specType]
    
    def getSpecAttrType (self, specType, attrName) -> SpecAttributeDefinition:
        """Retrieves or creates specification attrbiute type based on its name"""

        return self.spec_attrs[specType][attrName]
