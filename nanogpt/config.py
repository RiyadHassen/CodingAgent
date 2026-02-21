# config.py

# Model parameters
block_size = 32
n_embd = 64
n_head = 4
n_layer = 4
dropout = 0.1
bias = False

# Training parameters
batch_size = 16
learning_rate = 1e-3
max_iters = 1000
eval_interval = 100
eval_iters = 50
device = 'cpu' # 'cuda' if torch.cuda.is_available() else 'cpu'

# Data
data_dir = 'data'
input_file = 'input.txt'
