#!/usr/bin/env python3

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

def summary_report(run_path):
    summary_file = os.path.join(run_path, 'reports', 'final_summary_report.csv')

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
                    if "flow_status" in key:
                        status = value
    except FileNotFoundError as e:
        exit("summary file not found - did the run fail?")

    print("area %d um^2" % (1e6 * area))
    print("flow status: %s" % status)

def drc_report(run_path):
    # what drc is broken?
    drc_file = os.path.join(run_path, 'logs', 'magic', 'magic.drc')
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
    group = parser.add_mutually_exclusive_group(required=True)

    # either choose the design and interation
    group.add_argument('--design', help="only run checks on specific design", action='store')
    # or show standard cells
    group.add_argument('--show-sky130', help='show all standard cells', action='store_const', const=True)

    # optionally choose different name for top module and which run to use (default latest)
    parser.add_argument('--top', help="name of top module if not same as design", action='store')
    parser.add_argument('--run', help="choose a specific run. If not given use latest. If not arg, show a menu", action='store', default=-1, nargs='?', type=int)

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
    parser.add_argument('--gds', help='show final GDS', action='store_const', const=True)

    # GDS3D for 3d view
    parser.add_argument('--gds-3d', help='show final GDS in 3D', action='store_const', const=True)
    
    args = parser.parse_args()

    if not args.top:
        args.top = args.design 

    if not os.environ['OPENLANE_ROOT']:
        exit("pls set OPENLANE_ROOT to where your OpenLANE is installed")

    klayout_def = os.path.join(os.path.dirname(sys.argv[0]), 'klayout_def.xml')
    klayout_gds = os.path.join(os.path.dirname(sys.argv[0]), 'klayout_gds.xml')
    gds3d_tech  = os.path.join(os.path.dirname(sys.argv[0]), 'sky130.txt')

    # if showing off the sky130 cells
    if args.show_sky130:
        if not os.environ['PDK_ROOT']:
            exit("pls set PDK_ROOT to where your PDK is installed")
        path = check_path(os.path.join(os.environ['PDK_ROOT'], "sky130A", "libs.ref", "sky130_fd_sc_hd", "gds", "sky130_fd_sc_hd.gds"))
        os.system("klayout -l %s %s" % (klayout_gds, path))
        exit()

    # otherwise need to know where openlane and the designs are
    openlane_designs = os.path.join(os.environ['OPENLANE_ROOT'], 'designs')
    run_dir = os.path.join(openlane_designs, args.design, 'runs/*')
    list_of_files = glob.glob(run_dir)

    # what run to show?
    if args.run == -1:
        # default is to use the latest
        print("using latest run:")
        run_path = max(list_of_files, key=os.path.getctime)

    elif args.run is None:
        # UI for asking for which run to use
        for run_index, run in enumerate(list_of_files):
            print("\n%2d: %s" % (run_index, os.path.basename(run)), end='')
        print(" <default>\n")
        
        n = input("which run? <enter for default>: ") or run_index
        run_path = list_of_files[int(n)]

    else:
        # use the given run
        print("using run %d:" % args.run)
        run_path = list_of_files[args.run]

    print(run_path)

    if args.violations:
        summary_report(run_path)

    if args.drc:
        drc_report(run_path)

    if args.synth:
        os.system("xdot %s" % os.path.join(run_path, "tmp", "synthesis", "post_techmap.dot"))

    if args.yosys_report:
        os.system("cat %s" % os.path.join(run_path, "reports", "synthesis", "1-yosys_4.stat.rpt"))

    if args.floorplan:
        path = os.path.join(run_path, "results", "floorplan", args.top + ".floorplan.def")
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.pdn:
        path = check_path(os.path.join(run_path, "tmp", "floorplan", "7-pdn.def"))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.global_placement:
        path = check_path(os.path.join(run_path, "tmp", "placement", "8-replace.def"))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.detailed_placement:
        path = check_path(os.path.join(run_path, "results", "placement", args.top + ".placement.def"))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.gds:
        path = check_path(os.path.join(run_path, "results", "magic", args.top + ".gds"))
        os.system("klayout -l %s %s" % (klayout_gds, path))

    if args.gds_3d:
        if not is_tool('GDS3D'):
            exit("pls install GDS3D from https://github.com/trilomix/GDS3D")
        path = check_path(os.path.join(run_path, "results", "magic", args.top + ".gds"))
        os.system("GDS3D -p %s -i %s" % (gds3d_tech, path))
