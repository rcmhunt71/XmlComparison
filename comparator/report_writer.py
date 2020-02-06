import typing

from models.urla_xml_model import UrlaXML
from comparator.report_builder import ComparisonReportEngine
from logger.logging import Logger
from utils.file_utils import FileNameOps


log = Logger()


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
        html_file = FileNameOps.create_filename(primary_filename=self.src.data_file_name,
                                                basis_filename=self.cmp.data_file_name,
                                                ext=f'{tag_name}.html', unique=True)

        # Instantiate report generator and generate result tables
        result_tables = [self.report_engine.comparison_summary(results=results_dict),
                         self.report_engine.closest_match_info(results=results_dict)]
        result_table_str = ['Exact and Best Matches for "{tag_name}"\n{table}\n\n',
                            'Closest Element Match for "{tag_name}"\n{table}\n\n']

        # Write results to the logfile
        for index, (report, report_title) in enumerate(zip(result_tables, result_table_str)):
            log.info(report_title.format(tag_name=tag_name, table=report.get_string()))

            # Write the results to the report file
            with open(self.report_file, "a") as REPORT:
                REPORT.write(report_title.format(tag_name=tag_name, table=report.get_string()))

            # Generate HTML file if requested:
            if self.html:
                log.info(f"Generating HTML file ({html_file}) for '{tag_name}' comparison reports.\n")
                html_table = report.get_html_string()
                html_table = self._process_html_table(
                    html_table=html_table, table_title=report_title.format(tag_name=tag_name, table=""),
                    index=index, page_title="&lt{tag_name}&gt: Comparison Reports".format(tag_name=tag_name))

                with open(html_file, "a") as HTML:
                    HTML.write(html_table)
                    HTML.write("</br></br>")

    def build_sym_diff_reports(self, html: bool = False) -> typing.NoReturn:
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

        if html:
            html_file = FileNameOps.create_filename(
                primary_filename=self.src.data_file_name, basis_filename=self.cmp.data_file_name,
                ext=f'sym.html', unique=True)

            html_table = sym_diff_table.get_html_string()
            html_table = self._process_html_table(
                html_table=html_table, page_title="Symmetric Differences",
                table_title=f'Symmetrical Differences between "{self.src.data_file_name}" and '
                            f'"{self.cmp.data_file_name}"')

            with open(html_file, "a") as HTML:
                HTML.write(html_table)

    @staticmethod
    def _process_html_table(html_table: str, table_title: str, index: int = 0, font="Times New Roman",
                            page_title: str = "") -> str:
        """
        Updates the PrettyTable html to be easier to read (style, labelling, and color changes)

        :param html_table: (str) Table in HTML
        :param table_title: (str) Title of Table
        :param index: (int) Indicates first iteration of output (so title is only added once, if index == 0)
        :param font: (str) Specify the font to use in the table (default=Times New Roman)
        :param page_title: (str) Specify name of the page

        :return: (str) updated HTML

        """
        padding = 5
        color = "#00FF00"
        border = 1

        style = f"""
        <style>
        table, th, td {{
            font-family: {font};
            border: {border}px solid black;
            border-collapse: collapse;
        }}
        th, td {{
            padding: {padding}px
        }}
        th {{
            background-color: {color}
        }}
        </style>

        """

        # Only render the title once (index = 0). Subsequent calls should not add a page title.
        page_tab_title = f"<title>{page_title}</title>"
        page_title = f"<h1>{page_title}</h1></p>" if index == 0 else ""
        table_title = f"<h2>{table_title}</h2>"
        return f"{page_tab_title}\n{page_title}\n{table_title}{style}{html_table}"
