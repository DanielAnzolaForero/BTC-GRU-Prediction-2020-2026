import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

class PurgedKFold:
    """
    Implementation of Purged K-Fold Cross-Validation as described by Marcos López de Prado.
    Ensures that training and test sets are separated by a 'purge' zone to prevent 
    leakage due to serial correlation in financial time series.
    """
    def __init__(self, n_splits=5, purge_pct=0.01):
        self.n_splits = n_splits
        self.purge_pct = purge_pct

    def split(self, X, y=None, groups=None):
        """
        Custom split logic with purging.
        """
        n_samples = len(X)
        indices = np.arange(n_samples)
        purge_size = int(n_samples * self.purge_pct)
        
        # We use a non-shuffled KFold as base for time-series
        kf = KFold(n_splits=self.n_splits, shuffle=False)
        
        for train_indices, test_indices in kf.split(X):
            # Test indices are a continuous block in non-shuffled KFold
            test_start = test_indices[0]
            test_end = test_indices[-1]
            
            # PURGING: Remove indices that are too close to the test set
            # (within purge_size before and after the test set)
            purged_train_indices = []
            for idx in train_indices:
                if idx < test_start - purge_size or idx > test_end + purge_size:
                    purged_train_indices.append(idx)
            
            yield np.array(purged_train_indices), test_indices

def get_purged_data(X, y, train_indices, test_indices):
    """
    Helper to get purged subsets and ensure no leakage.
    """
    return X[train_indices], X[test_indices], y[train_indices], y[test_indices]
