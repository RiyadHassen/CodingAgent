# NanoGPT

This is a character-level NanoGPT model built using PyTorch. The model is a simplified version of the GPT-2 architecture.

## Project Structure

- `model.py`: Contains the GPT model definition.
- `train.py`: The training script.
- `inference.py`: The inference script.
- `data_loader.py`: Handles data loading and preprocessing.
- `config.py`: Stores the model and training configurations.
- `data/input.txt`: The training data.

## How to Run

1. **Install dependencies:**
   ```bash
   pip install torch
   ```

2. **Train the model:**
   ```bash
   python train.py
   ```
   This will train the model and save the weights to `nanogpt.pth`.

3. **Run inference:**
   ```bash
   python inference.py
   ```
   This will load the trained model and generate text.

## Configuration

The model and training parameters can be configured in `config.py`.

## Sample Output

The model is trained on a small dataset for a short period of time, so the generated text may not be very coherent. Here is some sample output:

```
- I am learning how to build a transformer ghining text with this model.
Let
Let's add some more var
```
