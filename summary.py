#!/usr/bin/env python3

import argparse
import os
import glob
import csv
import sys
import re
from shutil import which, copyfile
import datetime

def is_tool(name):
    return which(name) is not None

def check_path(path):
    paths = glob.glob(path)
    if len(paths) == 0:
        exit("file not found: %s" % path)
    if len(paths) > 1:
        print("warning: glob pattern found too many files, using first one: %s" % paths[0])
    
    return paths[0]

def openlane_date_sort(e):
    datestamp = os.path.basename(e)
    if re.match(r'^RUN_\d+.\d+.\d+\_\d+\.\d+\.\d+$',datestamp):
        datestamp = datestamp.replace('RUN_', '')
        timestamp = datetime.datetime.strptime(datestamp, '%Y.%m.%d_%H.%M.%S')
        return timestamp.timestamp()

    elif re.match(r'^\d+\-\d+\_\d+\-\d+$',datestamp):
            timestamp = datetime.datetime.strptime(datestamp, '%d-%m_%H-%M')
            return timestamp.timestamp()

    return -1

def summary_report(summary_file):
    # print short summary of the csv file
    status = None
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

    print("area %d um^2" % (1e6 * area))
    if status is not None: # newer OpenLANE has status, older ones don't
        print("flow status: %s" % status)

def full_summary_report(summary_file):
    # print short summary of the csv file
    with open(summary_file) as fh:
        summary = csv.DictReader(fh)
        for row in summary:
            for key, value in row.items():
                print("%30s : %20s" % (key, value))
                    
def drc_report(drc_file):
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

def antenna_report(antenna_report):
    violations = 0
    with open(antenna_report) as ant:
        for line in ant.readlines():
            m = re.match(r'\s+(PAR|CAR):\s+(\d+.\d+)\*\s+Ratio:\s+(\d+.\d+)', line)
            if m is not None:
                violations += 1
                violation = float(m.group(2))
                ratio = float(m.group(3))
                if violation > (ratio * 2):
                    print(line.strip(), ": worth fixing")
                else:
                    print(line.strip(), ": can ignore")

    if violations > 0:
        print("for more info on antenna reports see https://www.zerotoasiccourse.com/terminology/antenna-report/")

def check_and_sort_regressions(regressions):
    summaries = {}
    for run_path in regressions:
        summary_file = os.path.join(run_path, "reports", "final_summary_report.csv")
        if not os.path.exists(summary_file):
            # print(f"run {os.path.basename(run_path)} summary file not found")
            continue
        with open(summary_file) as fh:
            summary = next(csv.DictReader(fh))
        if summary['flow_status'] != 'Flow_completed':
            # print(f"run {os.path.basename(run_path)} did not complete : {summary['flow_status']}")
            continue
        summaries[run_path] = summary
    violations = {rp: sum(int(v) for k, v in summary.items() if ('violations' in k or 'error' in k) and int(v) >= 0) for rp, summary in summaries.items()}
    for rp, n in violations.items():
        print(f"found regression run {os.path.basename(rp)} with {n} violations")
    return sorted(
        violations,
        key=lambda rp: violations[rp]
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="OpenLANE summary tool")
    group = parser.add_mutually_exclusive_group(required=True)

    # either choose the design and interation
    group.add_argument('--design', help="only run checks on specific design", action='store')
    # or show standard cells
    group.add_argument('--show-sky130', help='show all standard cells', action='store_const', const=True)

    # arguments for caravel or regression context
    parser.add_argument('--regression', help="look for a regression test output dir", action='store_const', const=True)
    parser.add_argument('--caravel', help='use caravel directory structure instead of standard openlane', action='store_const', const=True)

    # optionally choose different name for top module and which run to use (default latest)
    parser.add_argument('--top', help="name of top module if not same as design", action='store')
    parser.add_argument('--run', help="choose a specific run. If not given use latest. If not arg, show a menu", action='store', default=-1, nargs='?', type=int)

    # what to show
    parser.add_argument('--drc', help='show DRC report', action='store_const', const=True)
    parser.add_argument('--summary', help='show violations, area & status from summary report', action='store_const', const=True)
    parser.add_argument('--full-summary', help='show the full summary report csv file', action='store_const', const=True)
    parser.add_argument('--synth', help='show post techmap synth', action='store_const', const=True)
    parser.add_argument('--yosys-report', help='show cell usage after yosys synth', action='store_const', const=True)
    parser.add_argument('--antenna', help='find and list any antenna violations', action='store_const', const=True)

    # some useful things to do
    parser.add_argument('--copy-gds', help='copy gds, lef and powered verilog to the current working directory', action='store_const', const=True)

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

    if not 'OPENLANE_ROOT' in os.environ:
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
    openlane_designs = ''
    if args.caravel:
        if os.path.exists('openlane'):
            openlane_designs = 'openlane'
        else:
            openlane_designs = '.'
        run_dir = os.path.join(openlane_designs, args.design, 'runs/*')

    else:
        openlane_designs = os.path.join(os.environ['OPENLANE_ROOT'], 'designs')
        if args.regression:
            run_dir = os.path.join(openlane_designs, args.design, 'config_regression_*')
        else:
            run_dir = os.path.join(openlane_designs, args.design, 'runs', '*')

    print(run_dir)

    list_of_files = glob.glob(run_dir)
    if len(list_of_files) == 0:
        exit("couldn't find that design")
    if args.regression:
        print(f"found {len(list_of_files)} regression variants, sorting by number of violations")
        list_of_files = check_and_sort_regressions(list_of_files)
        if len(list_of_files) == 0:
            exit("no successful regression runs found")
        run_path = list_of_files[0]
    else:
        list_of_files.sort(key=openlane_date_sort)
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

    if args.summary:
        path = check_path(os.path.join(run_path, 'reports', 'final_summary_report.csv'))
        summary_report(path)

    if args.full_summary:
        path = check_path(os.path.join(run_path, 'reports', 'final_summary_report.csv'))
        full_summary_report(path)

    if args.drc:
        path = os.path.join(run_path, 'logs', 'magic', 'magic.drc') # don't check path because if DRC is clean, don't get the file
        if os.path.exists(path):
            drc_report(path)
        else:
            print("no DRC file, DRC clean?")

    if args.synth:
        path = check_path(os.path.join(run_path, "tmp", "synthesis", "post_techmap.dot")) # post_techmap is created by https://github.com/efabless/openlane/pull/282
        os.system("xdot %s" % path)

    if args.yosys_report:
        filename = "*synthesis*.stat.*"
        path = check_path(os.path.join(run_path, "reports", "synthesis", filename))
        os.system("cat %s" % path)

    if args.antenna:
        filename = "*antenna.rpt"
        path = check_path(os.path.join(run_path, "reports", "finishing", filename))
        if os.path.exists(path):
            antenna_report(path)
        else:
            print("no antenna file, did the run finish?")

    if args.floorplan:
        path = check_path(os.path.join(run_path, "results", "floorplan", args.top + ".def"))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.pdn:
        filename = "*pdn.def"
        path = check_path(os.path.join(run_path, "tmp", "floorplan", filename))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.global_placement:
        filename = "*global.def"
        path = check_path(os.path.join(run_path, "tmp", "placement", filename))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.detailed_placement:
        path = check_path(os.path.join(run_path, "results", "placement", args.top + ".placement.def"))
        os.system("klayout -l %s %s" % (klayout_def, path))

    if args.gds:
        path = check_path(os.path.join(run_path, "results", "final", "gds", args.top + ".gds"))
        os.system("klayout -l %s %s" % (klayout_gds, path))

    if args.copy_gds:
        path = check_path(os.path.join(run_path, "results", "final", "gds", args.top + ".gds"))
        copyfile(path, args.top + ".gds")
        path = check_path(os.path.join(run_path, "results", "final", "lef", args.top + ".lef"))
        copyfile(path, args.top + ".lef")
        path = check_path(os.path.join(run_path, "results", "final", "verilog", "gl", args.top + ".v"))
        copyfile(path, args.top + ".lvs.powered.v")
        # def more complicated
        path = check_path(os.path.join(run_path, "results", "routing", "*" + args.top + ".def"))
        path = glob.glob(path)[0]
        copyfile(path, args.top + ".def")
        # also take the pdk and openlane versions
        path = check_path(os.path.join(run_path, "OPENLANE_VERSION"))
        copyfile(path, "OPENLANE_VERSION")
        path = check_path(os.path.join(run_path, "PDK_SOURCES"))
        copyfile(path, "PDK_SOURCES")

    if args.gds_3d:
        if not is_tool('GDS3D'):
            exit("pls install GDS3D from https://github.com/trilomix/GDS3D")
        path = check_path(os.path.join(run_path, "results", "magic", args.top + ".gds"))
        os.system("GDS3D -p %s -i %s" % (gds3d_tech, path))
        
