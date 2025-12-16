"""
JSON to ReqIF Converter - cli
"""

import json
import sys

from json2reqif import convert
from json2reqif._types import ReqIFMappingSchema
from json2reqif.helpers import ExitCodes, loadConfigOrExit, loadOrExit

def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("Usage: python json2reqif <input.json> <output.reqif> [config.json]")
        print()
        print("Arguments:")
        print("  input.json    - JSON file to convert")
        print("  output.reqif  - Output ReqIF file")
        print("  config.yaml   - Mapping configuration (default: mapping_config.json)")
        return ExitCodes.CommandLine

    try:
        json_path = sys.argv[1]
        output_path = sys.argv[2]
        config_path = len(sys.argv) > 3 and sys.argv[3] or "mapping_config.json"

        # Validate input files exist
        print("[Init] Loading JSON...")

        input = json.loads(loadOrExit(json_path,   "Input"))
        config: ReqIFMappingSchema = loadConfigOrExit(config_path)

        print("="*70)
        print("JSON TO REQIF CONVERTER")
        print("="*70)

        if input:
            print(f"      ✓ JSON loaded")
        else:
            print(f"         JSON load failed")
            return ExitCodes.Fail

        convert(input, config, output_path)
        
        print("\n" + "="*70)
        print("✓ CONVERSION COMPLETE")
        print("="*70)

        return ExitCodes.OK

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return ExitCodes.Fail
