"""
LoggingUtils.py

This file contains a class with utilities to facilitate consistent logging
patterns.
"""

import logging
import os
import getpass  # Used to get the username. Works on Windows and Linux.
import platform  # Used to get the hostname. Works on Windows and Linux.
import sys
from datetime import datetime, timedelta


class LogFileCreationError(Exception):
    """
    Exception raised for errors when creating the log file.

    Attributes:
        filespec -- the log filespec that was requested
    """

    def __init__(self, filespec):
        self.filespec = filespec


class LoggingUtils:
    """
    A utility class to provide consistent logging for applications.

    This class provides consistent formatting for logging information that is sent to the console or
    to a log file. It provides operations to log the start and finish of an application, writing
    header informnation.

    Usage
    -----
    1) Create an instance of the LoggingUtils, setting the parameters for your application:
            logging_utils = LoggingUtils("MyApp",
                                         logFile="myapp.log",
                                         fileLevel=logging.DEBUG,
                                         consoleLevel=logging.INFO)

    2) Call logApplicationStart() to put standard information in your log file about your application.

    3) Perform logging in your application using typical calls to the Python logging module:
            logger = logging.getLogger()
            logger.INFO("This is a log message.")

       It doesn't matter what name you pass to getLogger() or if you use no name at all.
       LoggingUtils configures the root logger, so all output will be logged to the same
       output.

    3) When your application is finished, call logApplicationFinish() to add standard information at
       the end of your log file.

    """

    def __init__(
        self,
        applicationName,
        logFile: str = None,
        fileLevel: int = logging.NOTSET,
        consoleLevel: int = logging.NOTSET,
    ):
        """
        Initialize an instance of the LoggingUtils. This creates an instance of the logging class and sets
        formatting for the log.

        Args:
            :param applicationName
                A string with the name of the application. This is used only in printing information about the
                application. This does is NOT used to access the instance of logging.Logger.
            :param logFile
                A string with the filespec for the log file.
            :param fileLevel
                An integer with the logging level for messages logged to the log file. Uses the definitions
                from logging. Only messages with the specified level or higher will be logged. Setting the
                level to logging.INFO will prevent logger.debug() messages from being logged, for example.
                If no value is specified, output will not be sent to the log file.
                    Level       Numeric value
                    CRITICAL    50
                    ERROR       40
                    WARNING     30
                    INFO        20
                    DEBUG       10
                    NOTSET      0
            :param consoleLevel
                An integer with the logging level for messages logged to the console. Uses the same definitions
                and values as fileLevel.  If no value is specified, output will not be sent to the console.
        """
        # The name of the application
        self._appName = applicationName
        # The filename used to write log output
        self._filename = logFile
        # The logging level for messages written to the logging file. All messages at this
        # level and higher will be logged.
        self._fileLevel = fileLevel
        # The level for messages to write to the console.
        self._consoleLevel = consoleLevel
        # Instance of logging.Logger used for logging.
        self._logger = None
        # Handler for writing to the log file.
        self._fileHandler = None
        # Handler for writing to the console.
        self._consoleHandler = None
        # User who initiated this program.
        self._username = getpass.getuser()
        # The system on which the program was run.
        self._hostname = platform.node()
        # The start time for this program.
        self._startDateTime = datetime.now()
        # The time this program is finished. This is set by calling logApplicationFinish().
        self._finishDateTime = None
        # Date and time formats
        self._fullDateTimeFormat = "%d%b%Y %H:%M:%S"
        self._timeWithMilleseconds = "%H:%M:%S.%f"

        # Define formatters
        formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] - %(module)s - %(levelname)s - %(message)s",
            self._fullDateTimeFormat,
        )

        # Initialize the root logger. This ensures that all child loggers use the same
        # handlers. With this, users can use any name they like (or no name at all)
        # in the call to:
        self._logger = logging.getLogger()

        # Set the logging level to DEBUG so that all message are processed by the
        # respective handlers. Setting this higher will prevent messages that are
        # lower from being handled, even if the handler is set to a lower level.
        # Setting this to NOTSET blocks all messages.
        self._logger.setLevel(logging.DEBUG)

        # Set up file level logging
        if fileLevel:
            # Create a log file using the application name if no logFile
            # was specified.
            if not self._filename:
                self._filename = os.path.join(self._appName + ".log")

            try:
                # Set the encoding so that files can properly print unicode characters. Was getting
                # an error without this.
                self._fileHandler = logging.FileHandler(
                    self._filename, encoding="UTF-8"
                )
            except IOError:
                raise LogFileCreationError(self._filename)

            self._fileHandler.setLevel(self._fileLevel)

            # add self._fileHandler to self._logger
            self._logger.addHandler(self._fileHandler)

            # Set formatter for file output
            self._fileHandler.setFormatter(formatter)

        # Set up console level logging
        if consoleLevel:
            self._consoleHandler = logging.StreamHandler()
            self._consoleHandler.setLevel(self._consoleLevel)
            self._consoleHandler.setFormatter(formatter)
            self._logger.addHandler(self._consoleHandler)

    def __del__(self):
        """
        Destructor for LoggingUtils.
        """
        # Close the handlers and remove them from the logger.
        # This prevents the problem in unit tests where log output from previous test
        # cases is printed in subsequent test case log files.
        if self._fileHandler:
            self._fileHandler.close()
            self._logger.removeHandler(self._fileHandler)
        if self._consoleHandler:
            self._consoleHandler.close()
            self._logger.removeHandler(self._consoleHandler)

        # Shutdown
        logging.shutdown()

    def logApplicationStart(self):
        """
        Log the start of an application. This inserts a standard set of information:
            * User name
            * Host name
            * Command used to run the application
            * Application name
            * Start time
        """
        command = " ".join(sys.argv)
        start = self._formatDateTime(self._startDateTime)
        self._logger.info(
            "**************************************************************"
        )
        self._logger.info(f"  User         = {self._username}")
        self._logger.info(f"  Hostname     = {self._hostname}")
        self._logger.info(f"  Command      = {command}")
        self._logger.info(f"  Application  = {self._appName}")
        self._logger.info(f"  Start        = {start}")
        self._logger.info(
            "**************************************************************"
        )

    def logApplicationFinish(self):
        """
        Log the finish of an application. This inserts the following information:
            * Finish time
            * Elapsed time
        """
        self._finishDateTime = datetime.now()
        finish = self._formatDateTime(self._finishDateTime)
        elapsedTime = self._finishDateTime - self._startDateTime
        self._logger.info(
            "**************************************************************"
        )
        self._logger.info(f"{self._appName} finished.")
        self._logger.info(f"  Finish time  = {finish}")
        self._logger.info(f"  Elapsed time = {str(elapsedTime)}")
        self._logger.info(
            "**************************************************************"
        )

    def _formatDateTime(self, rawDateTime):
        """
        Formats a time value in a human-readable format.

        Args:
            :param rawTime
                A floating point value returned from datetime.now().

        Returns:
            A string in human readable format with days, hours, minutes, seconds, and microseconds.
            Example: "2 days, 0:00:00.000678
        """
        return rawDateTime.strftime(self._timeWithMilleseconds)
