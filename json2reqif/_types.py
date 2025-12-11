from typing import Union

from json2reqif.models import mapping, mapping_capella

'''Root schema for implemented ReqiIF mappings'''
ReqIFMappingSchema =        Union[mapping.ReqifChoiceSchema, mapping_capella.ReqifChoiceSchema]
ReqIFMappingSpecification = Union[mapping.Specification,     mapping_capella.Specification]
ReqIFMappingRequirement =   Union[mapping.Requirements,      mapping_capella.Requirements]
ReqIFMappingVariant =       Union[mapping.Variant,           mapping_capella.Variant]