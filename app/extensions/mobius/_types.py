from typing_extensions import TypedDict, Literal, Callable
import pandas as pd

class _AllianceEmblem(TypedDict):
    Shape: int
    Pattern: int
    Icon: int

class _AllianceMember(TypedDict):
    Id: int
    Name: str
    Avatar: str
    Level: int
    AllianceRole: Literal[0, 1, 2]
    TotalWarPoints: int

class AllianceData(TypedDict):
    Id: str
    Name: str
    Description: str
    Emblem: _AllianceEmblem
    AllianceLevel: int
    WarPoints: int
    WarsWon: int
    WarsLost: int
    InWar: bool
    OpponentAllianceId: str | None
    Members: list[_AllianceMember]

class _UserPlanet(TypedDict):
    OwnerId: int
    HQLevel: int

class _IndividualUser(TypedDict):
    Id: int
    Name: str
    Avatar: str
    Level: str
    Experience: int
    TutorialCompleted: bool
    AllianceId: str | None
    Planets: list[_UserPlanet]

_PipeFunction = Callable[[pd.DataFrame], pd.DataFrame]
