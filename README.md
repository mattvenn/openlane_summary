# OpenLANE summary

After the [OpenLANE ASIC flow](https://github.com/efabless/openlane) has finished, you will have a useful final_report_summary.csv file.

There is a lot of data there, and a lot is not so useful. The file isn't readable on the command line so you have to open it with a spreadsheet program and then scroll to find the parts you're interested in.

    ./summary --design mydesign

This summary program prints:

* date of last run
* name of the design
* any fields that contain 'violation' or 'error'
* area in square microns

You will need the $OPENLANE_ROOT environment variable set to where your OpenLANE directory is.
