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
            "-a", "--actual", required=True,
            help="The 'actual' XML file to be compared to other MISMO formatted XML file (expected)")
        self.parser.add_argument(
            "-e", "--expected", required=True,
            help="MISMO formatted XML file used as the expected or 'source of truth' to verify against "
                 "the 'actual' XML file")
        self.parser.add_argument(
            "-o", "--outfile", action="store_true",
            help="[OPTIONAL] Create outfile of XML to dict conversion processes (for debugging)")
        self.parser.add_argument(
            "-t", "--tags", nargs="+", default=None,
            help="[OPTIONAL] Specific XML tags to analyze")
        self.parser.add_argument(
            "-d", "--debug", action="store_true",
            help="[OPTIONAL] Enable debug logging")
        self.parser.add_argument(
            "-w", "--html", action="store_true",
            help="[OPTIONAL] Generate HTML (web) versions of the reports, one set of reports per tag")


class DebugXML:
    @staticmethod
    def write_debug_files(actual_obj: UrlaXML, expected_obj: UrlaXML) -> typing.NoReturn:
        """
        Given the UrlaXML objs, write each objects's OrderedDict as a str (OrderedDict = output from
        converting XML to dict)

        :param actual_obj: Source (actual|generated) XML object
        :param expected_obj: Expected (correct|source of truth) XML object

        :return: None
        """
        # Outfile definition parameters
        outfile_dir, outfile_ext = ('outfiles', 'out')
        indent, width = (4, 180)

        # Build file spec (filename + path)
        out_actual_file_spec = FileNameOps.build_filename(
            target_dir=outfile_dir, input_fname=actual_obj.data_file_name, ext=outfile_ext)
        out_expected_file_spec = FileNameOps.build_filename(
            target_dir=outfile_dir, input_fname=expected_obj.data_file_name, ext=outfile_ext)

        # Build output data structure (as string)
        primary_dict_info = pprint.pformat(json.dumps(actual_obj.data), indent=indent, width=width, compact=False)
        compare_dict_info = pprint.pformat(json.dumps(expected_obj.data), indent=indent, width=width, compact=False)

        # Write to file
        actual_obj.dump_data_to_file(outfile=out_actual_file_spec, data_dict=primary_dict_info)
        expected_obj.dump_data_to_file(outfile=out_expected_file_spec, data_dict=compare_dict_info)


if __name__ == '__main__':
    # Parse CLI args
    cli = CLIArgs()

    # Build logfile file spec and instantiate logger
    project = "XMLComparison"
    log_filename = FileNameOps.create_filename(
        actual_xml_filename=cli.args.actual, expected_xml_filename=cli.args.expected, ext='log')
    print(f"Logging to: {log_filename}.")
    log = Logger(default_level=Logger.DEBUG if cli.args.debug else Logger.INFO,
                 set_root=True, project=project, filename=log_filename)

    # Create URLA XML objects (read file, convert to nested OrderedDict structure)
    actual = UrlaXML(data_file_name=cli.args.actual, is_primary_source=True)
    expected = UrlaXML(data_file_name=cli.args.expected, is_primary_source=False)

    # Write debug files if requested
    if cli.args.outfile:
        DebugXML.write_debug_files(actual_obj=actual, expected_obj=expected)

    # Instantiate comparison engine
    comp_eng = ComparisonEngine(actual=actual, expected=expected)
    reporter = ComparisonReports(actual_xml_model=actual, expected_xml_model=expected, html=cli.args.html)

    # Do a comparison on the following tags and generate the result reports
    tag_list = (cli.args.tags if cli.args.tags is not None else
                ["ASSET", "COLLATERAL", "EXPENSE", "LIABILITY", "LOAN", "PARTY"])

    for tag in tag_list:
        results = comp_eng.compare(tag_name=tag)
        reporter.generate_reports_per_tag(results_dict=results, tag_name=tag)
    reporter.build_sym_diff_reports(html=cli.args.html)
