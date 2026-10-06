# Training Data Bot - Test Fixtures
# Sample text content for testing all document types

SAMPLE_TEXT = """
Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that enables systems to learn
and improve from experience without being explicitly programmed. The focus is on
developing computer programs that can access data and use it to learn for themselves.

The process begins with observations or data, such as examples, direct experience,
or instruction, to look for patterns in data and make better decisions in the future.
The primary aim is to allow computers to learn automatically without human intervention
or assistance and adjust actions accordingly.

Types of Machine Learning

There are three main types of machine learning:

1. Supervised Learning: The algorithm is trained on labeled data. The model learns
to map inputs to outputs based on example input-output pairs. Common applications
include classification and regression tasks.

2. Unsupervised Learning: The algorithm works with unlabeled data and must find
structure on its own. Clustering and dimensionality reduction are common techniques.

3. Reinforcement Learning: An agent learns to make decisions by taking actions in
an environment to maximize a cumulative reward signal.

Applications

Machine learning has numerous real-world applications including:
- Image and speech recognition
- Natural language processing
- Recommendation systems
- Medical diagnosis
- Financial fraud detection
- Autonomous vehicles

The field continues to evolve rapidly with deep learning and neural networks pushing
the boundaries of what is possible with artificial intelligence.
"""

SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Python Programming Language</title></head>
<body>
<h1>Python</h1>
<p>Python is a high-level, general-purpose programming language. Its design philosophy
emphasizes code readability with the use of significant indentation.</p>
<h2>Features</h2>
<ul>
<li>Dynamic typing</li>
<li>Garbage collection</li>
<li>Multiple programming paradigms</li>
</ul>
<p>Python was created by Guido van Rossum and first released in 1991.</p>
</body>
</html>"""

SAMPLE_MARKDOWN = """# Deep Learning Overview

## What is Deep Learning?

Deep learning is a machine learning technique that teaches computers to do what
comes naturally to humans: learn by example. Deep learning is a key technology
behind driverless cars.

## Neural Networks

Neural networks are the backbone of deep learning algorithms. They are inspired
by the structure of the human brain, with layers of interconnected nodes.

### Types of Neural Networks

- **CNN** - Convolutional Neural Networks for image processing
- **RNN** - Recurrent Neural Networks for sequential data  
- **Transformer** - Attention-based models for NLP tasks

## Training Process

1. Initialize weights randomly
2. Forward pass through network
3. Calculate loss
4. Backpropagation
5. Update weights using gradient descent
6. Repeat until convergence
"""

SAMPLE_JSON = """[
  {"topic": "AI", "content": "Artificial intelligence is the simulation of human intelligence by machines.", "difficulty": "beginner"},
  {"topic": "ML", "content": "Machine learning allows systems to automatically learn and improve from experience.", "difficulty": "intermediate"},
  {"topic": "DL", "content": "Deep learning uses neural networks with many layers to model complex patterns.", "difficulty": "advanced"}
]"""

SAMPLE_CSV = """title,content,category
Introduction to AI,Artificial intelligence enables machines to perform tasks that typically require human intelligence.,Technology
Python Basics,Python is an interpreted high-level general-purpose programming language created by Guido van Rossum.,Programming
Data Science,Data science is an interdisciplinary field that uses scientific methods to extract knowledge from data.,Analytics
Neural Networks,Neural networks are computing systems inspired by biological neural networks in animal brains.,Deep Learning
"""
