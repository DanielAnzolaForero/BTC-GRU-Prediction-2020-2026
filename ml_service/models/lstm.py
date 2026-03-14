import torch
import torch.nn as nn

class CryptoLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size=1, dropout=0.2):
        super(CryptoLSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True, 
            dropout=dropout if num_layers > 1 else 0
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, output_size),
            nn.Sigmoid() # For binary classification (UP/DOWN)
        )
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        out, _ = self.lstm(x, (h0, c0))
        # Take the last time step output
        out = self.fc(out[:, -1, :])
        return out

if __name__ == "__main__":
    # Test model shape
    model = CryptoLSTM(input_size=8, hidden_size=50, num_layers=2)
    dummy_input = torch.randn(32, 60, 8) # Batch, Seq, Features
    output = model(dummy_input)
    print(f"Output shape: {output.shape}")
