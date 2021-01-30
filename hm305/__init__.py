import csv
from datetime import datetime


class CRCError(Exception):
    pass


def rint(x):
    return int(round(x))


class CSVWriter:

    def __init__(self, filename=None, delimiter=";", time_format="%Y-%m-%d %H:%M:%S.%f"):
        self.filename = filename
        self.delimiter = delimiter
        self.time_format = time_format
        self.file = None

        if self.filename is not None:
            self.file = open(self.filename, "w")
            self.writer = csv.writer(self.file, delimiter=self.delimiter)
            self.writer.writerow(["datetime", "voltage", "current", "power"])
            self.file.flush()

    def write(self, voltage, current, power):
        if self.file is not None:
            now = datetime.now().strftime(self.time_format)
            self.writer.writerow([now, voltage, current, power])
            self.file.flush()

    def __del__(self):
        if self.file is not None:
            self.file.close()
