# A Practical, Deep Technical Guide to Modern AI

## From neural-network fundamentals to transformers, large language models, and agents

**Prepared:** November 2026\
**Audience:** A software/embedded engineer with an ECE + CS background,
prior neural-network coursework, and hands-on experience building
agentic workflows.

------------------------------------------------------------------------

## How to use this guide

This is a map of the field, not a claim that you must master every
branch before building anything. The best way to learn modern AI is to
connect three layers:

1.  **Mathematical model:** What function is being learned, what
    objective is optimized, and how do gradients change its parameters?
2.  **Computational system:** What tensors, kernels, memory transfers,
    accelerators, and distributed processes make the model run?
3.  **Product/system architecture:** How do models connect to data,
    tools, memory, APIs, evaluation, and users?

You already have useful foundations: C/C++, Python, operating systems,
computer architecture, statistics, embedded debugging, Linux, Docker,
databases, and experience building software around LLMs. The goal is to
reconnect those skills to the modern AI stack rather than treating AI as
a completely new discipline.

A useful mental model throughout this guide:

``` text
                 DATA + OBJECTIVE
                       |
                       v
             TRAINABLE MODEL PARAMETERS
                       |
             forward pass / prediction
                       |
                       v
                 LOSS FUNCTION
                       |
              automatic differentiation
                       |
                       v
               GRADIENTS (dL/dθ)
                       |
                 OPTIMIZER STEP
                       |
                       +------ repeat over batches

After training:
  model weights + tokenizer + inference runtime
                       |
                       v
                MODEL INFERENCE
                       |
       prompt/context -> next-token probabilities
                       |
                       v
          application / retrieval / tools / agents
                       |
                       v
              measured user outcome
```

The distinction between **training** and **inference** is foundational.
Training changes model parameters. Inference uses already-trained
parameters to produce outputs. Most application developers work
primarily on inference-time systems, but understanding training explains
why models behave as they do and what adaptation techniques can and
cannot accomplish.

------------------------------------------------------------------------

# Part I --- Rebuilding the neural-network foundation

## 1. What machine learning is actually doing

Traditional programming:

``` text
human writes rules + input -> output
```

Supervised machine learning:

``` text
examples of inputs and desired outputs
             |
             v
learning algorithm adjusts parameters
             |
             v
model approximates input -> output mapping
```

A model is a parameterized function. For an input vector (x), it
computes:

\[ `\hat{y}`{=tex} = f\_`\theta`{=tex}(x) \]

-   (x): input features
-   (`\hat{y}`{=tex}): model prediction
-   (`\theta`{=tex}): all trainable parameters (weights and biases, for
    example)

Training attempts to find parameters that make predictions agree with
examples. It does not usually discover a set of human-readable rules. It
adjusts many numerical parameters so the function performs well on
examples and, ideally, generalizes to new examples.

### The handwritten-digit example

The MNIST task is a useful anchor because it is likely close to what you
implemented in school.

An image is commonly represented as a 28 × 28 grid of grayscale pixel
values. Flattening it gives:

\[ x `\in `{=tex}`\mathbb{R}`{=tex}\^{784} \]

The model produces ten scores, one per digit:

\[ z = f\_`\theta`{=tex}(x) `\in `{=tex}`\mathbb{R}`{=tex}\^{10} \]

A softmax converts scores (logits) into a probability distribution:

\[ p_i = `\frac{e^{z_i}}{\sum_{j=0}^{9} e^{z_j}}`{=tex} \]

If the output is approximately:

``` text
digit:       0     1     2     3     4 ...
probability .01   .02   .91   .01   .01 ...
```

the predicted class is digit 2, because it has the highest probability.

The model does not literally understand the visual concept of "two" as a
person does. It has learned numerical patterns that help distinguish
examples labeled 0 through 9.

## 2. A neuron: weighted sum plus nonlinearity

A simple artificial neuron computes:

\[ z = w\^T x + b \] \[ a = `\phi`{=tex}(z) \]

-   (w): weight vector
-   (b): bias
-   (`\phi`{=tex}): activation function
-   (a): neuron output

The weighted sum is an affine transformation. The activation function
introduces nonlinearity.

Common activations:

-   **ReLU:** (`\max`{=tex}(0,z)). Simple and common in many networks.
-   **Sigmoid:** (1/(1+e\^{-z})). Maps to (0,1), historically common in
    output layers and older networks.
-   **Tanh:** maps to (-1,1).
-   **GELU / SiLU:** smoother nonlinearities commonly used in modern
    architectures.

Why is nonlinearity important? A stack of linear transformations is
still just one linear transformation:

\[ W_3(W_2(W_1x)) = W'x \]

Without nonlinear activations, adding layers would not give the network
the expressive power usually intended.

## 3. A multilayer neural network

A fully connected network can be written:

\[ a\^{(0)} = x \] \[ a\^{(1)} = `\phi`{=tex}(W^{(1)}a^{(0)} + b\^{(1)})
\] \[ a\^{(2)} = `\phi`{=tex}(W^{(2)}a^{(1)} + b\^{(2)}) \] \[ z =
W^{(3)}a^{(2)} + b\^{(3)} \]

Think of each layer as a transformation of a tensor. The output of one
layer becomes the input of the next.

``` text
784 input pixel values
       |
       v
Linear(784 -> 256)
       |
      ReLU
       |
       v
Linear(256 -> 128)
       |
      ReLU
       |
       v
Linear(128 -> 10)
       |
       v
10 logits -> softmax/probabilities -> predicted digit
```

The (W) matrices and (b) vectors are the trainable parameters. The
architecture specifies how parameters are connected; training determines
their values.

### Parameter count

For a linear layer with (n\_{in}) inputs and (n\_{out}) outputs:

\[ `\text{parameters}`{=tex} = n\_{in}n\_{out} + n\_{out} \]

The first term is the weight matrix; the second is the bias vector. This
simple calculation becomes important when thinking about model size,
memory, and compute.

## 4. Where does the loss function come from?

A loss function is a numerical definition of "how wrong was this
prediction?" It is chosen based on the task and the statistical
assumptions we want the model to optimize.

For classification, suppose the true label is digit 2. We want the model
to assign high probability to class 2. A standard loss is
**cross-entropy**:

\[ L = -`\sum`{=tex}\_{i=0}\^{9} y_i `\log`{=tex}(p_i) \]

Here (y) is a one-hot target vector. If the correct class is 2, then
(y_2=1) and all other entries are 0. The expression reduces to:

\[ L = -`\log`{=tex}(p_2) \]

Examples:

-   Correct class probability = 0.99 -\> small loss.
-   Correct class probability = 0.50 -\> larger loss.
-   Correct class probability = 0.01 -\> very large loss.

Cross-entropy is not arbitrary. It is the negative log-likelihood of the
observed label under the model's predicted categorical distribution.
Minimizing it is equivalent to maximizing the likelihood assigned to the
training labels.

Other common objectives:

  -----------------------------------------------------------------------
  Task                    Typical loss            Intuition
  ----------------------- ----------------------- -----------------------
  Regression              Mean squared error      Penalize squared
                                                  distance from target

  Binary classification   Binary cross-entropy    Assign probability to
                                                  yes/no label

  Multiclass              Cross-entropy           Assign probability to
  classification                                  correct class

  Language modeling       Token-level             Predict the next token
                          cross-entropy           in a sequence

  Contrastive learning    Contrastive /           Pull related
                          InfoNCE-style loss      representations
                                                  together and separate
                                                  unrelated ones
  -----------------------------------------------------------------------

The task determines the target and loss. The model architecture
determines the function family. The optimizer determines how parameters
are updated.

## 5. The chain rule and backpropagation --- what you remember from calculus

You remembered correctly: backpropagation uses the multivariable chain
rule to compute how the loss changes with every trainable parameter.

Consider a tiny computation:

\[ z = wx+b,`\quad `{=tex}a=`\sigma`{=tex}(z),`\quad `{=tex}L=(a-y)\^2
\]

We want:

\[ `\frac{\partial L}{\partial w}`{=tex} \]

The chain rule gives:

\[ `\frac{\partial L}{\partial w}`{=tex} =
`\frac{\partial L}{\partial a}`{=tex}
`\frac{\partial a}{\partial z}`{=tex}
`\frac{\partial z}{\partial w}`{=tex} \]

Each factor answers a local question:

-   How does loss change as the activation changes?
-   How does activation change as the pre-activation changes?
-   How does the pre-activation change as the weight changes?

For this example:

\[ `\frac{\partial L}{\partial a}`{=tex}=2(a-y) \] \[
`\frac{\partial a}{\partial z}`{=tex}=`\sigma`{=tex}(z)(1-`\sigma`{=tex}(z))
\] \[ `\frac{\partial z}{\partial w}`{=tex}=x \]

Multiply them to get the gradient.

A deep network is a much larger computation graph. Backpropagation
applies the same principle efficiently, reusing intermediate derivatives
rather than repeatedly differentiating the entire expression from
scratch.

### Computational graph intuition

``` text
x ----\
       multiply/add ---> z ---> activation ---> a ---> loss
w ----/       ^                                  ^
              b                                  y
```

For a large model, the graph contains many tensor operations. Automatic
differentiation records or reconstructs the operations and applies the
chain rule. PyTorch's autograd is doing this bookkeeping for you.

### Why gradients are useful

A gradient points in the direction of greatest local increase in the
loss. To reduce loss, take a small step in the opposite direction:

\[ `\theta`{=tex}\_{t+1} = `\theta`{=tex}*t -
`\eta `{=tex}`\nabla`{=tex}*`\theta `{=tex}L \]

-   (`\theta`{=tex}): parameter vector
-   (`\nabla`{=tex}\_`\theta `{=tex}L): gradient of loss with respect to
    parameters
-   (`\eta`{=tex}): learning rate

The learning rate is a step-size control. Too large can make training
unstable; too small can make it painfully slow.

## 6. Gradient descent, batches, epochs, and optimizers

Training data is usually divided into **batches**.

-   **Sample:** one example.
-   **Batch:** a group of examples used to estimate a gradient.
-   **Step / iteration:** one optimizer update.
-   **Epoch:** one pass through the training dataset.

If there are 60,000 training images and batch size is 100, one epoch
contains 600 batches/updates (assuming all examples are used).

The batch loss is commonly averaged across examples. The gradient of
this average estimates the direction that reduces the dataset objective.

### Common optimizers

-   **SGD:** basic gradient descent, often with momentum.
-   **Momentum:** smooths updates by accumulating a running direction.
-   **Adam:** adapts update scales using running estimates of first and
    second gradient moments.
-   **AdamW:** Adam variant with decoupled weight decay; widely used in
    transformer training.

You do not need to memorize optimizer equations immediately. Understand
the role: an optimizer converts gradients into parameter updates.

### A compact training loop

``` python
for epoch in range(num_epochs):
    for images, labels in train_loader:
        optimizer.zero_grad()

        logits = model(images)
        loss = loss_fn(logits, labels)

        loss.backward()       # compute gradients
        optimizer.step()      # update parameters
```

That is the core loop behind a huge amount of deep learning.

## 7. Training, validation, and test data

A model can memorize training examples without learning patterns that
generalize. This is **overfitting**.

Split data into:

-   **Training:** used to calculate gradients and update parameters.
-   **Validation:** used during development to choose settings and
    compare models.
-   **Test:** held back for a final, less-biased estimate of
    generalization.

Never repeatedly tune against the test set; doing so gradually turns it
into another validation set.

Important concepts:

-   **Underfitting:** model is too simple, poorly optimized, or
    insufficiently trained.
-   **Overfitting:** training performance is strong but unseen-data
    performance is poor.
-   **Regularization:** techniques that discourage brittle or overly
    complex solutions.
-   **Data leakage:** information from validation/test or the future
    accidentally enters training.
-   **Distribution shift:** deployment data differs from training data.

Accuracy is not always enough. For imbalanced classes, precision,
recall, F1, confusion matrices, and calibration can matter more.

## 8. A small PyTorch example: reconnect the old coursework

This example is intentionally close to the MNIST task. It shows the
relationship between tensors, model layers, logits, loss, autograd, and
optimizer.

``` python
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

device = "cuda" if torch.cuda.is_available() else "cpu"

transform = transforms.ToTensor()
train_data = datasets.MNIST(
    root="data", train=True, download=True, transform=transform
)
test_data = datasets.MNIST(
    root="data", train=False, download=True, transform=transform
)

train_loader = DataLoader(train_data, batch_size=128, shuffle=True)
test_loader = DataLoader(test_data, batch_size=128)

class DigitClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Flatten(),          # [B, 1, 28, 28] -> [B, 784]
            nn.Linear(784, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 10),    # 10 raw scores (logits)
        )

    def forward(self, x):
        return self.layers(x)

model = DigitClassifier().to(device)
loss_fn = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)

for epoch in range(5):
    model.train()
    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        logits = model(images)
        loss = loss_fn(logits, labels)
        loss.backward()
        optimizer.step()

    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            predictions = model(images).argmax(dim=1)
            correct += (predictions == labels).sum().item()
            total += labels.size(0)

    print(epoch, correct / total)
```

A key detail: `CrossEntropyLoss` expects raw logits and internally
applies the appropriate log-softmax calculation. Do not add a softmax
before it.

### Questions to ask while reading the code

1.  What is the shape of `images`? `[batch, channels, height, width]`.
2.  What does `Flatten` do? It changes the representation shape, not the
    image's underlying information.
3.  What does `model.parameters()` return? The trainable tensors.
4.  What does `loss.backward()` do? Computes gradients for parameters
    that participate in the graph.
5.  What does `optimizer.step()` do? Mutates the parameters using those
    gradients.
6.  Why `model.eval()`? It switches behavior for layers such as dropout
    and batch normalization.
7.  Why `torch.no_grad()` during evaluation? No gradient graph is
    needed, so memory and computation are saved.

------------------------------------------------------------------------

# Part II --- From ordinary neural networks to modern deep learning

## 9. Why different neural-network architectures exist

A neural network is not one specific architecture. Different structures
encode useful assumptions about different kinds of data.

  -----------------------------------------------------------------------
  Architecture            Useful for              Main idea
  ----------------------- ----------------------- -----------------------
  MLP / fully connected   Tabular data, simple    Every layer transforms
                          classification          a vector

  CNN                     Images, spatial signals Shared filters detect
                                                  local patterns

  RNN / LSTM / GRU        Sequential data         Recurrent state carries
                                                  information over time

  Transformer             Text, code, images,     Attention mixes
                          audio, multimodal       information across
                          sequences               positions

  Graph neural network    Graph-structured data   Update node
                                                  representations using
                                                  neighbors

  Diffusion model         Image/audio/video       Learn to reverse a
                          generation              gradual noise process
  -----------------------------------------------------------------------

### Convolutional neural networks

For images, nearby pixels are related. A CNN uses filters that slide
across the image, detecting local patterns such as edges, textures, and
shapes. Weight sharing means the same filter is applied at different
positions.

This is a useful inductive bias: the model does not need to learn a
separate edge detector for every pixel location.

### Recurrent networks

An RNN processes a sequence while carrying a hidden state:

\[ h_t = f(x_t,h\_{t-1}) \]

This naturally handles ordered data, but sequential computation makes
parallel training difficult, and long-range dependencies can be
challenging. LSTMs and GRUs address some optimization and memory
problems.

Transformers changed the landscape by making attention the central
mechanism and allowing much more parallel computation during training.

------------------------------------------------------------------------

# Part III --- Transformers and large language models

## 10. The central idea: language modeling as next-token prediction

A large language model (LLM) is generally a neural network trained to
model sequences of tokens.

Given a sequence:

``` text
The engineer opened the
```

the model estimates a probability distribution over the next token:

``` text
file      0.31
door      0.18
device    0.11
...
```

It selects or samples a token, appends it to the context, and predicts
again.

Mathematically, a sequence is assigned probability using the chain rule:

\[
P(x_1,`\ldots`{=tex},x_T)=`\prod`{=tex}*{t=1}\^{T}P(x_t`\mid `{=tex}x_1,`\ldots`{=tex},x*{t-1})
\]

Training minimizes the negative log-likelihood of the correct next token
at each position. This is token-level cross-entropy, closely related to
the classification loss you saw with MNIST.

The important conceptual bridge:

-   MNIST: input image -\> classify one of ten labels.
-   Language modeling: preceding tokens -\> classify the next token from
    a very large vocabulary.

The output space is much larger, and the input is a sequence whose
meaning depends on context.

## 11. Tokens and tokenization

An LLM does not directly receive words or characters as humans see them.
A tokenizer converts text into token IDs.

Example, purely illustrative:

``` text
"unbelievable engineering"
          |
       tokenizer
          |
     [4821, 19372, 845]
          |
    embedding lookup
          |
   vectors passed to model
```

A token can be a whole word, part of a word, punctuation, whitespace
pattern, or other byte/character-derived unit. Tokenization is often
based on subword algorithms such as byte-pair encoding or related
methods.

Why it matters:

-   Context limits are measured in tokens, not words.
-   API cost is often related to input and output tokens.
-   Code, unusual names, and non-English text can tokenize differently
    from ordinary English.
-   The model's vocabulary and tokenizer are coupled to its learned
    embedding table.

A tokenizer is not a semantic parser. It is a learned or designed
mapping between text and discrete IDs.

## 12. Embeddings: turning token IDs into vectors

Token IDs are categorical identifiers. Neural networks need numerical
representations that can participate in learned transformations.

An embedding table is a matrix:

\[ E `\in `{=tex}`\mathbb{R}`{=tex}\^{V `\times `{=tex}d} \]

-   (V): vocabulary size
-   (d): embedding dimension

For token ID (i), the model retrieves row (E_i), a vector of length (d).

``` text
token ID 104
    |
    v
embedding matrix E
    |
    v
[-0.12, 0.44, 0.08, ..., 0.31]   # d-dimensional vector
```

The embedding values are learned during training. They are not usually
manually assigned definitions. Their geometry becomes useful to the
model as part of its overall learned computation.

## 13. Attention: how tokens exchange information

The key innovation in the Transformer is attention. Each token
representation can use information from other tokens to build a
context-dependent representation.

Intuition: when processing the word "it" in a sentence, the model may
need to relate it to a noun several tokens earlier. Attention provides a
mechanism for computing which other positions are relevant.

For a matrix of token representations (X), learned projections produce:

\[ Q=XW_Q,`\quad `{=tex}K=XW_K,`\quad `{=tex}V=XW_V \]

-   **Query (Q):** what this position is looking for.
-   **Key (K):** what each position offers for matching.
-   **Value (V):** the information contributed by each position.

Scaled dot-product attention:

\[
Attention(Q,K,V)=softmax`\left`{=tex}(`\frac{QK^T}{\sqrt{d_k}}`{=tex}`\right`{=tex})V
\]

Step by step:

1.  Compare each query with keys using dot products.
2.  Scale the scores to keep their magnitude manageable.
3.  Apply softmax to produce attention weights.
4.  Use those weights to take a weighted sum of value vectors.

``` text
token representations X
       |
   linear projections
       |
   Q       K       V
    \      |      /
     \     |     /
       QK^T / sqrt(d)
              |
            softmax
              |
       attention weights
              |
       weighted sum of V
              |
       contextualized vectors
```

### Why multiple heads?

Multi-head attention performs several attention calculations in
parallel, using different learned projections. Different heads can learn
different patterns of interaction. The outputs are combined and
projected.

Do not overinterpret attention maps as a complete explanation of what a
model "understands." They are part of the computation, not a perfect
human-readable explanation.

### Causal masking

For next-token prediction, a position must not see future tokens during
training. A causal mask blocks attention to later positions.

For a sequence of length 4:

``` text
position 1 can see: 1
position 2 can see: 1, 2
position 3 can see: 1, 2, 3
position 4 can see: 1, 2, 3, 4
```

This ensures the training task matches autoregressive generation.

## 14. The rest of a Transformer block

A decoder-style Transformer block commonly contains:

``` text
input hidden states
       |
causal multi-head self-attention
       |
residual connection + normalization
       |
feed-forward network (MLP)
       |
residual connection + normalization
       |
output hidden states
```

The feed-forward network independently transforms each token position's
representation, while attention mixes information across positions.

**Residual connections** add a block's input to its output. They help
information and gradients flow through deep networks.

**Layer normalization / RMS normalization** stabilizes activation scales
and supports optimization.

A model stacks many such blocks. The final hidden representation is
projected to vocabulary logits. A softmax gives next-token
probabilities.

## 15. What happens when an LLM generates a response?

At inference time:

``` text
system instructions + user message + conversation context
                         |
                     tokenizer
                         |
                    token IDs
                         |
                 embedding lookup
                         |
              transformer layers
                         |
                  vocabulary logits
                         |
              sampling / decoding
                         |
                  next token
                         |
                 append to context
                         |
                    repeat
```

Common decoding concepts:

-   **Greedy decoding:** choose the highest-probability token every
    time.
-   **Temperature:** changes how concentrated or spread out the sampling
    distribution is.
-   **Top-k:** sample only from the k highest-ranked tokens.
-   **Top-p / nucleus sampling:** sample from the smallest set of tokens
    whose cumulative probability reaches p.
-   **Stop sequence / end token:** determines when generation ends.

Temperature does not make a model more knowledgeable. It changes the
randomness of token selection.

### KV cache

During autoregressive generation, the model repeatedly attends to
previous tokens. Recomputing all earlier key and value projections on
every new token would be wasteful.

A **key-value cache** stores previous attention keys and values so the
next generation step can reuse them.

This is a systems concept as much as a model concept. Cache size grows
with sequence length, number of layers, attention heads, and
representation dimensions. Long context therefore has memory and latency
costs.

## 16. What does "training an LLM" mean?

A modern LLM's development is a pipeline, not one magical training
event. The exact process varies by model developer, but a useful
high-level map is:

``` text
large text/code/multimodal corpus
             |
       filtering + deduplication
             |
       tokenization / packing
             |
       pretraining objective
             |
       distributed optimization
             |
       base pretrained model
             |
       instruction / supervised tuning
             |
       preference and behavior optimization
             |
       evaluations + safety work
             |
       deployed model
```

### Pretraining

The model learns broad statistical structure by predicting tokens over
enormous datasets. It adjusts its parameters to reduce next-token
prediction loss.

This is where a large amount of general language, code, factual
associations, and reusable patterns are acquired. Data quality, mixture,
deduplication, filtering, and training choices all matter.

A base model is not necessarily a polished assistant. It may be good at
continuing text without reliably following instructions or behaving
conversationally.

### Supervised fine-tuning (SFT)

The model is trained on curated input/output examples that demonstrate
desired behavior, such as following instructions, answering questions,
or using a particular format.

Fine-tuning starts from pretrained weights. It is not the same as
training from scratch.

### Preference optimization and alignment

A model may be further optimized using comparisons or preference signals
about which responses are better. Historically common approaches include
RLHF (reinforcement learning from human feedback); other approaches
include direct preference optimization and variants.

The broad goal is to shape model behavior toward desired responses, not
simply predict arbitrary internet text.

Important distinction: alignment techniques do not guarantee
truthfulness. A model can be helpful-sounding and still be wrong.

## 17. Why scaling mattered --- and what it does not mean

Increasing model parameters, training data, and compute has often
improved model capability, but scaling is not a magic substitute for
engineering.

Relevant constraints include:

-   Data quality and duplication.
-   Training compute and accelerator availability.
-   Memory bandwidth and communication between GPUs.
-   Optimization stability.
-   Inference latency and serving cost.
-   Evaluation quality.
-   Reliability on the specific task.

A large model can be worse than a smaller one for a particular job if
the smaller model is better adapted, cheaper, faster, or more reliable.

### Training compute versus inference compute

-   **Training compute:** repeatedly process huge datasets and update
    model weights.
-   **Inference compute:** run the fixed model to generate predictions.
-   **Test-time compute:** spend additional inference-time computation
    on a hard problem, such as generating candidates, checking work,
    searching, or reasoning through multiple steps.

Modern systems increasingly improve results not only by making the base
model larger, but by giving it better tools, context, verification, and
inference-time procedures.

## 18. Reasoning models and "thinking"

Some models are trained or configured to spend additional computation on
difficult problems before returning a final answer. The implementation
details vary and are often proprietary.

Useful distinction:

-   **Model capability:** what the learned model can do.
-   **Inference strategy:** how much computation or how many attempts
    are used.
-   **Scaffolding:** external code, tools, search, checks, or
    orchestration around the model.

A strong result can come from a capable model plus a good procedure. It
is not always evidence that the model has a human-like internal
reasoning process.

Treat generated reasoning as a process that must be checked against
evidence, tests, calculations, or the external world.

------------------------------------------------------------------------

# Part IV --- The modern AI application stack

## 19. A model is not an AI product

An LLM by itself is a text-generation component. A useful AI application
usually combines:

``` text
                 user / client
                      |
                  API layer
                      |
             orchestration logic
              /       |        \
          model     retrieval   tools
            |          |          |
        inference   vector DB   external systems
              \       |        /
                application state
                      |
                validation / eval
                      |
                  user result
```

This distinction is important given your previous work with agents: the
model is only one subsystem. Much of the engineering challenge is
conventional software engineering---state, permissions, retries, APIs,
observability, data integrity, concurrency, and failure handling.

## 20. Prompting and context engineering

A prompt is not a weight update. It supplies information to the model at
inference time.

A useful prompt often includes:

-   Role or task framing.
-   Relevant context.
-   Explicit constraints.
-   Examples of desired output.
-   Output schema.
-   A clear definition of success.

**Context engineering** is broader than writing a clever prompt. It is
the process of selecting, organizing, and supplying the right
information to the model at the right time.

Context can include:

-   System/developer instructions.
-   User messages and conversation history.
-   Retrieved documents.
-   Tool descriptions and tool results.
-   Structured state.
-   Examples.
-   Files, images, audio, or other modalities.

A large context window does not mean all information is equally useful.
Irrelevant context can distract the model, consume resources, and make
important details harder to use.

## 21. Embeddings and semantic search

An embedding model maps text (or another supported input) into a vector:

\[ g(text) `\rightarrow `{=tex}`\mathbb{R}`{=tex}\^d \]

Texts with similar semantic content often have nearby vectors, according
to a chosen similarity measure.

A simple retrieval system:

1.  Split documents into chunks.
2.  Generate an embedding for each chunk.
3.  Store vectors and metadata.
4.  Embed the user's query.
5.  Search for nearby vectors.
6.  Return the most relevant chunks to the LLM.

Common similarity functions:

-   Cosine similarity.
-   Dot product.
-   Euclidean distance.

An embedding is not a database of facts in the ordinary relational
sense. It is a learned representation useful for similarity-based
retrieval.

### Chunking is an engineering decision

Chunks that are too large can contain irrelevant material; chunks that
are too small can lose context. Useful strategies include:

-   Fixed token windows with overlap.
-   Splitting by headings, paragraphs, or code structure.
-   Parent-child retrieval: search small chunks but return a larger
    surrounding section.
-   Metadata filters such as product version, document type, date, or
    owner.

For technical documentation, preserve identifiers, headings, version
numbers, and code boundaries. A retrieval system that finds the wrong
driver version can be worse than one that returns no answer.

## 22. RAG: retrieval-augmented generation

RAG combines retrieval with generation:

``` text
user question
     |
embed / search query
     |
retrieve relevant chunks
     |
optional reranking
     |
construct grounded context
     |
LLM generates answer
     |
citations / validation
```

RAG is useful when the answer depends on information outside the model's
parameters, especially private, changing, or specialized information.

RAG is not fine-tuning:

  -----------------------------------------------------------------------
  RAG                                 Fine-tuning
  ----------------------------------- -----------------------------------
  Supplies information at inference   Changes model parameters
  time                                

  Good for changing/private reference Good for behavior, format, or task
  material                            adaptation

  Can provide source passages         Does not inherently provide
                                      citations

  Knowledge can be updated by         Updating knowledge may require
  changing the index                  another training run

  Retrieval can fail or return        Fine-tuning can overfit or fail to
  irrelevant chunks                   teach factual updates
  -----------------------------------------------------------------------

A good RAG system needs evaluation of retrieval and generation
separately:

-   Did it retrieve the right evidence?
-   Did the answer use the evidence accurately?
-   Did it abstain when evidence was insufficient?
-   Are citations traceable to the correct source?

## 23. Tool calling / function calling

A model can request that an application execute a tool. The model does
not magically execute arbitrary code just because it names a function.
The host application must validate and execute the request.

``` text
1. Developer exposes tool schema
2. User asks a task
3. Model emits structured tool request
4. Application validates arguments and permissions
5. Application executes tool
6. Tool result is returned to model
7. Model interprets result and responds or calls another tool
```

Example schema:

``` json
{
  "name": "get_device_status",
  "description": "Read the current status of a device",
  "parameters": {
    "type": "object",
    "properties": {
      "device_id": {"type": "string"}
    },
    "required": ["device_id"]
  }
}
```

A model-generated tool call is an **untrusted proposal**, not an
authorization decision. The application must enforce permissions,
validate types and ranges, and handle errors.

This is analogous to a service receiving a request from a client: the
client can ask, but the server owns the authorization and execution
boundary.

------------------------------------------------------------------------

# Part V --- Agents: connecting model capability to action

## 24. What is an AI agent?

There is no single universally enforced definition. A practical
definition:

> An agent is a system in which a model helps choose actions, uses tools
> to affect or inspect an environment, observes the results, and repeats
> until a stopping condition is reached.

A simple agent loop:

``` text
          task / goal
              |
              v
       model receives context
              |
              v
       choose next action
              |
       +------+------+
       |             |
   final answer   tool request
                     |
               host validates
                     |
               tool executes
                     |
               result returned
                     |
               update context
                     |
                     +------> model again
```

The loop is the essential difference between a one-shot LLM call and an
agentic system.

### Workflow versus agent

A **workflow** has a largely predefined path:

``` text
extract -> validate -> summarize -> store
```

An **agent** has more freedom to decide which action to take next:

``` text
inspect -> search -> test -> inspect result -> revise plan -> finish
```

A workflow is usually easier to test and predict. An agent can handle
more variable tasks but introduces uncertainty, latency, cost, and more
failure modes.

Use the simplest architecture that reliably solves the problem. Do not
add an autonomous loop just because the application uses an LLM.

## 25. Common agent patterns

### A. Prompt chaining

Several model calls execute in a fixed sequence. Useful when a task can
be decomposed into predictable stages.

### B. Routing

A model or classifier directs a request to a specialized handler.

### C. Parallelization

Independent subtasks run concurrently, then results are combined. Watch
for duplicated work, inconsistent assumptions, and synchronization
costs.

### D. Orchestrator-worker

A coordinator decomposes a task and delegates work to specialized
workers. Useful when the number or type of subtasks is not known in
advance.

### E. Evaluator-optimizer

One component generates; another evaluates against criteria; the system
iterates. It works best when the evaluation criteria are concrete enough
to measure.

### F. Human-in-the-loop

The system pauses for approval or clarification before high-impact
actions. This is especially important for irreversible operations,
external communication, security-sensitive tasks, and changes to
production systems.

## 26. Agent state and memory

"Memory" can refer to several very different things:

1.  **Context window:** information included in the current model
    request.
2.  **Conversation history:** prior messages retained by the
    application.
3.  **Working state:** structured data for the current task, such as
    current plan, completed steps, and pending actions.
4.  **Long-term memory:** information stored outside a single
    interaction and retrieved later.
5.  **Knowledge base:** documents or records searched through RAG.

A robust agent should not rely on a giant transcript as its only state
store. Prefer explicit structured state:

``` python
from dataclasses import dataclass, field

@dataclass
class TaskState:
    goal: str
    plan: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    pending_approval: bool = False
    status: str = "running"
```

This resembles ordinary application state management. It makes the
system easier to inspect, resume, test, and recover.

## 27. Reliability engineering for agents

An agent is a distributed software system with a probabilistic decision
component. Treat it accordingly.

Important failure modes:

-   Incorrect tool selection.
-   Invalid arguments.
-   Tool timeout or partial failure.
-   Stale or contradictory observations.
-   Repeated actions / infinite loops.
-   Hallucinated completion.
-   Prompt injection in retrieved content.
-   Permission escalation.
-   Duplicate side effects after retries.
-   Context overflow.
-   Model or provider outage.

Useful controls:

-   Explicit maximum steps and token/cost budgets.
-   Timeouts and cancellation.
-   Schema validation.
-   Least-privilege tool credentials.
-   Idempotency keys for actions that may be retried.
-   Checkpoints and durable task state.
-   Human approval for sensitive actions.
-   Deterministic checks after model actions.
-   Clear distinction between proposed, attempted, and confirmed
    actions.

A model saying "I completed the deployment" is not proof of deployment.
Check the deployment system.

## 28. MCP and tool ecosystems

The Model Context Protocol (MCP) is a protocol for connecting AI
applications to external tools and context providers through
standardized interfaces.

Conceptually:

``` text
AI host / client
      |
  MCP client
      |
  MCP server
   /   |    \
tools resources prompts
   |      |
external systems / data
```

MCP standardizes discovery and communication patterns; it does not make
a tool safe by itself. Authentication, authorization, data boundaries,
validation, and auditing remain application responsibilities.

A useful engineering question is: "What capability does this tool
expose, what identity does it run under, and what is the blast radius if
the model misuses it?"

------------------------------------------------------------------------

# Part VI --- Multimodal AI and generative models

## 29. AI is no longer only text

Modern models can process or generate combinations of:

-   Text.
-   Images.
-   Audio.
-   Video.
-   Structured spatial/action data.

A multimodal model may map different input types into representations
that can interact within a shared or coordinated architecture.

Examples:

-   Image question answering: image + text question -\> textual
    response.
-   Speech recognition: audio -\> text.
-   Speech generation: text or semantic representation -\> audio.
-   Video understanding: sequence of frames, often with timestamps and
    audio.
-   Robotics: perception + state + action representations.

Do not assume every model uses one universal architecture. Some systems
use a shared multimodal backbone; others combine specialized encoders,
decoders, and routing components.

## 30. Diffusion models: a different generative approach

Many image-generation systems use diffusion or related iterative
denoising methods.

Simplified idea:

1.  Take a training image.
2.  Gradually add noise.
3.  Train a neural network to estimate or remove noise at different
    steps.
4.  At generation time, begin with noise and iteratively denoise toward
    a sample.

``` text
real image -> slightly noisy -> noisier -> ... -> random noise
                                               |
                                      learned denoising process
                                               |
                                               v
                                       generated image
```

Text conditioning guides the denoising process toward the requested
concept. This is fundamentally different from an autoregressive LLM
generating one token at a time, though both rely on learned neural
networks and optimization.

------------------------------------------------------------------------

# Part VII --- AI systems engineering: the layer that connects to your background

## 31. GPU computation and tensor operations

Deep learning is dominated by large tensor operations, especially matrix
multiplications.

A fully connected layer:

\[ Y = XW + b \]

For a batch of inputs, this can be executed as a large matrix operation.
GPUs are designed to perform many arithmetic operations in parallel and
have high memory bandwidth.

The performance of an AI workload depends on more than raw FLOPS:

-   Compute throughput.
-   Memory bandwidth.
-   Memory capacity.
-   Kernel launch overhead.
-   Data movement between CPU and GPU.
-   Batch size and sequence length.
-   Parallelization and communication overhead.

### Why memory matters so much

A model's weights must live somewhere. During inference, memory is also
needed for activations, temporary buffers, and KV cache.

A rough lower-bound estimate for weight storage:

\[ `\text{weight memory}`{=tex}
`\approx `{=tex}`\text{parameter count}`{=tex}
`\times `{=tex}`\text{bytes per parameter}`{=tex} \]

For example, a 7-billion-parameter model at 16 bits per parameter
requires roughly 14 GB just for weights, before runtime overhead and
cache.

Quantization stores weights with fewer bits (for example, 8-bit or 4-bit
formats) to reduce memory and sometimes improve speed. It can introduce
accuracy tradeoffs. The actual memory footprint depends on the format
and implementation.

## 32. Training and inference are different systems problems

Training typically needs:

-   Model weights.
-   Activations retained for backward computation.
-   Gradients.
-   Optimizer state.
-   Large data pipelines.
-   Distributed synchronization.

Inference typically needs:

-   Model weights.
-   Input and output buffers.
-   KV cache for autoregressive models.
-   Serving infrastructure and batching.
-   Scheduling and latency management.

This is why a model that can be trained on a large cluster may be
difficult to serve on a single device.

## 33. Distributed training concepts

When a model or dataset is too large for one accelerator, work can be
distributed.

-   **Data parallelism:** replicate model across devices; each processes
    different batches; gradients are synchronized.
-   **Tensor parallelism:** split parts of matrix operations across
    devices.
-   **Pipeline parallelism:** assign different layers to different
    devices; batches flow through stages.
-   **Expert parallelism:** distribute experts in a mixture-of-experts
    architecture.

Communication is a major cost. More GPUs do not automatically mean
proportionally faster training.

## 34. Mixture of Experts (MoE)

A mixture-of-experts model contains multiple expert subnetworks and a
routing mechanism that selects a subset for each token.

``` text
token representation
        |
      router
        |
  select expert(s)
    /    |    \
 Expert A B   C ...
        |
 combine selected outputs
```

This can increase total parameter capacity without activating every
parameter for every token. It introduces routing and communication
complexity. "Total parameter count" and "parameters active per token"
are therefore different quantities.

## 35. Serving models as production services

An inference service has familiar distributed-systems concerns:

``` text
client
  |
API gateway / auth / rate limits
  |
request queue / scheduler
  |
model server
  |
GPU workers
  |
streamed tokens / response
```

Key metrics:

-   **Time to first token (TTFT):** how long before generation starts.
-   **Inter-token latency:** delay between generated tokens.
-   **Tokens per second:** throughput.
-   **End-to-end latency:** total user-perceived time.
-   **Throughput:** requests or tokens served per unit time.
-   **Availability / error rate.**
-   **Cost per request or per output token.**

Batching improves accelerator utilization but can increase latency.
Streaming improves perceived responsiveness but does not necessarily
reduce total compute.

Your experience with embedded telemetry and device diagnostics gives you
a useful way to approach inference systems: identify the resource,
instrument it, measure the bottleneck, and distinguish a software
failure from a hardware, driver, memory, or scheduling failure.

------------------------------------------------------------------------

# Part VIII --- Evaluation, security, and responsible deployment

## 36. Why evaluation is one of the most important AI skills

Traditional software often has crisp expected outputs. LLM outputs are
variable, open-ended, and context-sensitive. You still need tests---but
the testing strategy must account for that variability.

Build an evaluation dataset from representative real tasks. Define what
success means before optimizing.

Useful dimensions:

-   Correctness / factuality.
-   Instruction following.
-   Completeness.
-   Grounding in supplied sources.
-   Tool-selection accuracy.
-   Tool-argument validity.
-   Task completion.
-   Safety and policy compliance.
-   Latency and cost.

### Three levels of evaluation

1.  **Model-level:** Does the model perform the target task?
2.  **Component-level:** Does retrieval, parsing, routing, or a tool
    work?
3.  **System-level:** Does the entire application complete the user's
    task reliably?

A model can score well on a benchmark and still fail in your product
because the retrieval system is poor, context is missing, or the tool
integration is broken.

### Golden datasets and regression tests

Maintain a fixed collection of representative inputs and expected
properties. Run it after prompt, model, retrieval, or code changes.

Not every test needs an exact string match. You can use: - Exact
assertions for structured fields. - Unit tests for deterministic code. -
Reference answers and human review. - Model-based graders, calibrated
against humans. - Task completion and outcome checks. - Adversarial
cases.

Do not trust an LLM judge blindly. It can share the same blind spots as
the model being evaluated.

## 37. Hallucinations and grounding

A hallucination is an output that is unsupported or false but presented
as if it were true.

Why it happens: next-token training rewards plausible continuation, not
a universal guarantee of truth. A model may produce a fluent answer when
evidence is missing.

Mitigations:

-   Retrieve trustworthy sources.
-   Require evidence for claims.
-   Validate structured outputs.
-   Use calculators, databases, compilers, and tests for things they can
    verify.
-   Allow abstention.
-   Separate facts from assumptions.
-   Evaluate factuality on representative cases.

The strongest pattern is often: **model proposes; deterministic system
verifies.**

## 38. Prompt injection and data security

An agent may read untrusted content from web pages, documents, emails,
code repositories, or tool results. That content may contain
instructions attempting to redirect the model.

Treat retrieved content as data, not as trusted instructions. Do not
assume a prompt saying "ignore malicious instructions" is sufficient.

Security controls should exist outside the model:

-   Enforce permissions in the tool implementation.
-   Scope credentials to minimum necessary access.
-   Separate trusted instructions from untrusted data.
-   Require confirmation for high-impact actions.
-   Sanitize and validate inputs/outputs where appropriate.
-   Log sensitive actions.
-   Prevent secrets from entering model context unnecessarily.
-   Use sandboxing for code execution.
-   Design for data exfiltration and confused-deputy risks.

For a Microsoft/enterprise environment, also understand data
classification, tenant boundaries, retention, audit, identity, and
compliance requirements. The model's behavior is not a substitute for
those controls.

------------------------------------------------------------------------

# Part IX --- A practical learning path

## 39. Recommended sequence

Do not jump directly into training a giant model. Rebuild the
fundamentals, then progress toward the systems you are already
interested in.

### Stage 1 --- Reconstruct neural-network training

**Goal:** Be able to explain and implement a small network without
treating autograd as magic.

Learn: - Tensors and shapes. - Linear layers and activations. -
Cross-entropy. - Computation graphs. - Chain rule and backpropagation. -
Gradient descent and Adam. - Train/validation/test splits. - Overfitting
and regularization.

Build: - MNIST classifier in PyTorch. - Then implement a tiny two-layer
network and backpropagation manually using NumPy.

You should be able to explain every line in the training loop and
inspect a parameter's gradient.

### Stage 2 --- Understand transformers from the inside

**Goal:** Understand how text becomes token IDs, vectors, attention, and
next-token predictions.

Learn: - Tokenization. - Embeddings. - Positional information. -
Query/key/value. - Scaled dot-product attention. - Causal masking. -
Transformer blocks. - Logits, softmax, and autoregressive decoding. - KV
cache.

Build: - A tiny character-level language model. - A small self-attention
layer in PyTorch. - A toy decoder-only transformer.

Do not start with a huge framework. A tiny implementation makes tensor
shapes and data flow visible.

### Stage 3 --- Learn how modern LLMs are adapted and used

**Goal:** Distinguish model training from application engineering.

Learn: - Pretraining vs SFT vs preference optimization. - Prompting and
context engineering. - Embedding models. - RAG and reranking. -
Fine-tuning and parameter-efficient fine-tuning (such as LoRA). -
Quantization. - Inference and serving.

Build: - A local-document RAG application with citations. - Compare
keyword search, vector search, and hybrid retrieval. - Measure retrieval
quality separately from answer quality.

### Stage 4 --- Engineer reliable agents

**Goal:** Move beyond demos to systems that can complete tasks safely.

Learn: - Tool schemas and function calling. - Agent loops and state
machines. - Workflow patterns. - Durable state and checkpoints. -
Retries, timeouts, idempotency. - Human approval. - Tracing and
evaluation. - Prompt injection and least privilege.

Build: - A repository investigation agent that can search, read, and run
tests in a sandbox. - Require it to cite file paths and line ranges. -
Make it report proposed changes separately from executed changes. - Add
a fixed evaluation suite and trace every tool call.

### Stage 5 --- AI systems and hardware

**Goal:** Understand what happens below the API.

Learn: - GPU architecture at a high level. - Matrix multiplication and
memory hierarchy. - Model weight and KV-cache sizing. - Quantization. -
Batching and scheduling. - Inference metrics. - Distributed
parallelism. - Linux drivers and accelerator runtime boundaries.

Build: - Run a small open model locally. - Measure memory use, TTFT,
tokens/sec, and effect of context length. - Compare
precision/quantization options on a fixed evaluation set. - Inspect
CPU/GPU utilization and identify bottlenecks.

## 40. Projects that connect AI to your existing engineering experience

These are intentionally selected to combine your embedded, OS, backend,
and agent experience.

### Project A --- Explainable MNIST training lab

Deliverables: - PyTorch model. - Manual NumPy backpropagation for a tiny
network. - Loss/accuracy plots. - Gradient inspection. - Short
explanation of tensor shapes and chain rule.

Why: restores the mathematical foundation and makes modern training less
mysterious.

### Project B --- Technical-documentation RAG for an embedded platform

Use public documentation only. Index multiple versions of a platform's
manuals, release notes, and driver documentation.

Features: - Metadata for product, version, date, and document section. -
Hybrid keyword + vector retrieval. - Reranking. - Citations to source
passages. - "I don't have enough evidence" behavior. - Tests for
version-confusion errors.

Why: directly connects RAG to your experience debugging Linux, drivers,
firmware, and hardware bring-up.

### Project C --- Repository-aware software engineering agent

Give an agent read-only repository access first. It should: 1. Inspect a
repository. 2. Identify relevant projects and dependencies. 3. Search
for call paths. 4. Propose a change plan. 5. Run selected tests in a
sandbox. 6. Summarize evidence and limitations.

Then add controlled write access with human approval.

Why: connects your .NET/open-source learning to practical agent
engineering.

### Project D --- Local LLM inference benchmark on your hardware

Use a model that fits your available device. Record: - Model and
quantization. - Weight memory. - Peak memory. - Context length. - Time
to first token. - Tokens per second. - CPU/GPU utilization. - Output
quality on a small fixed task set.

Why: gives you real experience with the boundary between model
architecture and systems performance.

### Project E --- Multimodal device-diagnostics assistant

Use simulated or public telemetry and device documentation. Let a model
summarize anomalies, but have deterministic code calculate thresholds
and verify measurements.

Architecture:

``` text
device / telemetry simulator
          |
      ingestion API
          |
     time-series DB
          |
 deterministic anomaly checks
          |
 relevant documentation retrieval
          |
       LLM summary
          |
 cited diagnostic report
```

Why: combines embedded telemetry, databases, backend engineering, and AI
without letting a probabilistic model invent measurements.

------------------------------------------------------------------------

# Part X --- What to learn deeply, and what not to overfocus on yet

## 41. Priority map

  -------------------------------------------------------------------------
  Topic                                  Priority now Why
  ---------------------- ---------------------------- ---------------------
  Neural-network                            Very high Reconnects your prior
  training and                                        coursework
  backpropagation                                     

  Transformer                               Very high Core modern LLM
  architecture and                                    architecture
  attention                                           

  Tokenization,                             Very high Explains what an LLM
  embeddings, inference                               actually does

  RAG and retrieval                         Very high Common production
  evaluation                                          application pattern

  Tool calling and agent                    Very high Builds on your
  architecture                                        existing experience

  Evaluation and                            Very high Separates reliable
  observability                                       systems from demos

  GPU/memory/inference                           High Valuable
  fundamentals                                        systems-engineering
                                                      differentiator

  Fine-tuning / LoRA                      Medium-high Important adaptation
                                                      tool, but not always
                                                      needed

  Distributed training                         Medium Learn concepts before
  internals                                           deep implementation

  Advanced optimizer             Medium-low initially Understand the role
  research                                            before studying
                                                      variants

  Training a                   Low practical priority Requires enormous
  frontier-scale model                                data, compute, and
                                                      infrastructure
  -------------------------------------------------------------------------

## 42. Common misconceptions to avoid

1.  **"An LLM is a database."** Its parameters encode learned
    statistical structure, not a clean queryable record store.
2.  **"The model searches the internet by itself."** Search is a tool or
    external capability supplied by the surrounding system.
3.  **"RAG trains the model on my documents."** RAG retrieves documents
    at inference time; it does not update model weights.
4.  **"Fine-tuning is how I add the latest facts."** Frequently,
    retrieval is a better choice for changing factual information.
5.  **"A tool call is the model executing code."** The model requests an
    action; the host application executes and authorizes it.
6.  **"More agents means better results."** More agents add
    coordination, latency, cost, and failure modes.
7.  **"A bigger context window solves memory."** Context selection,
    retrieval, and state management still matter.
8.  **"A fluent answer is a correct answer."** Fluency is not
    verification.
9.  **"Benchmark performance guarantees product quality."** End-to-end
    system evaluation is essential.
10. **"AI engineering is only prompt engineering."** It includes data,
    models, systems, security, evaluation, and product design.

------------------------------------------------------------------------

# Part XI --- A compact glossary

  -----------------------------------------------------------------------
  Term                                Meaning
  ----------------------------------- -----------------------------------
  Parameter / weight                  Trainable numerical value in a
                                      model

  Activation                          Intermediate output of a neuron or
                                      layer

  Tensor                              Multidimensional numerical array

  Logit                               Raw model score before probability
                                      normalization

  Loss                                Scalar objective measuring
                                      prediction error

  Gradient                            Derivative of loss with respect to
                                      parameters

  Backpropagation                     Efficient chain-rule computation of
                                      gradients

  Optimizer                           Algorithm that updates parameters
                                      using gradients

  Epoch                               One pass through the training
                                      dataset

  Batch size                          Number of examples processed per
                                      training step

  Generalization                      Performance on unseen examples

  Overfitting                         Learning training-specific patterns
                                      that do not generalize

  Token                               Discrete unit produced by a
                                      tokenizer

  Embedding                           Learned vector representation

  Transformer                         Neural architecture built around
                                      attention and feed-forward blocks

  Attention                           Weighted information exchange among
                                      sequence positions

  Context window                      Tokens available to a model in a
                                      request

  Inference                           Running a trained model to produce
                                      outputs

  Pretraining                         Broad initial training on large
                                      datasets

  SFT                                 Supervised fine-tuning on curated
                                      examples

  RLHF                                Reinforcement learning from human
                                      feedback

  Fine-tuning                         Further training of an
                                      already-trained model

  LoRA                                Parameter-efficient fine-tuning
                                      method using low-rank updates

  Quantization                        Representing model values with
                                      fewer bits

  RAG                                 Retrieval-augmented generation

  Reranker                            Model that reorders retrieved
                                      candidates by relevance

  Agent                               Model-centered system that selects
                                      actions and observes results

  Tool calling                        Structured request for an
                                      application to execute a function

  MCP                                 Protocol for connecting AI
                                      applications to external
                                      tools/context

  Evaluation / eval                   Repeatable measurement of model or
                                      system behavior

  Trace                               Recorded sequence of model, tool,
                                      and workflow operations

  Hallucination                       Unsupported or false generated
                                      claim

  Prompt injection                    Untrusted content attempting to
                                      manipulate model instructions

  KV cache                            Stored attention keys and values
                                      reused during generation

  MoE                                 Mixture-of-experts architecture
                                      with conditional expert routing

  TTFT                                Time to first generated token
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Part XII --- A short reading and reference path

Use these as primary references and practical companions. Read
selectively; do not try to consume the entire internet's AI content.

1.  **"Attention Is All You Need" (Vaswani et al., 2017).** The original
    Transformer paper. Read the architecture and attention sections
    after completing the neural-network refresher. The paper is
    historically important, though modern production models may differ
    substantially.
2.  **PyTorch tutorials: Autograd and neural networks.** Use these to
    understand how computation graphs and gradient calculation are
    implemented in a real framework.
3.  **Hugging Face Transformers documentation.** Useful for tokenizers,
    model loading, fine-tuning, datasets, and inference workflows.
4.  **Anthropic, "Building Effective Agents."** A valuable architectural
    discussion of workflows, agent loops, orchestration, and when not to
    use agents.
5.  **OpenAI developer documentation: Agents, tracing, and
    evaluations.** Useful for concrete implementation patterns and the
    operational side of agent systems.

A sensible reading order is: PyTorch autograd -\> Transformer paper
(with a tutorial alongside) -\> tokenization and model documentation -\>
RAG -\> agent architecture -\> evaluation and tracing.

------------------------------------------------------------------------

# Final mental model

The field becomes much easier to navigate if you keep these layers
separate:

``` text
MATHEMATICS
  functions, probability, linear algebra, calculus, optimization
       |
       v
MODEL ARCHITECTURE
  MLPs, CNNs, transformers, diffusion, multimodal models
       |
       v
TRAINING
  data, objective, backpropagation, optimizers, evaluation
       |
       v
INFERENCE
  tokenization, forward pass, decoding, KV cache, serving
       |
       v
APPLICATION ENGINEERING
  prompts, retrieval, tools, state, agents, APIs
       |
       v
PRODUCTION ENGINEERING
  tests, evals, traces, security, latency, cost, reliability
```

Your prior neural-network coursework is not obsolete. The chain rule,
loss functions, tensors, and optimization are still at the heart of deep
learning. What changed dramatically is the scale of the models, the
Transformer architecture, the breadth of training data and compute, and
the ecosystem built around inference-time tools, retrieval,
multimodality, and agents.

A strong next step is to implement the MNIST model, then build a tiny
next-token language model and a small transformer. Those two projects
will reconnect the mathematical foundation to the technology behind
modern LLMs. From there, your existing backend, Linux, embedded, and
agent experience becomes a meaningful advantage: you can learn not only
how models work, but how to turn them into dependable systems.
