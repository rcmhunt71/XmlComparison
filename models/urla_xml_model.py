from collections import OrderedDict
import os
import typing

import xmltodict
from models.element_base_model import BaseElement


class UrlaXML:
    """

    This class reads and converts the MISMO v3.4 XML into a complex, nested python data structure. It removes the need
    to process the XML, and allows the user to quickly access the various data elements within the XML.

    """
    def __init__(self, source_file_name: str, primary_source: bool = False) -> typing.NoReturn:
        self.source_file_name = source_file_name
        self.primary_source = primary_source
        self.data = self.convert_xml_to_dict(source_file_name)
        self.model = BaseElement(data=self.data)

    def read_file(self, filename: str) -> typing.List[str]:
        """
        Read the specified file and return the contents as a list of lines.
        :param filename: Name (& diirectory) of target file
        :return: List of strings (file content, per line)
        """
        file_type = "primary" if self.primary_source else "comparison"
        print(f"Reading {file_type} file: '{os.path.abspath(filename)}'")
        with open(filename, "r") as FILE:
            return FILE.readlines()

    def convert_xml_to_dict(self, file_spec: str) -> OrderedDict:
        """
        Reads XML and converts the contents to a nested collections.OrderedDict
        :param file_spec: filespec of the input XML file.
        :return: OrderedDict representation of the XML.
        """
        if not os.path.exists(file_spec):
            raise FileNotFoundError(f"XML Source file ('{file_spec}') was not found.")

        file_contents = self.read_file(file_spec)
        return xmltodict.parse("\n".join(file_contents))

    @staticmethod
    def dump_data_to_file(outfile: str, data_dict: OrderedDict) -> typing.NoReturn:
        """
        Write the OrderedDict to file (as a string)
        :param outfile: file spec of the file to dump contents
        :param data_dict: OrderedDict to write to file
        :return: None
        """
        with open(outfile, "w") as OUT:
            OUT.writelines(data_dict)
        print(f"Wrote to OUTFILE: {outfile} --> Created Successfully? {os.path.exists(outfile)}")
