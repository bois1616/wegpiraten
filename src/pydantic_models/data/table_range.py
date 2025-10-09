from pydantic import BaseModel, field_validator


class TableRange(BaseModel):
    """
    Bereich der Positionszeilen im Sheet (inklusive).
    """

    start_row: int = 10
    end_row: int = 28
    first_col: str = "A"
    last_col: str = "H"

    @field_validator("end_row")
    @classmethod
    def end_after_start(cls, v, values):
        start = values.get("start_row", 10)
        assert v >= start, "end_row muss >= start_row sein"
        return v