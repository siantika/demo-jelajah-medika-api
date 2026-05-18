from __future__ import annotations

import pickle
from typing import Literal

import numpy as np
import torch

_SAFE_BUILTINS = {
    "dict",
    "list",
    "tuple",
    "set",
    "frozenset",
    "str",
    "bytes",
    "int",
    "float",
    "bool",
}


class _RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if module == "builtins" and name in _SAFE_BUILTINS:
            return super().find_class(module, name)
        if module == "numpy.core.multiarray" and name == "scalar":
            return np.core.multiarray.scalar
        if module == "numpy" and name == "dtype":
            return np.dtype
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


def get_device(selected_device: Literal["cpu", "cuda"] = "cpu") -> torch.device:
    return torch.device(selected_device)


def convert_tensor(load_data, dtype):
    device = get_device()
    return [dtype(data).to(device) for data in load_data]


def load_pickle(file_name: str):
    with open(file_name, "rb") as f:
        return _RestrictedUnpickler(f).load()
