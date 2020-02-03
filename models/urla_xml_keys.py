from dataclasses import dataclass


@dataclass
class UrlaXmlKeys:
    """
    Abstraction of MISMO v3.4 XML keywords into CONSTANTS to be used throughout application.
    This prevents hard-coding within the application, and ability to change values globally in one place.
    """
    SEQ_NUM: str = '@SequenceNumber'
    XLINK_LABEL: str = '@xlink:label'
    LOAN_ROLE_TYPE: str = '@LoanRoleType'
