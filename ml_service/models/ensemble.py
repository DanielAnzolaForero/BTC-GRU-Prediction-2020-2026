import xgboost as xgb
import joblib
import os

class CryptoEnsemble:
    def __init__(self, params=None):
        if params is None:
            self.params = {
                'objective': 'binary:logistic',
                'max_depth': 6,
                'eta': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'eval_metric': 'logloss'
            }
        else:
            self.params = params
        self.model = None

    def train(self, X_train, y_train):
        # Flatten X from (N, Seq, Feat) to (N, Seq*Feat) for XGBoost
        N, S, F = X_train.shape
        X_flattened = X_train.reshape(N, S * F)
        
        dtrain = xgb.DMatrix(X_flattened, label=y_train)
        self.model = xgb.train(self.params, dtrain, num_boost_round=100)

    def predict(self, X):
        N, S, F = X.shape
        X_flattened = X.reshape(N, S * F)
        dtest = xgb.DMatrix(X_flattened)
        return self.model.predict(dtest)

    def save(self, path):
        joblib.dump(self.model, path)

    def load(self, path):
        self.model = joblib.load(path)
