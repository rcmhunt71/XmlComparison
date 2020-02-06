import argparse
import json
import os
import pprint
import typing

from comparator.comparison_engine import ComparisonEngine
from comparator.reporter import ComparisonReportEngine
from logger.logging import Logger
from models.urla_xml_model import UrlaXML

log = Logger()

# TODO: Rename all source/comparison references (method and var names) to primary/basis.


class CLIArgs:
    """
    CLI Arguments available for this application.
    See _defined_args for list and description of the available arguments
    """

    def __init__(self) -> typing.NoReturn:
        self.parser = argparse.ArgumentParser()
        self._defined_args()
        self.args = self.parser.parse_args()

    def _defined_args(self) -> typing.NoReturn:
        self.parser.add_argument(
            "-p", "--primary", required=True,
            help="Primary XML file to be compared to other MISMO formatted XML files")
        self.parser.add_argument(
            "-b", "--basis", required=True,
            help="MISMO formatted XML file used as a basis or 'source of truth' to verify against the primary XML file")
        self.parser.add_argument(
            "-o", "--outfile", action="store_true",
            help="[OPTIONAL] Create outfile of XML to dict conversion processes (for debugging)")
        self.parser.add_argument(
            "-d", "--debug", action="store_true",
            help="[OPTIONAL] Enable debug logging.")
        self.parser.add_argument(
            "-w", "--html", action="store_true",
            help="[OPTIONAL] Generate HTML (web) versions of the report")


class FileNameOps:

    @staticmethod
    def build_filename(target_dir: str, input_fname: str, ext: str) -> str:
        """
        Builds the out file name, based on desired directory and extension, using the filename of the input file
        (minus the file extension)

        :param target_dir: (str) relative path to the directory to write the file
        :param input_fname: (str) name of input file
        :param ext: (str) file extension to append to the out file

        :return: (str) full absolute-path file spec

        """
        # Get the input filename, minus any file path (/this/direct/file.ext --> file.ext)
        input_fname = input_fname.split(os.path.sep)[-1]

        # Get the input filename, minus the extension, and append the provided extension.
        input_fname = f"{'.'.join(input_fname.split('.')[:-1])}.{ext}"

        # Build the complete file spec and return as an absolute path
        return os.path.abspath(os.path.sep.join(['.', target_dir, input_fname]))

    @staticmethod
    def build_filespec(src: str, dst: str, target_dir: str = '.', ext: str = "log", html: bool = False) -> str:
        """
        Builds the dir+name by combining the source file names (no ext) and adding a log file extension.
        :param src: Source XML file
        :param dst: Comparison XML file
        :param target_dir: directory to write file (relative or absolute directory path)
        :param ext: file extension - default: "log"
        :param html: (bool) - Build HTML filename

        :return: new file spec
        """
        extension = "html" if html else ext
        src_portion = ".".join(src.split(os.path.sep)[-1].split(".")[:-1])
        dst_portion = ".".join(dst.split(os.path.sep)[-1].split(".")[:-1])

        return os.path.abspath(os.path.sep.join([target_dir, f"comp_{src_portion}_{dst_portion}.{extension}"]))

    @classmethod
    def create_filename(cls, primary_filename, basis_filename, ext="rpt", target_dir=".", unique=True):
        """
        Create the requested filespec, and if the file exists, delete it (in the case where a filehandle needs to open
        in append mode, but it should be an empty file to start.

        :param primary_filename: Primary XML file
        :param basis_filename: Comparison XML file
        :param target_dir: directory to write file (relative or absolute directory path)
        :param ext: file extension - default: "rpt"
        :param unique: (bool) - If file already exists, delete

        :return: (str) filespec
        """
        target_filespec = cls.build_filespec(src=primary_filename, dst=basis_filename, ext=ext, target_dir=target_dir)
        if unique and os.path.exists(target_filespec):
            os.remove(target_filespec)
        return target_filespec


class ComparisonReports:
    def __init__(self, primary: UrlaXML, basis: UrlaXML, html: bool = False) -> typing.NoReturn:
        """
        The ComparisonReports Class defines and generates the various comparison reports, and also
        collects the necessary data sources for all reports, so the information only needs to be provided once
        and is available to all generated reports. (DRY Principle)

        :param primary: Primary UrlaXML model
        :param basis: Basis UrlaXML model
        :param html: (Bool) Generate HTML pages for each table?
        
        """
        self.src = primary
        self.cmp = basis
        self.html = html
        self.report_engine = ComparisonReportEngine(primary_model=self.src.model, basis_model=self.cmp.model)
        self.report_file = FileNameOps.create_filename(
            primary_filename=self.src.data_file_name, basis_filename=self.cmp.data_file_name, ext='rpt', unique=True)

    def generate_reports_per_tag(self, results_dict: typing.Dict[str, dict], tag_name: str) -> typing.NoReturn:
        """
        Builds the various results table from the results_dict. The tag_name is used to generate a table title.
        :param results_dict: Dictionary of results - generated and returned by the ComparisonEngine class
        :param tag_name: Name of XML tag that represents current comparison results

        :return: None
        """
        # Create the report filename and if it already exists, delete the file.
        html_file = FileNameOps.create_filename(primary_filename=cli.args.primary, basis_filename=cli.args.basis,
                                                ext=f'{tag_name}.html', unique=False)

        # Instantiate report generator and generate result tables
        result_tables = [self.report_engine.comparison_summary(results=results_dict),
                         self.report_engine.closest_match_info(results=results_dict)]
        result_table_str = ["*** Comparison Matches for {tag_name} ***\n{table}\n\n",
                            "Closest Element Match for {tag_name}:\n{table}\n\n"]

        # Write results to the logfile
        for report, report_title in zip(result_tables, result_table_str):
            log.info(report_title.format(tag_name=tag_name, table=report.get_string()))

            # Write the results to the report file
            with open(self.report_file, "a") as REPORT:
                REPORT.write(report_title.format(tag_name=tag_name, table=report.get_string()))

            # Generate HTML file if requested:
            if self.html:
                log.info(f"Generating HTML file ({html_file}) for '{tag}' comparison reports.\n")
                with open(html_file, "a") as HTML:
                    HTML.write(report.get_html_string())
                    HTML.write("</br></br>")

    def build_sym_diff_reports(self) -> typing.NoReturn:
        """
        Build a symmetrical difference table from the results. Symmetrical differences are elements that are only
        unique to one of the tables --> the element is NOT present in both tables.

        :return: None

        """
        sym_diff_table = self.report_engine.symmetrical_differences()
        sym_diff_table_str = (f"\n\nSymmetrical Difference Table:\n"
                              f"{sym_diff_table.get_string(title='Symmetrical Differences')}")

        # Write the symmetrical difference results to the logfile
        log.info(sym_diff_table_str)

        # Write the symmetrical difference results to the report file
        with open(self.report_file, "a") as RPT:
            RPT.write(sym_diff_table_str)

        if cli.args.html:
            html_file = FileNameOps.create_filename(
                primary_filename=cli.args.primary, basis_filename=cli.args.basis, ext=f'.sym.html', unique=True)

            with open(html_file, "a") as HTML:
                HTML.write(sym_diff_table.get_html_string())


class DebugXML:
    @staticmethod
    def write_debug_files(source_obj: UrlaXML, compare_obj: UrlaXML) -> typing.NoReturn:
        """
        Given the UrlaXML objs, write each objects's OrderedDict as a str (OrderedDict = output from
        converting XML to dict)

        :param source_obj: Source XML object
        :param compare_obj: Comparison XML object

        :return: None
        """
        # Outfile definition parameters
        outfile_dir, outfile_ext = ('outfiles', 'out')
        indent, width = (4, 180)

        # Build file spec (filename + path)
        out_primary_file_spec = FileNameOps.build_filename(
            target_dir=outfile_dir, input_fname=source_obj.source_file_name, ext=outfile_ext)
        out_compare_file_spec = FileNameOps.build_filename(
            target_dir=outfile_dir, input_fname=compare_obj.source_file_name, ext=outfile_ext)

        # Build output data structure (as string)
        primary_dict_info = pprint.pformat(json.dumps(source_obj.data), indent=indent, width=width, compact=False)
        compare_dict_info = pprint.pformat(json.dumps(compare_obj.data), indent=indent, width=width, compact=False)

        # Write to file
        source_obj.dump_data_to_file(outfile=out_primary_file_spec, data_dict=primary_dict_info)
        compare_obj.dump_data_to_file(outfile=out_compare_file_spec, data_dict=compare_dict_info)


if __name__ == '__main__':
    # Parse CLI args
    cli = CLIArgs()

    # Build logfile file spec and instantiate logger
    project = "XMLComparison"
    log_filename = FileNameOps.create_filename(primary_filename=cli.args.primary, basis_filename=cli.args.basis, ext='log')
    print(f"Logging to: {log_filename}.")
    log = Logger(default_level=Logger.DEBUG if cli.args.debug else Logger.INFO,
                 set_root=True, project=project, filename=log_filename)

    # Create URLA XML objects (read file, convert to nested OrderedDict structure)
    primary = UrlaXML(data_file_name=cli.args.primary, is_primary_source=True)
    basis = UrlaXML(data_file_name=cli.args.basis, is_primary_source=False)

    # Write debug files if requested
    if cli.args.outfile:
        DebugXML.write_debug_files(source_obj=primary, compare_obj=basis)

    # Instantiate comparison engine
    comp_eng = ComparisonEngine(primary=primary, comparison=basis)
    reporter = ComparisonReports(primary=primary, basis=basis, html=cli.args.html)
    # Do comparison on the following tags and generate result reports
    TAG_LIST = ["ASSET", "COLLATERAL", "EXPENSE", "LIABILITY", "LOAN", "PARTY"]
    for tag in TAG_LIST:
        results = comp_eng.compare(tag_name=tag)
        reporter.generate_reports_per_tag(results_dict=results, tag_name=tag)
    reporter.build_sym_diff_reports()
