#!/usr/bin/env python3
import argparse
import os
import math
import glob
import csv
import sys

openlane_designs = os.path.join(os.environ['OPENLANE_ROOT'], 'designs')

def report(design):
    run_dir = os.path.join(openlane_designs, design, 'runs/*')
    list_of_files = glob.glob(run_dir)
    latest_run = max(list_of_files, key=os.path.getctime)
    date = os.path.basename(latest_run)
    print("## %s : DESIGN=%s RUN_DATE=%s" % (design, design, date))
    print()

    summary_file = os.path.join(latest_run, 'reports', 'final_summary_report.csv')

    # print pertinent summary - only interested in errors atm
    with open(summary_file) as fh:
        summary = csv.DictReader(fh)
        for row in summary:
            for key, value in row.items():
                if "violation" in key or "error" in key:
                    print("%30s : %20s" % (key, value))
                if "AREA" in key:
                    area = float(value)
    
    print()
    print("area %d um^2" % (1e6 * area))
  
    # what drc is broken?
    print()
    drc_file = os.path.join(latest_run, 'logs', 'magic', 'magic.drc')
    last_drc = None
    drc_count = 0
    with open(drc_file) as drc:
        for line in drc.readlines():
            drc_count += 1
            if '(' in line:
                if last_drc is not None:
                    print("* %s (%d)" % (last_drc, drc_count/4))
                last_drc = line.strip()
                drc_count = 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="View Events")
    parser.add_argument('--design', help="only run checks on specific design", action='store', required=True)
    args = parser.parse_args()
    report(args.design)
    
