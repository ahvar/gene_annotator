"""
Custom exceptions for ETL PIPELINE
"""


class GeneReaderException(Exception):
    """
    Thrown when GeneReader has a problem reading or processing gene or annotation data
    """


class GeneAnnotationException(GeneReaderException):
    """
    Thrown when GeneReader has a problem with annotation data
    """


class GeneDataException(GeneReaderException):
    """
    Thrown when GeneReader has a problem with gene data
    """
