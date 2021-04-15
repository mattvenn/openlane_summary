#!/usr/bin/env python3

# Original version of this script forked from https://github.com/mattvenn/openlane_summary.
# Produces a simplified summary of all violations from
# $OPENLANE_ROOT/designs/<design>/runs/<date_time>/reports/final_summary_report.csv
# Use --run to specify the runs directory. Default is to use cvs from the newest <date_time>.

import argparse
import os
import glob
import csv
import sys
from shutil import which

def is_tool(name):
    return which(name) is not None

def check_path(path):
    if not os.path.exists(path):
        exit("file not found: %s" % path)
    return path

def summary_report(latest_run):

    summary_file = os.path.join(latest_run, 'reports', 'final_summary_report.csv')

    # print pertinent summary - only interested in errors atm
    try:
        with open(summary_file) as fh:
            summary = csv.DictReader(fh)
            for row in summary:
                for key, value in row.items():
                    if "violation" in key or "error" in key:
                        print("%30s : %20s" % (key, value))
                    if "AREA" in key:
                        area = float(value)
    except FileNotFoundError as e:
        exit("summary file not found - did the run fail?")

    print("area %d um^2" % (1e6 * area))

def drc_report(latest_run):
    # what drc is broken?
    drc_file = os.path.join(latest_run, 'logs', 'magic', 'magic.drc')
    last_drc = None
    drc_count = 0
    try:
        with open(drc_file) as drc:
            for line in drc.readlines():
                drc_count += 1
                if '(' in line:
                    if last_drc is not None:
                        print("* %s (%d)" % (last_drc, drc_count/4))
                    last_drc = line.strip()
                    drc_count = 0
    except FileNotFoundError as e:
        print("no DRC file found")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OpenLANE summary tool")
    # choose the design and interation
    parser.add_argument('--design', help="only run checks on specific design", action='store', required=True)
    parser.add_argument('--top', help="name of top module if not same as design", action='store')
    parser.add_argument('--run', help="choose a specific run. If not given use latest. If not arg, show a menu", action='store', default=0, nargs='?', type=int)

    # what to show
    parser.add_argument('--drc', help='show DRC report', action='store_const', const=True)
    parser.add_argument('--violations', help='show violations summary report', action='store_const', const=True)
    parser.add_argument('--synth', help='show post techmap synth', action='store_const', const=True)
    parser.add_argument('--yosys-report', help='show cell usage after yosys synth', action='store_const', const=True)

    # klayout for intermediate files
    parser.add_argument('--floorplan', help='show floorplan', action='store_const', const=True)
    parser.add_argument('--pdn', help='show PDN', action='store_const', const=True)
    parser.add_argument('--global-placement', help='show global placement PDN', action='store_const', const=True)
    parser.add_argument('--detailed-placement', help='show detailed placement', action='store_const', const=True)
    parser.add_argument('--final-gds', help='show final GDS', action='store_const', const=True)

    # GDS3D for 3d view
    parser.add_argument('--final-gds-3d', help='show final GDS in 3D', action='store_const', const=True)
  
    # show all standard cells
    parser.add_argument('--show-sky-all', help='show all standard cells', action='store_const', const=True)
    
    args = parser.parse_args()
    if not args.top:
        args.top = args.design 

    if not os.environ['OPENLANE_ROOT']:
        exit("pls set OPENLANE_ROOT to where your OpenLANE is installed")

    openlane_designs = os.path.join(os.environ['OPENLANE_ROOT'], 'designs')
    run_dir = os.path.join(openlane_designs, args.design, 'runs/*')
    list_of_files = glob.glob(run_dir)

    # what run to show?
    if args.run == 0:
        # use the latest
        print("using latest run:")
        latest_run = max(list_of_files, key=os.path.getctime)

    elif args.run is None:
        # UI for asking for which run to use
        run_index = 0
        for run in list_of_files:
            print("%2d: %s" % (run_index, os.path.basename(run)), end='')
            if(run_index == len(list_of_files)-1):
                print(" <default>")
            else:
                print()
            run_index += 1
        
        n = input("which run? <enter for default>: ")
        if n == '':
            n = len(list_of_files)-1 
        latest_run = list_of_files[int(n)]

    else:
        # use the given run
        print("using run %d:" % args.run)
        latest_run = list_of_files[args.run]

    print(latest_run)

    if args.violations:
        summary_report(latest_run)

    if args.drc:
        drc_report(latest_run)

    if args.synth:
        os.system("xdot %s" % os.path.join(latest_run, "tmp", "synthesis", "post_techmap.dot"))

    if args.yosys_report:
        os.system("cat %s" % os.path.join(latest_run, "reports", "synthesis", "1-yosys_4.stat.rpt"))

    if args.floorplan:
        path = os.path.join(latest_run, "results", "floorplan", args.top + ".floorplan.def")
        os.system("klayout -l klayout_def.xml %s" % path)

    if args.pdn:
        path = check_path(os.path.join(latest_run, "tmp", "floorplan", "7-pdn.def"))
        os.system("klayout -l klayout_def.xml %s" % path)

    if args.global_placement:
        path = check_path(os.path.join(latest_run, "tmp", "placement", "8-replace.def"))
        os.system("klayout -l klayout_def.xml %s" % path)

    if args.detailed_placement:
        path = check_path(os.path.join(latest_run, "results", "placement", args.top + ".placement.def"))
        os.system("klayout -l klayout_def.xml %s" % path)

    if args.final_gds:
        path = check_path(os.path.join(latest_run, "results", "magic", args.top + ".gds"))
        os.system("klayout -l klayout_gds.xml %s" % path)

    if args.final_gds_3d:
        if not is_tool('GDS3D'):
            exit("pls install GDS3D from https://github.com/trilomix/GDS3D")
        path = check_path(os.path.join(latest_run, "results", "magic", args.top + ".gds"))
        os.system("GDS3D -p sky130.txt -i %s" % path)

    if args.show_sky_all:
        if not os.environ['PDK_ROOT']:
            exit("pls set PDK_ROOT to where your PDK is installed")
        path = check_path(os.path.join(os.environ['PDK_ROOT'], "sky130A", "libs.ref", "sky130_fd_sc_hd", "gds", "sky130_fd_sc_hd.gds"))
        os.system("klayout -l klayout_gds.xml %s" % path)

