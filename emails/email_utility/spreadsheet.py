from typing import List
import pandas as pd

from email_utility.utils import from_base26, to_base26

class Spreadsheet:
    """
    Contains details about the spreadsheet.
    """

    class Header:
        def __init__(self, index: str, title: str):
            self.index = index
            self.title = title

    class Row:
        def __init__(self, index: int, values: pd.Series):
            self.index = index
            self.values = values

    def __init__(
            self,
            sheet_range: str,
            values: List[List[str]],
            mapping: dict):
        """
        Parsing is done by creating a raw Pandas DataFrame of the mapped values as well as
        maintaining metadata about the column and row mapping for ease of use when writing back to
        Google Sheets.
        """

        df = pd.DataFrame(values)
        df.columns = df.iloc[0]
        df = df[1:]
        df = df.reset_index(drop=True)
        df = df.rename(columns=mapping)

        self.range = self.parse_range(sheet_range)
        self.headers = [
            Spreadsheet.Header(idx, value)
            for idx, value
            in zip(self.get_sheet_range_columns(self.range[0][0], self.range[1][0]), df.columns)]
        self.rows = [
            Spreadsheet.Row(idx, value)
            for idx, value
            in zip(
                self.get_sheet_range_rows(self.range[0][1], self.range[1][1]),
                [row for i, row in df.iterrows()])]

        unused = set(df.columns) - mapping.keys() - set(mapping.values())
        # Remove all mapped keys and their corresponding mapping since we've already renamed them
        df = df.drop(list(unused))
        self.sheet = df

    def parse_range(self, sheet_range: str):
        def parse_col(s):
            col = ''
            i = 0
            while i < len(s):
                if s[i].isdigit():
                    break
                col += s[i]
                i += 1
            return col, int(s[i:])

        [start, end] = sheet_range.split(':')

        return [parse_col(start), parse_col(end)]

    def get_sheet_range_columns(self, start_col: str, end_col: str):
        """
        Expects sheet range to only be <start_col><start_row>:<end_col><end_row>
        """
        sheet_range_columns = []
        for i in range(from_base26(start_col), from_base26(end_col) + 1):
            sheet_range_columns.append(to_base26(i))
        return sheet_range_columns

    def get_sheet_range_rows(self, start_row: int, end_row: int):
        sheet_range_rows = []
        for i in range(start_row, end_row + 1):
            sheet_range_rows.append(i)
        return sheet_range_rows

