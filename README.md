# XmlComparison
Compares a "primary" XML file against a basis (source of truth) XML and reports exact matches, best match (+ detailed report), and symmetrical differences (tags in one file that are not present in the other file).


**NOTE**: More documentation will be added later. The documentation included below should be enough to get users started.

## Usage:
* To see the available options:

       python compare.py --help 

    Minimum required options:

         python compare.py --primary <file_to_be_checked.xml> --basis <source_of_truth.xml>

* To generate HTML output, also add `--html` option:

       python compare.py --primary <file_to_be_checked.xml> --basis <source_of_truth.xml> --html

    This option will generate an html file **per XML tag** analyzed.

## Reporting
All output, including debug logging if enabled, will be logged and recorded in a text file:

     <file_to_be_checked>_<source_of_truth>.log
     
**RPT** files are also generated; these are text files with only the result tables.

     <file_to_be_checked>_<source_of_truth>.rpt

## Debugging
To **enable** debug logging:

     WINDOWS:    set DEBUG=1
     LINUX/BASH: export DEBUG=1
     
and execute.

To **disable** debug logging:

      WINDOWS:    set DEBUG=
      LINUX/BASH: unset DEBUG
