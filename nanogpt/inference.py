# inference.py
import torch
from model import GPTLanguageModel
from data_loader import load_data
from config import *

# Load data to get vocab_size and encoder/decoder
_, _, vocab_size, encode, decode = load_data()

# Create model
model = GPTLanguageModel(vocab_size)
model.load_state_dict(torch.load('nanogpt.pth'))
model.to(device)
model.eval()

# Generate text
context = torch.zeros((1, 1), dtype=torch.long, device=device)
generated_text = decode(model.generate(context, max_new_tokens=100)[0].tolist())
print(generated_text)
