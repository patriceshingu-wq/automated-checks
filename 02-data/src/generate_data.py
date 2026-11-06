# generate_data.py
import pandas as pd
import numpy as np, os

np.random.seed(42)        # reproducibility
n = 5000                  # number of synthetic transactions

amounts  = np.random.exponential(scale=200, size=n)
times    = np.random.uniform(0, 24, size=n)
is_fraud = ((amounts > 400) & (times < 6)).astype(int)

df = pd.DataFrame({
    'amount':   amounts.round(2),
    'time':     times.round(2),
    'is_fraud': is_fraud
})
os.makedirs('../data', exist_ok=True)
df.to_csv('../data/transactions.csv', index=False)
print(f'Generated {len(df)} rows, {is_fraud.sum()} fraud')