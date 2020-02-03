from collections import OrderedDict
import typing

from models.urla_xml_keys import UrlaXmlKeys


class BaseElement:

    START = "MESSAGE"
    XPATH_DELIMITER = "/"
    VALUE_NOT_SET = 'NOT_SET'
    XPATH = VALUE_NOT_SET
    OBJ_TYPE = VALUE_NOT_SET
    OBJ_PATH_DELIMITER = "|"
    ENTRY_DELIMITER = ":"

    def __init__(self, data: OrderedDict, parent: typing.Optional["BaseElement"] = None,
                 element_type: str = None, index: int = None) -> typing.NoReturn:
        """
        Instantiate and populate BaseElement. A BaseElement is the basic building block of translating the
        OrderedDict results generated from XMLtoDict to an object model.

        :param data: OrderDict of XML (created from XmlToDict library)
        :param parent: This object's Parent BaseElement
        :param element_type: Provided type (key from child OrderedDict, value=data) or First Key in dict
                             (should be only key since it is the root)
        :param index: If element is in a list, index indicates this "data"'s position in the list

        """
        self.data = data
        self.parent = parent
        self.name = self.data.get(UrlaXmlKeys.XLINK_LABEL, self.VALUE_NOT_SET)
        self.type = element_type or list(data.keys())[0]
        self.index = index
        self.path_dict = None
        self.children = []

        # Collect attributes for this element
        # List of strings, each element = "<key>:<value>"
        self.attributes = self._get_element_data_attributes(data)

        # XPATH: Build the xpath to this element (same as traversal path, but contains indices when in a list)
        if parent is None:
            self.xpath = [self.XPATH_DELIMITER]
        else:
            self.xpath = parent.xpath.copy()
            elem_type = self.type if self.index is None else f"{self.type}[{self.index}]"
            self.xpath.append(elem_type)

        # TRAVERSAL_LIST: A traversal list is the XPATH **WITHOUT** the embedded element-index tracking
        # Instantiate the traversal list or copy the list from the parent and then append current element type
        if parent is None:
            self.traversal_list = []
        else:
            self.traversal_list = parent.traversal_list.copy()
            self.traversal_list.append(self.type)

        # OBJECT_PATH: Object_path is the same as the traversal path, but the object's attributes are included also.
        # This path is used for raw comparison of leaf nodes to help find matches between documents (source/compare)
        if parent is None:
            self.obj_path = []
        else:
            self.obj_path = parent.obj_path.copy()
            current_object = self.type
            if self.attributes:
                current_object += self.OBJ_PATH_DELIMITER + self.OBJ_PATH_DELIMITER.join(self.attributes)
            self.obj_path.append(current_object)

        # Marshall all child nodes into BaseElement objects
        self._deserialize_children()

        # Build dictionary of possible keys and corresponding paths (only done for root element)
        if parent is None:
            self.path_dict = self.build_element_paths_dict()

    @property
    def obj_path_str(self) -> str:
        """
        Build the obj_path list as a string (using the XPATH_DELIMITER)

        Example: Given the obj_path: [TAG_1, TAG_2, TAG_3, ..., TAG_N)
        Result: TAG_1/TAG_2/TAG_3/.../TAG_N

        :return: str value of list.
        """
        return self.XPATH_DELIMITER.join(self.obj_path)

    @property
    def xpath_str(self) -> str:
        """
        Build the xpath list as a string (using the XPATH_DELIMITER)

        Example: Given the xpath: [TAG_1, TAG_2, TAG_3, ..., TAG_N)
        Result: TAG_1/TAG_2/TAG_3/.../TAG_N

        :return: str value of list.
        """
        return self.XPATH_DELIMITER.join(self.xpath)

    @property
    def traversal_list_str(self) -> str:
        """
        Build the traversal_path list as a string (using the XPATH_DELIMITER)

        Example: Given the traversal_path: [TAG_1, TAG_2, TAG_3, ..., TAG_N)
        Result: TAG_1/TAG_2/TAG_3/.../TAG_N

        :return: str value of list.
        """
        return self.XPATH_DELIMITER.join(self.traversal_list)

    def get_children_by_type(self, child_type: str) -> typing.List["BaseElement"]:
        """
        Build a list of element children that match a specific type
        :param child_type: Type of child to accumulate

        :return: List of BaseElement (children) of the specified type
        """
        return [child for child in self.children if child.type == child_type]

    def _deserialize_children(self) -> typing.NoReturn:
        """
        Iterate through child elements, instantiating and storing child elements

        :return: None
        """
        for child_type, child_data in [(key, value) for key, value in self.data.items()]:

            # If ordered dictionary...
            if isinstance(child_data, OrderedDict):
                self.children.append(BaseElement(data=child_data, element_type=child_type, parent=self))

            # If list...
            elif isinstance(child_data, list):
                for index, child_element in enumerate(child_data):
                    self.children.append(
                        BaseElement(data=child_element, element_type=child_type, index=index, parent=self))

    @classmethod
    def _get_element_data_attributes(cls, data: OrderedDict) -> typing.List[str]:
        """
        Collect attributes (key prefixed with '@' character)
        :param data: OrderedDict of XML element
        :return: List of lexicographically sorted strings --> attribute_name:attribute_value

        """
        return sorted([f"{key}{cls.ENTRY_DELIMITER}{value}" for key, value in data.items() if
                       not key.startswith('@') and
                       not isinstance(value, OrderedDict) and
                       not isinstance(value, list)])

    def __str__(self, index: int = 0) -> str:
        """
        Representation of Object if cast to a string.
        :param index: Used to recurse child elements (not needed for initial call)
        :return: Str representation of obj

        """
        border_length = 120
        tabs = "\t" * index
        elem_idx = f"[{self.index}]" if self.index is not None else ""

        output = (f"{tabs}{'-' * border_length}\n"
                  f"{tabs}TYPE: {self.type}{elem_idx} --> NAME: {self.name}\n"
                  f"{tabs}xpath: {self.xpath_str}\n"
                  f"{tabs}TRAVERSAL LIST: {'-'.join(self.traversal_list)}\n"
                  f"{tabs}OBJECT_PATH: {'-'.join(self.obj_path)}\n"
                  f"{tabs}ATTRS: {','.join(self.attributes)}\n\n")

        output += ''.join([child.__str__(index + 1) for child in self.children])
        return output

    def build_element_paths_dict(self, paths: typing.List[str] = None) -> typing.Dict[str, typing.List[str]]:
        """
        Traverse data tree, recording the path to each unique element type

        :param paths: Dictionary of elements, value equals list of elements required to reach key element.
        :return: Dictionary of elements, value equals list of elements required to reach key element.

        """
        # If first value in the structure, initialize the path dictionary.
        if paths is None:
            paths = {self.type: [self.traversal_list_str]}

        # New element type... don't include the current element, which will be the last element in the list
        elif self.type not in paths:
            paths[self.type] = [self.traversal_list_str]

        elif self.type in paths:
            # Element type exists in the list, check if the current type is in the traversal list.
            # if not, append it to the list.
            if self.traversal_list_str not in paths[self.type]:
                paths[self.type].append(self.traversal_list_str)

        # Iterate through the children, gathering their paths
        for child in self.children:
            paths = child.build_element_paths_dict(paths=paths)

        return paths
