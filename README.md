# JSON2ReqIF
Tool for conversion of arbitrary json into correct ReqIF file.

It was primarily developed to convert requirenents from the tools with broken or missing ReqIF support to Capella.

## Features
* uses JSONSchema for the schema definition
* uses jsonpath-ng for the data matching and processing
* supports DOORS/Capella mapping
* supports embedded images
* provides correct ReqIF passing validation
* operates as a commandline tool

## To be done
* support for the relations/links
* better jsonpath processing
* split commandline interface from library
* improve performance

## How to use

1. clone this repo
2. study samples folder
3. study supplied scripts
4. modify mapping

## License

`json2reqif` is distributed under the terms of the [EP-2.0L](https://www.eclipse.org/legal/epl-2.0/) license.