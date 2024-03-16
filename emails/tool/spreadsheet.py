from typing import List
import pandas as pd

from tool.utils import from_base26, to_base26

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

        def __eq__(self, other):
            return isinstance(other, Spreadsheet.Row) and self.index == other.index

        def __hash__(self):
            return hash(self.index)


    def __init__(self, spreadsheet_id: str, sheet_name: str, sheet_range: str, values: List[List[str]]):
        """
        Parsing is done by creating a raw Pandas DataFrame of the mapped values as well as
        maintaining metadata about the column and row mapping for ease of use when writing back to
        Google Sheets.
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.sheet_range = sheet_range

        df = pd.DataFrame(values)
        df.columns = df.iloc[0]
        df = df[1:]
        df = df.reset_index(drop=True)

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

        self.sheet = df

    def get_header_letter(self, header: str):
        for h in self.headers:
            if h.title == header:
                return h.index
        return None

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
        for i in range(start_row + 1, end_row + 1):
            # Skip first row as header
            sheet_range_rows.append(i)
        return sheet_range_rows

