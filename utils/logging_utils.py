"""
LoggingUtils.py

This file contains a class with utilities to facilitate consistent logging
patterns.
"""

import logging
import os
import getpass
import platform
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
        formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] - %(module)s - %(levelname)s - %(message)s",
            self._fullDateTimeFormat,
        )
        self._logger = logging.getLogger()
        self._logger.setLevel(logging.DEBUG)
        if fileLevel:
            if not self._filename:
                self._filename = os.path.join(self._appName + ".log")

            try:
                self._fileHandler = logging.FileHandler(
                    self._filename, encoding="UTF-8"
                )
            except IOError:
                raise LogFileCreationError(self._filename)

            self._fileHandler.setLevel(self._fileLevel)
            self._logger.addHandler(self._fileHandler)

            self._fileHandler.setFormatter(formatter)
        if consoleLevel:
            self._consoleHandler = logging.StreamHandler()
            self._consoleHandler.setLevel(self._consoleLevel)
            self._consoleHandler.setFormatter(formatter)
            self._logger.addHandler(self._consoleHandler)

    def __del__(self):
        """
        Destructor for LoggingUtils.
        """

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
        """
        return rawDateTime.strftime(self._timeWithMilleseconds)
