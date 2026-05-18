import math

import pytest

from modules.job_management.domain.exceptions import InvalidValueObject
from modules.job_management.domain.value_objects.dataset import Dataset
from modules.job_management.domain.value_objects.job_status import JobStatus, JobStatusEnum
from modules.job_management.domain.value_objects.model_version import ModelVersion
from modules.job_management.domain.value_objects.options import Options
from modules.job_management.domain.value_objects.prediction_result_item import (
    PredictionResultItem,
)
from modules.job_management.domain.value_objects.smiles import Smiles


def test_job_status_accepts_enum_value() -> None:
    status = JobStatus(JobStatusEnum.PENDING)
    assert status.value == JobStatusEnum.PENDING


def test_job_status_rejects_non_enum_value() -> None:
    with pytest.raises(InvalidValueObject):
        JobStatus("PENDING")


def test_model_version_normalizes_whitespace() -> None:
    version = ModelVersion("  gnn-1.0.0  ")
    assert version.value == "gnn-1.0.0"


def test_model_version_rejects_empty() -> None:
    with pytest.raises(InvalidValueObject):
        ModelVersion("   ")


def test_model_version_rejects_invalid_characters() -> None:
    with pytest.raises(InvalidValueObject):
        ModelVersion("gnn@1")


def test_options_accepts_valid_values() -> None:
    options = Options(top_k=10, return_sequence=True)
    assert options.top_k == 10
    assert options.return_sequence is True


def test_options_rejects_invalid_top_k() -> None:
    with pytest.raises(InvalidValueObject):
        Options(top_k=0, return_sequence=True)


def test_options_rejects_non_bool_return_sequence() -> None:
    with pytest.raises(InvalidValueObject):
        Options(top_k=5, return_sequence="yes")  # type: ignore[arg-type]


def test_prediction_result_item_normalizes_sequence() -> None:
    item = PredictionResultItem(affinity=0.9, target_sequence="  acdefg  ")
    assert item.target_sequence == "ACDEFG"


def test_prediction_result_item_rejects_nan_affinity() -> None:
    with pytest.raises(InvalidValueObject):
        PredictionResultItem(affinity=math.nan, target_sequence="ACDEFG")


def test_prediction_result_item_rejects_invalid_sequence_chars() -> None:
    with pytest.raises(InvalidValueObject):
        PredictionResultItem(affinity=0.7, target_sequence="ACD3FG")


def test_smiles_normalizes_whitespace() -> None:
    smiles = Smiles("  CCO  ")
    assert smiles.value == "CCO"


def test_smiles_rejects_unbalanced_parentheses() -> None:
    with pytest.raises(InvalidValueObject):
        Smiles("C(C")


def test_smiles_rejects_unpaired_ring_digit() -> None:
    with pytest.raises(InvalidValueObject):
        Smiles("C1CC")


def test_dataset_currently_has_no_validation() -> None:
    # Reflect current implementation: Dataset.__post_init__ is a no-op.
    dataset = Dataset(name="")
    assert dataset.name == ""
