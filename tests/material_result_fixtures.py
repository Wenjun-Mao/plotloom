"""Rectangular Result-owned metadata and processed ordered values for byte guards."""


class MaterialResult:
    def __init__(self, columns, records):
        self._columns = tuple(columns)
        self._records = records

    def keys(self):
        return self._columns

    def __iter__(self):
        for record in self._records:
            assert set(record) == set(self._columns), "fixture row must contain every declared result column"
            yield tuple(record[key] for key in self._columns)
