from dataclasses import dataclass
from enum import Enum


class DatasetEnum(str, Enum):
    KIBA = "KIBA"
    DAVIS = "DAVIS"
    

@dataclass(frozen=True)
class Dataset:
    name: str 
    
    def __post_init__(self):
        pass 
    
    