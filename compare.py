import argparse
import json
import pprint
import typing

from comparator.comparison_engine import ComparisonEngine
from comparator.report_writer import ComparisonReports
from logger.logging import Logger
from models.urla_xml_model import UrlaXML
from utils.file_utils import FileNameOps


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
            help="[OPTIONAL] Enable debug logging")
        self.parser.add_argument(
            "-w", "--html", action="store_true",
            help="[OPTIONAL] Generate HTML (web) versions of the reports, one set of reports per tag")


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
            target_dir=outfile_dir, input_fname=source_obj.data_file_name, ext=outfile_ext)
        out_compare_file_spec = FileNameOps.build_filename(
            target_dir=outfile_dir, input_fname=compare_obj.data_file_name, ext=outfile_ext)

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
    log_filename = FileNameOps.create_filename(
        primary_filename=cli.args.primary, basis_filename=cli.args.basis, ext='log')
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

    # Do a comparison on the following tags and generate the result reports
    TAG_LIST = ["ASSET", "COLLATERAL", "EXPENSE", "LIABILITY", "LOAN", "PARTY"]
    for tag in TAG_LIST:
        results = comp_eng.compare(tag_name=tag)
        reporter.generate_reports_per_tag(results_dict=results, tag_name=tag)
    reporter.build_sym_diff_reports(html=cli.args.html)
