import pprint
import typing

from logger import logging
from models.element_base_model import BaseElement
from models.urla_xml_model import UrlaXML

log = logging.Logger()


class ComparisonEngine:
    MATCH = "Match"
    CLOSEST_MATCH_COUNT = "ClosestMatchCount"
    CLOSEST_OBJ = "ClosestObj"
    SRC_OBJ = 'SrcObj'
    CMP_OBJ = 'CmpObj'
    TOTAL = 'Total'
    HEADER_LENGTH = 120

    def __init__(self, primary: UrlaXML, comparison: UrlaXML) -> typing.NoReturn:
        """
        Instantiate the Comparison Engine

        :param primary: Primary Model (model that should be correct)
        :param comparison: Source of Truth (compare primary to this and report results)

        """
        self.primary = primary
        self.comparison = comparison

    def compare(self, tag_name: str) -> typing.Dict[str, dict]:
        """
        Compare the source/comparison models for the provided tag

        :param tag_name: XML tag (+ descendants) to compare.

        :return: Results dictionary: for each tag of type 'tag_name' found, indicate if there was an exact match,
                 a close match (and how close), and links to current and corresponding XML node BaseElement models.
        """
        # If the tag is not found in the primary model, there is nothing to do.
        if tag_name not in self.primary.model.path_dict.keys():
            log.error(f"ERROR: Element '{tag_name}' not found in the primary model. Available elements:")
            log.error(sorted(list(self.primary.model.path_dict.keys())))
            return {}

        # Log the "boxed" tag section header to record what is being evaluated.
        log.info(self._build_log_header(f"Comparing element: '{tag_name}'"))

        # Get the target nodes from each XML file
        log.debug(f"Getting SRC NODES")
        src_nodes = self.get_elements(element_name=tag_name, root=self.primary.model)
        log.debug(f"Getting CMP NODES")
        cmp_nodes = self.get_elements(element_name=tag_name, root=self.comparison.model)

        # Do analysis and return results
        return self._compare_element_lists(source_list=src_nodes, compare_list=cmp_nodes)

    def _compare_element_lists(self, source_list: typing.List[BaseElement],
                               compare_list: typing.List[BaseElement]) -> typing.Dict[str, dict]:
        """
        Given two nodes (one from each source), comnpare the node attributes and children to find the matches and
        provide closest matches.

        :param source_list: List of nodes to compare and verify
        :param compare_list: List of nodes to compare (source of truth)

        :return: dictionary of: key=src node xpaths, value={dict of source data, match data, and nearest match)

        """
        log.debug(f"SRC NODES: {[x.xpath_str for x in source_list]}")
        log.debug(f"CMP NODES: {[x.xpath_str for x in compare_list]}")

        # Define the result tracking structure (for each element with the target tag)
        # Key: The XPATH for each target
        # Values: SRC = complete source structure underneath the target
        #         MATCH: Matching Node
        results_dict = dict(
            [(src.xpath_str, {self.SRC_OBJ: src,
                              self.MATCH: None,
                              self.CLOSEST_MATCH_COUNT: 0,
                              self.TOTAL: 0,
                              self.CLOSEST_OBJ: None}) for src in source_list])
        cmp_match_found = []

        for src_node in source_list:
            log.debug(f"SOURCE NODE XPATH: {src_node.xpath_str}")

            for cmp_node in compare_list:
                log.debug(f"COMPARISON NODE XPATH: {cmp_node.xpath_str}")

                # Don't compare this comparison node if the comparison node has already been matched.
                if cmp_node.xpath_str in cmp_match_found:
                    log.debug(f"COMPARISON NODE ({cmp_node.xpath_str}) ALREADY MATCHED.")
                    continue

                # If the src node matches current cmp node, then compare elements (including children)
                # Match = data elements match + same number of children
                if self._compare_node(src_node=src_node, cmp_node=cmp_node):
                    log.debug(f"CMP node matches (attr + #_child): {cmp_node.xpath_str} -> Checking descendants...")

                    # Get all descendant nodes (down to the leaf elements)
                    src_children = self.get_leaf_nodes(src_node)
                    cmp_children = self.get_leaf_nodes(cmp_node)

                    # For a detailed analyses, expand the data nodes to be separate XPATH entries
                    # By default, all data nodes are combined with the parent for quicker comparison of nodes
                    # with children and data, but in this case, it will provide a less accurate comparison.
                    src_child_set = self._expand_objpath_pathsets(children=src_children)
                    cmp_child_set = self._expand_objpath_pathsets(children=cmp_children)

                    log.debug(f"EXPANDED SOURCE OBJ_PATH SET:\n{pprint.pformat(src_child_set)}")
                    log.debug(f"EXPANDED COMPARISON OBJ_PATH SET:\n{pprint.pformat(cmp_child_set)}")

                    # Determine the total number of unique xpaths/traversal paths in this comparison
                    max_count = self._get_max_unique_count(set_1=src_child_set, set_2=cmp_child_set)

                    # Exact match
                    if src_child_set == cmp_child_set:
                        log.debug(f"**MATCH**: {src_node.xpath_str} and {cmp_node.xpath_str}")
                        results_dict[src_node.xpath_str][self.MATCH] = cmp_node
                        results_dict[src_node.xpath_str][self.CLOSEST_OBJ] = None
                        results_dict[src_node.xpath_str][self.CLOSEST_MATCH_COUNT] = -1
                        results_dict[src_node.xpath_str][self.TOTAL] = max_count
                        cmp_match_found.append(cmp_node.xpath_str)
                        break

                    # Check if this cmp node is the closest match compared to previous comparisons.
                    # If so, store the cmp_node (BaseElement), number of matches, + total number of compared elements.
                    else:
                        log.debug(f"DID NOT MATCH: {src_node.xpath_str} and {cmp_node.xpath_str}")

                        num_matches = len(src_child_set.intersection(cmp_child_set))
                        if num_matches > results_dict[src_node.xpath_str][self.CLOSEST_MATCH_COUNT]:
                            results_dict[src_node.xpath_str][self.CLOSEST_MATCH_COUNT] = num_matches
                            results_dict[src_node.xpath_str][self.CLOSEST_OBJ] = cmp_node
                            results_dict[src_node.xpath_str][self.TOTAL] = max_count

                # C0mp node did not match the source node (in format/size), so move to the next comp node.
                else:
                    log.debug("SRC node and CMP node did not match (attributes and number of children)")
                log.debug("")

        self._debug_print_results(results_dict)
        return results_dict

    @staticmethod
    def _get_max_unique_count(set_1: typing.Set[str], set_2: typing.Set[str]) -> int:
        """
        Get the unique tag xpath count. This requires looking at all obj_paths without the data values (which are
        stored as part of the obj_path)
        :param set_1: Set of obj_paths
        :param set_2: Set of obj_paths

        :return: Number of unique obj_paths contained between the two sets

        """

        def _build_value(entry_str):
            """
            Quick string processing routine (specific to singular BaseElement entity storage)
            :param entry_str: entity string (traversal_path|attribute_key:entity_value)

            :return: String of traversal_path|entity_key

            """
            path_segment, entity = entry_str.split(BaseElement.OBJ_PATH_DELIMITER)
            attr = entity.split(BaseElement.ENTRY_DELIMITER)[0]
            return BaseElement.OBJ_PATH_DELIMITER.join([path_segment, attr])

        # Accumulate all traversal_paths (without data value) down to each leaf node
        total_list = [_build_value(item) for item in set_1]
        total_list.extend([_build_value(item) for item in set_2])

        # Return the number of unique traversal_paths
        return len(set(total_list))

    @staticmethod
    def _expand_objpath_pathsets(children: typing.List[BaseElement]) -> typing.Set[str]:
        """
        BaseElement obj_paths contain the traversal_path and all leaf data:value nodes.
        For a better comparison, break the obj_path into individual traversal_path + single leaf
        data:value node entities.

        :param children: BaseElement child nodes of current parent

        :return: Set of unique traversal_path + single leaf data:value node entities.

        """
        final_list = []

        # Get list of all traversal_paths
        starting_list = [x.obj_path_str for x in children]

        # Break each traversal_path|[entity_key:value] into individual path|entity:value strings
        for path in starting_list:

            # If the traversal_path has attribute
            if BaseElement.OBJ_PATH_DELIMITER in path:
                parts = path.split(BaseElement.OBJ_PATH_DELIMITER)
                current_path = parts.pop(0)
                final_list.extend([BaseElement.OBJ_PATH_DELIMITER.join([current_path, entity]) for entity in parts])
            else:
                final_list.append(path)

        # Return all unique paths (as a set)
        return set(final_list)

    @classmethod
    def get_leaf_nodes(cls, node: BaseElement) -> typing.List[BaseElement]:
        """
        Gets all leaf nodes below the provided root node. (Leaf = node without children)
        :param node: Specific node to use to start checking for leaf nodes (self + descendants)
        :return: List of leaf nodes (List of BaseElements)

        """
        leaves = []
        if not node.children:
            leaves.append(node)
        else:
            for child in node.children:
                leaves.extend(cls.get_leaf_nodes(node=child))
        return leaves

    # -------------------------------------------------------------------------------------
    @staticmethod
    def _compare_node(src_node: BaseElement, cmp_node: BaseElement) -> bool:
        """
        Compare the attributes and the number of children. If they match, the nodes are considered equal.

        :param src_node: Source Node
        :param cmp_node: Comparisan Node

        :return: Bool: True = nodes match.
        """
        # Check if attributes (data) match and number/type of children
        attrs = sorted(src_node.attributes) == sorted(cmp_node.attributes)
        child_types = (sorted([child.type for child in src_node.children]) ==
                       sorted([child.type for child in cmp_node.children]))

        return attrs & child_types

    def get_elements(self, element_name: str, root: BaseElement) -> typing.List[BaseElement]:
        """
        Get the child elements of the element_name using the relative "root" node

        :param element_name: Name of element tag to to find
        :param root: relative starting node

        :return: List of nodes underneath the relative root

        """
        # Get the XPATH tag list that corresponds to the final destination tag name
        paths = root.path_dict[element_name]

        log.debug(f"List of XPath(s) to '{element_name}': {paths}")

        results = []
        for path in paths:
            results.extend(self._get_elements(path=path.split(root.XPATH_DELIMITER), starting_node=root))
        log.debug(f"RESULTS: {[x.xpath_str for x in results]}")
        return results

    def _get_elements(self, starting_node: BaseElement, path: typing.List[str]) -> typing.List[BaseElement]:
        """
        Get the element(s) under the specified path (through recursive calls --> depth first strategy)

        :param starting_node: Node (relative root) used to start the retrieval process
        :param path: List of node types required to create the path to the target node:
                if the path = TAG1/TAG2/TAG3/TAG4, the path will be [TAG1, TAG2, TAG3, TAG4]

        :return: List of Elements

        """
        results = []
        current_type = path[0]
        extra_debugging = False

        if extra_debugging:
            log.debug(f"Rec'd Path: {path}")
            log.debug(f"Rec'd Starting Node: {starting_node.type} --> '{starting_node.name}'")
            log.debug(f"Current Type to look for: {current_type}\n")

        # Get all child nodes that match the requested type
        matching_child_nodes = starting_node.get_children_by_type(child_type=current_type)

        # If the current matching node type matches the desired type and there are no more nodes in the path,
        # save the node
        if matching_child_nodes:

            # If there are no more nodes to traverse beyond the current node, return
            if len(path) == 1:

                log.debug(f"Node type ({starting_node.type}) has children of current type ({current_type}) "
                          f"and path has single element ({path}).\nReturning matching child nodes: "
                          f"{[x.xpath_str for x in matching_child_nodes]}\n")

                return matching_child_nodes

            new_path = path[1:]                      # Advance to the next step
            for child_node in matching_child_nodes:  # Next set of nodes to evaluate
                results.extend(self._get_elements(path=new_path, starting_node=child_node))

        return results

    def _debug_print_results(self, results_dict: typing.Dict[str, dict]) -> typing.NoReturn:
        """
        Quick and easy display of result output
        :param results_dict: results dictionary

        :return: None
        """
        for xpath, data in results_dict.items():
            debug_msg = f"XPATH: {xpath} --> "
            if data[self.MATCH] is not None:
                debug_msg += f"{data[self.MATCH].xpath_str}"
            else:
                debug_msg += "None"
                if data[self.CLOSEST_OBJ] is not None:
                    debug_msg += (f"--> Closest Match: {data[self.CLOSEST_OBJ].xpath_str} with "
                                  f"{data[self.CLOSEST_MATCH_COUNT]} descendant(s) matching.")
            log.debug(debug_msg)

    def _build_log_header(self, tag: str) -> str:
        """
        Builds a header string centered around the provided text

        Example:
            +================+
            |     <tag>      |
            +================+

        :param tag: Name of tag (or text) to encase in a header
        :return: string of header (with embedded <cr>)

        """
        border_char = "-"
        border = border_char * self.HEADER_LENGTH

        header = "{{tag:^{entry_length}}}".format(entry_length=self.HEADER_LENGTH)
        header = header.format(tag=tag)
        return (f"+{border}+\n"
                f"|{header}|\n"
                f"+{border}+\n")
