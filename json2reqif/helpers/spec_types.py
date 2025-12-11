from typing import Dict

from reqif.models.reqif_spec_object_type import SpecAttributeDefinition
from reqif.models.reqif_specification_type import ReqIFSpecificationType
from reqif.models.reqif_types import SpecObjectAttributeType

from json2reqif._types import ReqIFMappingSpecification
from json2reqif.helpers.spec_datatypes import SpecDataTypesHelper
from json2reqif.helpers import (
    _gen_id,
    _get_timestamp
)

class SpecTypesHelper:
    '''Helper for the specification types operations'''
    def __init__(self, spec: ReqIFMappingSpecification, helper: SpecDataTypesHelper):
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
                identifier          = _gen_id("SAD", key),
                last_change         = _get_timestamp(),
                attribute_type      = self._TYPES[val.attributeType],
                datatype_definition = self.data_types_helper.createType(val.attributeType, val.type, val).identifier,
                long_name           = val.longName,
            )

            self.spec_attrs[typeName][key] = attr

        specification = ReqIFSpecificationType(
            identifier      = _gen_id('ST', typeName),
            last_change     = _get_timestamp(),
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