"""Verify complete clean class repeats without excluding or relabeling originals."""
from argparse import ArgumentParser
import json
from pathlib import Path
from artifact_measurement_support import verify_machine_repeats


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--original',type=Path,required=True)
    parser.add_argument('--repeat',action='append',default=[],help='class=receipt.json, repeat for each affected class')
    args=parser.parse_args();original=json.loads(args.original.read_text(encoding='utf-8'));repeats={}
    for value in args.repeat:
        name,separator,path=value.partition('=')
        if not separator:parser.error('--repeat requires class=path')
        if name in repeats:parser.error('Duplicate repeat class')
        repeats[name]=json.loads(Path(path).read_text(encoding='utf-8'))
    result=verify_machine_repeats(original,repeats)
    result['original_receipt']=str(args.original);result['repeat_receipts']=args.repeat
    print(json.dumps(result,indent=2))
    return 0 if result['machine_attributed_repeat_policy_satisfied'] else 1


if __name__=='__main__':raise SystemExit(main())
