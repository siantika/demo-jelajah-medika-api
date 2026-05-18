from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GanDTI(nn.Module):
    def __init__(self, compound_len, protein_len, features, gnn_depth, mlp_depth, mode):
        super().__init__()
        self.mode = mode
        self.embed_compound = nn.Embedding(compound_len, features)
        self.embed_protein = nn.Embedding(protein_len, features)
        self.GNN_depth = gnn_depth
        self.GNN = nn.ModuleList(nn.Linear(features, features) for _ in range(gnn_depth))
        self.W_att = nn.Linear(features, features)
        self.MLP_depth = mlp_depth
        self.MLP = nn.ModuleList(nn.Linear(features * 2, features * 2) for _ in range(mlp_depth))
        self.classification_out = nn.Linear(2 * features, 2)
        self.regression_out = nn.Linear(2 * features, 1)
        self.dropout = nn.Dropout(0.5)

    def _attention(self, compound, protein):
        compound_h = torch.relu(self.W_att(compound))
        protein_h = torch.relu(self.W_att(protein))
        mult = compound @ protein_h.T
        weights = torch.tanh(mult)
        protein = weights.T * protein_h
        return torch.unsqueeze(torch.mean(protein, 0), 0)

    def _graph_neural_net(self, compound, adjacency):
        residual = compound
        for i in range(self.GNN_depth):
            compound_h = F.leaky_relu(self.GNN[i](compound))
            compound = compound + torch.matmul(adjacency, compound_h)
        compound = compound + residual
        return torch.unsqueeze(torch.mean(compound, 0), 0)

    def _mlp_module(self, compound_protein):
        for i in range(self.MLP_depth):
            compound_protein = torch.relu(self.MLP[i](compound_protein))
        compound_protein = self.dropout(compound_protein)
        if self.mode == "classification":
            return self.classification_out(compound_protein)
        return self.regression_out(compound_protein)

    def forward(self, data):
        compound, adjacency, protein = data
        compound_embed = self.embed_compound(compound)
        compound_vector = self._graph_neural_net(compound_embed, adjacency)
        protein_embed = self.embed_protein(protein)
        protein_vector = self._attention(compound_vector, protein_embed)
        return self._mlp_module(torch.cat((compound_vector, protein_vector), 1))

    def predict(self, data):
        predict_data = self.forward(data)
        if self.mode == "classification":
            predict_data = torch.sigmoid(predict_data).to("cpu").data.numpy()
            return list(map(lambda x: np.argmax(x), predict_data))
        return predict_data[0].to("cpu").data.numpy()
