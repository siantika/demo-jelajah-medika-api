from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from rdkit import Chem

from apps.ml_engine_service.src.infra.integrations.gnn.create_data import (
    create_adjacency,
    create_atoms,
    create_bond_dict,
    get_fingerprints,
    split_sequence,
)
from apps.ml_engine_service.src.infra.integrations.gnn.model import GanDTI
from apps.ml_engine_service.src.infra.integrations.gnn.utils import (
    convert_tensor,
    get_device,
    load_pickle,
)


class GNNPredictorCore:
    def __init__(
        self,
        *,
        args: dict,
        dataset_name: str,
        is_threshold: bool,
        assets_root: Path,
    ) -> None:
        self.args = args
        self.dataset_name = dataset_name
        self.is_threshold = is_threshold
        self.assets_root = assets_root
        self.device = get_device()

    def _model_path(self) -> Path:
        return self.assets_root / "static" / "models" / f"best_{self.dataset_name}_regression.pkl"

    def _target_path(self) -> Path:
        return self.assets_root / "static" / "data" / f"{self.dataset_name}_target_sequence.txt"

    def _fingerprint_dict_path(self) -> Path:
        return self.assets_root / "static" / "models" / f"{self.dataset_name}_fingerprint.pickle"

    def _word_dict_path(self) -> Path:
        return self.assets_root / "static" / "models" / f"{self.dataset_name}_wordDict.pickle"

    def load_model_state(self):
        safe_numpy_globals = [np.core.multiarray.scalar, np.dtype]
        if hasattr(np, "dtypes"):
            for name in dir(np.dtypes):
                value = getattr(np.dtypes, name, None)
                if isinstance(value, type) and name.endswith("DType"):
                    safe_numpy_globals.append(value)
        with open(self._model_path(), "rb") as f:
            if hasattr(torch.serialization, "safe_globals"):
                with torch.serialization.safe_globals(safe_numpy_globals):
                    return torch.load(f, map_location=self.device, weights_only=True)
            return torch.load(f, map_location=self.device, weights_only=True)

    def load_target_sequence(self):
        with open(self._target_path(), "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    def preprocess(self, loaded_target_sequence, smiles: str):
        compounds, adjacencies, proteins = [], [], []
        for sequence in loaded_target_sequence:
            mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
            atoms = create_atoms(mol)
            ij_bond_dict = create_bond_dict(mol)
            compounds.append(get_fingerprints(atoms, ij_bond_dict, radius=2))
            adjacencies.append(create_adjacency(mol))
            proteins.append(split_sequence(sequence, ngram=3))
        return compounds, adjacencies, proteins

    def load_data(self, loaded_target_sequence, smiles: str):
        arr_compounds, arr_adjacencies, arr_proteins = self.preprocess(loaded_target_sequence, smiles)
        compounds = convert_tensor(arr_compounds, torch.LongTensor)
        adjacencies = convert_tensor(arr_adjacencies, torch.FloatTensor)
        proteins = convert_tensor(arr_proteins, torch.LongTensor)
        fingerprint_dict = load_pickle(str(self._fingerprint_dict_path()))
        word_dict = load_pickle(str(self._word_dict_path()))
        compound_len = len(fingerprint_dict)
        protein_len = len(word_dict)
        return list(zip(compounds, adjacencies, proteins)), compound_len, protein_len

    def predict_target(self, smiles: str):
        loaded_model = self.load_model_state()
        loaded_target_sequence = self.load_target_sequence()
        test_data, compound_len, protein_len = self.load_data(loaded_target_sequence, smiles)
        model = GanDTI(
            compound_len,
            protein_len,
            self.args["features"],
            self.args["GNN_depth"],
            self.args["MLP_depth"],
            self.args["mode"],
        ).to(self.device)
        model.load_state_dict(loaded_model["model"])
        model.eval()

        predictions = [model.predict(data) for data in test_data]
        affinity_data = [float(affinity[0]) for affinity in predictions]
        combined_data = sorted(zip(loaded_target_sequence, affinity_data), key=lambda x: x[1], reverse=True)
        threshold_affinity = 0
        if self.is_threshold:
            threshold_affinity = 7.0 if self.dataset_name == "davis" else 12.1
        filtered = [(sequence, affinity) for sequence, affinity in combined_data if affinity > threshold_affinity]
        return [{"sequence_target": sequence, "affinity": affinity} for sequence, affinity in filtered]
