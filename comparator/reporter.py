from collections import namedtuple
import typing

import prettytable

from comparator.comparison_engine import ComparisonEngine
from logger.logging import Logger

log = Logger()


class ComparisonReportEngine:

    # Table column headers
    ATTRIBUTE = "Attribute"
    BASIS = "Basis"
    BASIS_VALUE = "Base Value"
    CLOSEST = "Closest Match"
    DIFFERENCE = "Diff?"
    DIFFERENCES = "ELEMENT DIFFERENCES"
    EXACT = "Exact Match"
    PATH = "Path"
    PRIMARY = "Primary"
    PRIMARY_PATH = "Primary Path"
    PRIMARY_VALUE = "Primary Value"
    SOURCE = 'Source'
    TAG = "Tag"
    XPATH = "XPath"

    # Default Table Values
    DOES_NOT_MATCH = "X"
    EMPTY = ""
    NO_ENTRY = "--"

    # Column Alignment Constants
    LEFT = 'l'
    CENTER = 'c'
    RIGHT = 'r'

    # Named Tuple for column definition
    COLUMN_DEF = namedtuple('column', field_names=("name", "alignment"))

    def __init__(self, src_model, cmp_model, results=None) -> typing.NoReturn:
        """
        Initialize the reporting engine
        :param src_model: Source (absolute or relative root) BaseElement Model
        :param cmp_model: Comparison [source of truth] (absolute or relative root) BaseElement Model
        :param results: Result Dict from comparing the models (done by comparison_engine:ComparisonEngine)

        """
        self.src_model = src_model
        self.cmp_model = cmp_model
        self.results = results

    def symmetrical_differences(self) -> str:
        """
        Create a report of symmetrical ELEMENT (not attribute) differences between the data sets.
        (Symmetrical = found in one dataset, but not the other, irrespective if source or comparison)

        :return: String representation of tabular results

        """
        # Determine difference between models tags (list all tags only present in either model but not both)
        diff = set(list(self.src_model.path_dict)) ^ set(list(self.cmp_model.path_dict))

        # Instantiate table
        report = f"{self.DIFFERENCES}:"
        table = prettytable.PrettyTable()

        # Column name, order, and alignment
        setup = [self.COLUMN_DEF(self.SOURCE, self.CENTER),
                 self.COLUMN_DEF(self.TAG, self.CENTER),
                 self.COLUMN_DEF(self.PATH, self.LEFT)]
        table.field_names = [col.name for col in setup]
        for col in setup:
            table.align[col.name] = col.alignment

        # Build table
        for elem in sorted(diff):

            # Determine which dictionary had the current element (unique tag path)
            if elem in self.src_model.path_dict:
                row = [self.PRIMARY.upper(), elem,
                       '//' + self.src_model.XPATH_DELIMITER.join(self.src_model.path_dict[elem])]
            else:
                row = [self.BASIS.upper(), elem,
                       '//' + self.cmp_model.XPATH_DELIMITER.join(self.cmp_model.path_dict[elem])]

            table.add_row(row)
        return f"{report}\n{table.get_string()}"

    def comparison_summary(self, title: str, results=None) -> str:
        """
        Builds table of overall results (exact and closest matches)
        :param title: Title to prefix the table
        :param results: Results dictionary (defined in ComparisonEngine)

        :return: String representation of tabular results

        """
        results = results or self.results
        table = prettytable.PrettyTable()

        # Column name, order, and alignment
        setup = [self.COLUMN_DEF(self.PRIMARY_PATH, self.LEFT),
                 self.COLUMN_DEF(self.EXACT, self.LEFT),
                 self.COLUMN_DEF(self.CLOSEST, self.LEFT)]
        table.field_names = [x.name for x in setup]
        for col in setup:
            table.align[col.name] = col.alignment

        # if the results are a dictionary (should be!)
        if isinstance(results, dict):

            # For each result, determine match type and build a corresponding table row
            for xpath, data in results.items():

                # Default values (these will be overwritten depending on the match type)
                exact_match = self.NO_ENTRY
                closest_match = ''

                # Current result had an exact match
                if data[ComparisonEngine.MATCH] is not None:
                    exact_match = data[ComparisonEngine.MATCH].xpath_str

                # Current result is a partial (best effort) or no match
                else:
                    closest_match = None

                    # Partial match identified
                    if data[ComparisonEngine.CLOSEST_OBJ] is not None:
                        diff_val = abs(data[ComparisonEngine.TOTAL] - data[ComparisonEngine.CLOSEST_MATCH_COUNT])
                        closest_match = (f"{data[ComparisonEngine.CLOSEST_OBJ].xpath_str} "
                                         f"({data[ComparisonEngine.CLOSEST_MATCH_COUNT]}/{data[ComparisonEngine.TOTAL]}"
                                         f" matches; {diff_val} diffs)")
                # Build row
                table.add_row([xpath, exact_match, closest_match])

        return f"{title}\n{table.get_string()}"

    def closest_match_info(self, results: typing.Dict[str, dict] = None) -> str:
        """
        Generates element-by-element comparison of closest match to source element.
        :param results: Results Data dictionary (defined by comparison_engine._compare_element_lists())
        :return: String representation of tabular results

        """
        title = 'Closest Match Report'

        # Column name, order, and alignment
        columns = [
            self.COLUMN_DEF(self.PRIMARY_PATH, self.LEFT),
            self.COLUMN_DEF(self.CLOSEST, self.LEFT),
            self.COLUMN_DEF(self.TAG, self.LEFT),
            self.COLUMN_DEF(self.DIFFERENCE, self.CENTER),
            self.COLUMN_DEF(self.PRIMARY_VALUE, self.LEFT),
            self.COLUMN_DEF(self.BASIS_VALUE, self.LEFT),
        ]

        # Define table
        table = prettytable.PrettyTable()
        table.field_names = [col.name for col in columns]
        for col in columns:
            table.align[col.name] = col.alignment

        # Assess results
        results = results or self.results
        if results is not None:
            for xpath, data in results.items():

                # If there was an exact match or no potential match identified, go to the next result
                if data[ComparisonEngine.CLOSEST_MATCH_COUNT] <= 0:
                    continue

                # Go through the current result and build a dictionary that can be iterated though to
                # build the table row
                diff = self._build_differences(xpath, data)
                for src_xpath, src_data in diff.items():
                    for dst_xpath, dst_data in src_data.items():

                        # Each new XPATH will be listed on it's own row
                        table.add_row([src_xpath, dst_xpath, "", "", "", ""])

                        # Sort data by the XPATH value (which is the value[self.XPATH] of dict.items() key/value tuple)
                        for index, (attr, attr_data) in enumerate(
                                sorted(dst_data.items(), key=lambda key_value_tuple: key_value_tuple[1][self.XPATH])):

                            # Initial columns for current xpath leaf tag
                            row = ["", attr_data[self.XPATH], attr]

                            # Check if XPATH had a value in the source and comparison tables.
                            # If so, save to add to the row data.
                            src_value = (self.NO_ENTRY if attr_data[self.PRIMARY_VALUE] == "" else
                                         attr_data[self.PRIMARY_VALUE])
                            cmp_value = (self.NO_ENTRY if attr_data[self.BASIS_VALUE] == "" else
                                         attr_data[self.BASIS_VALUE])

                            # If the source and comparison values were different, denote this in the row data.
                            # Build row data with known information.
                            row.extend([self.DOES_NOT_MATCH if src_value != cmp_value else "", src_value, cmp_value])
                            table.add_row(row)

                    # After each comparison, add a blank line
                    table.add_row(["" for _ in range(len(columns))])

        return f"{title}\n{table.get_string()}"

    def _build_differences(self, src_xpath: str, data: typing.Dict[str, typing.Any]) -> typing.Dict[str, dict]:
        """
        Builds a dictionary of element data matching/storage (src_xpath, cmp_xpath, attribute, src_value, cmp_value)
        :param src_xpath: Path to start comparison
        :param data: Results data dictionary (see ComparisonEngine._compare_element_lists())
        :return: Dictionary of element data matching/storage

        """
        # Add element name to XPATH if available (xpath index 3 may have a name of ELEMENT_4)
        if data[ComparisonEngine.SRC_OBJ].name != data[ComparisonEngine.SRC_OBJ].VALUE_NOT_SET:
            src_xpath += f" (NAME: {data[ComparisonEngine.SRC_OBJ].name})"

        # Data dictionary
        diff_dict = {src_xpath: {}}

        # Get the two nodes to compare
        src = data[ComparisonEngine.SRC_OBJ]
        cmp = data[ComparisonEngine.CLOSEST_OBJ]

        # Get children of the nodes
        src_children = ComparisonEngine.get_leaf_nodes(src)
        cmp_children = ComparisonEngine.get_leaf_nodes(cmp)

        # Convert child data to sets for easy comparison
        src_child_set = set([x.obj_path_str for x in src_children])
        cmp_child_set = set([x.obj_path_str for x in cmp_children])

        # For all element identified...
        for attr_found in sorted(src_child_set.union(cmp_child_set)):

            # Spilt obj_path based on OBJ_PATH_DELIMITER: '|' --> traversal_path | attributes
            attr_xpath = attr_found.split(src.OBJ_PATH_DELIMITER)[0]
            for attr_num, entry in enumerate(attr_found.split(src.OBJ_PATH_DELIMITER)[1:]):

                # Determine the cmp_xpath (Add the tag name attribute since XPATH index != name/index)
                cmp_xpath = data[ComparisonEngine.CLOSEST_OBJ].xpath_str
                if data[ComparisonEngine.CLOSEST_OBJ].name != data[ComparisonEngine.CLOSEST_OBJ].VALUE_NOT_SET:
                    cmp_xpath += f" (NAME: {data[ComparisonEngine.CLOSEST_OBJ].name})"

                # Add cmp_xpath if not defined
                if cmp_xpath not in diff_dict[src_xpath]:
                    diff_dict[src_xpath][cmp_xpath] = {}

                # Split node attributes by ENTRY_DELIMITER: ':'
                cmp_attr_data = entry.split(src.ENTRY_DELIMITER)

                # If new leaf tag name, add to dict[src_xpath][cmp_xpath][new_attr] = {}
                leaf_tag_name = cmp_attr_data[0]
                if leaf_tag_name not in diff_dict[src_xpath][cmp_xpath]:
                    diff_dict[src_xpath][cmp_xpath][leaf_tag_name] = {
                        self.XPATH: attr_xpath,
                        self.PRIMARY_VALUE: self.NO_ENTRY,
                        self.BASIS_VALUE: self.NO_ENTRY}

                # If the current attribute difference is in the src set
                if attr_found in src_child_set:
                    diff_dict[src_xpath][cmp_xpath][leaf_tag_name][
                        self.PRIMARY_VALUE] = src.ENTRY_DELIMITER.join(cmp_attr_data[1:])

                # If the current attribute difference is in the cmp set
                if attr_found in cmp_child_set:
                    diff_dict[src_xpath][cmp_xpath][leaf_tag_name][
                        self.BASIS_VALUE] = src.ENTRY_DELIMITER.join(cmp_attr_data[1:])

        return diff_dict
