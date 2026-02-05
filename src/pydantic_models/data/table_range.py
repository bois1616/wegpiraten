from pydantic import BaseModel, ValidationInfo, field_validator


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
    def end_after_start(cls, v: int, info: ValidationInfo) -> int:
        start = 10
        if info.data and "start_row" in info.data:
            start = int(info.data["start_row"])
        if v < start:
            raise ValueError("end_row muss >= start_row sein")
        return v
