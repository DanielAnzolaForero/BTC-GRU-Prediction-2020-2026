import torch
import torch.nn as nn

class TabTransformer(nn.Module):
    """
    A simplified Tabular Transformer for financial numerical features.
    """
    def __init__(self, input_size, n_heads=4, n_layers=2, dim_feedforward=128, dropout=0.2):
        super(TabTransformer, self).__init__()
        
        # Linear projection to d_model (64)
        self.input_projection = nn.Linear(input_size, 64)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=64, 
            nhead=n_heads, 
            dim_feedforward=dim_feedforward, 
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        # Final MLP
        self.mlp = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size) or (batch_size, input_size)
        # For simplicity in research_pipeline, we might use flat features for TabTransformer
        # but if we use sequences, we'll pool them.
        
        if len(x.shape) == 3:
            # Seq length handling
            x = self.input_projection(x)
            x = self.transformer_encoder(x)
            # Pool: use last time step or mean
            x = x[:, -1, :] 
        else:
            # Batch size x Features
            x = self.input_projection(x).unsqueeze(1) # Add dummy seq dim
            x = self.transformer_encoder(x)
            x = x.squeeze(1)
            
        return self.mlp(x)

if __name__ == "__main__":
    model = TabTransformer(input_size=20)
    dummy_input = torch.randn(16, 20)
    output = model(dummy_input)
    print(f"TabTransformer Output shape: {output.shape}")
