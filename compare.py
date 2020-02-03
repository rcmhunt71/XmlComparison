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
            help="[OPTIONAL] Enable debug logging."
        )


def _build_out_filename(target_dir: str, input_fname: str, ext: str) -> str:
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


def write_debug_files(source_obj: UrlaXML, compare_obj: UrlaXML) -> typing.NoReturn:
    """
    Given the UrlaXML objs, write each objects's OrderedDict as a str (OrderedDict = output from converting XML to dict)

    :param source_obj: Source XML object
    :param compare_obj: Comparison XML object

    :return: None

    """
    # Outfile definition parameters
    outfile_dir, outfile_ext = ('outfiles', 'out')
    indent, width = (4, 180)

    # Build file spec (filename + path)
    out_primary_file_spec = _build_out_filename(
        target_dir=outfile_dir, input_fname=source_obj.source_file_name, ext=outfile_ext)
    out_compare_file_spec = _build_out_filename(
        target_dir=outfile_dir, input_fname=compare_obj.source_file_name, ext=outfile_ext)

    # Build output data structure (as string)
    primary_dict_info = pprint.pformat(json.dumps(source_obj.data), indent=indent, width=width, compact=False)
    compare_dict_info = pprint.pformat(json.dumps(compare_obj.data), indent=indent, width=width, compact=False)

    # Write to file
    source_obj.dump_data_to_file(outfile=out_primary_file_spec, data_dict=primary_dict_info)
    compare_obj.dump_data_to_file(outfile=out_compare_file_spec, data_dict=compare_dict_info)


def build_log_filespec(src: str, dst: str, target_dir='.') -> str:
    """
    Builds the logfile dir+name by combining the source file names (no ext) and adding a log file extension.
    :param src: Source XML file
    :param dst: Comparison XML file
    :param target_dir: directory to write file (relative or absolute directory path)

    :return: new log file spec
    """
    extension = "log"
    src_portion = ".".join(src.split(os.path.sep)[-1].split(".")[:-1])
    dst_portion = ".".join(dst.split(os.path.sep)[-1].split(".")[:-1])

    return os.path.abspath(os.path.sep.join([target_dir, f"comp_{src_portion}_{dst_portion}.{extension}"]))


if __name__ == '__main__':

    # Parse CLI args
    cli = CLIArgs()

    # Build logfile file spec and instantiate logger
    log_filename = build_log_filespec(src=cli.args.primary, dst=cli.args.basis)
    print(f"Logging to: {log_filename}.")
    log = Logger(default_level=Logger.DEBUG if cli.args.debug else Logger.INFO,
                 set_root=True, project="FiServ", filename=log_filename)

    # Create URLA XML objects (read file, convert to nested OrderedDict structure)
    primary = UrlaXML(source_file_name=cli.args.primary, primary_source=True)
    basis = UrlaXML(source_file_name=cli.args.basis, primary_source=False)

    # Write debug files if requested
    if cli.args.outfile:
        write_debug_files(source_obj=primary, compare_obj=basis)

    # Instantiate report generator
    reports = ComparisonReportEngine(src_model=primary.model, cmp_model=basis.model)

    # Instantiate comparison engine
    comp_eng = ComparisonEngine(primary=primary, comparison=basis)

    # Do comparison on the following tags and generate result reports
    TAG_LIST = ["ASSET", "COLLATERAL", "EXPENSE", "LIABILITY", "LOAN", "PARTY"]
    for tag in TAG_LIST:
        results = comp_eng.compare(tag_name=tag)
        log.info(reports.comparison_summary(title=f"*** ELEMENT TAG: <{tag}> ***", results=results))
        log.info(reports.closest_match_info(results=results))
    log.info(f"\n{reports.symmetrical_differences()}\n")
