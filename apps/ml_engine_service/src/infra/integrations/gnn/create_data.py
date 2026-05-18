from __future__ import annotations

from collections import defaultdict

import numpy as np
from rdkit import Chem


def create_atoms(mol) -> np.ndarray:
    atom_dict = defaultdict(lambda: len(atom_dict))
    atoms = [atom.GetSymbol() for atom in mol.GetAtoms()]

    for atom in mol.GetAromaticAtoms():
        idx = atom.GetIdx()
        atoms[idx] = (atoms[idx], "aromatic")
    return np.array([atom_dict[value] for value in atoms])


def create_bond_dict(mol):
    bond_dict = defaultdict(lambda: len(bond_dict))
    ij_bond_dict = defaultdict(list)
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        bond_type = bond_dict[str(bond.GetBondType())]
        ij_bond_dict[i].append((j, bond_type))
        ij_bond_dict[j].append((i, bond_type))
    return ij_bond_dict


def get_fingerprints(atoms, bond_dict, radius: int) -> np.ndarray:
    edge_dict = defaultdict(lambda: len(edge_dict))
    fingerprint_dict = defaultdict(lambda: len(fingerprint_dict))

    if len(atoms) == 1 or radius == 0:
        return np.array([fingerprint_dict[atom] for atom in atoms])

    nodes = atoms
    ij_edge_dict = bond_dict
    for _ in range(radius):
        fingerprints = []
        for i, j_edge in ij_edge_dict.items():
            neighbors = [(nodes[j], edge) for j, edge in j_edge]
            fingerprint = (nodes[i], tuple(sorted(neighbors)))
            fingerprints.append(fingerprint_dict[fingerprint])
        nodes = fingerprints

    ij_edge_dict2 = defaultdict(list)
    for i, j_edge in edge_dict.items():
        for j, edge in j_edge:
            both_side = tuple(sorted((nodes[i], nodes[j])))
            edge_val = edge_dict[(both_side, edge)]
            ij_edge_dict2[i].append((j, edge_val))
    return np.array(fingerprints)


def create_adjacency(mol) -> np.ndarray:
    return np.array(Chem.GetAdjacencyMatrix(mol))


def split_sequence(sequence: str, ngram: int) -> np.ndarray:
    word_dict = defaultdict(lambda: len(word_dict))
    sequence = "-" + sequence + "="
    words = [word_dict[sequence[i : i + ngram]] for i in range(len(sequence) - ngram + 1)]
    return np.array(words)
