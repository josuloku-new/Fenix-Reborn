"""Command-line equivalent of the assistant's portable build workflow."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'launcher'))
from backend import Backend

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare-tools',action='store_true')
    parser.add_argument('--accept-tool-licenses',action='store_true')
    args=parser.parse_args();backend=Backend(Path(__file__).resolve().parents[1])
    if args.prepare_tools:
        if not args.accept_tool_licenses:raise SystemExit('Read Microsoft tool terms before using --accept-tool-licenses.')
        backend.dependencies()
    else:backend.build()
if __name__=='__main__':main()
