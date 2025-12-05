from setuptools import setup, find_packages

setup(
    name="travel-order-resolver",
    version="0.1.0",
    description="NLP system to resolve French train travel orders - Comparative study: spaCy vs Qwen2.5+ChromaDB",
    author="T-AIA-911-PAR_14",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "spacy>=3.7.0",
        "transformers>=4.35.0",
        "torch>=2.0.0",
        "chromadb==0.4.24",
        "pandas>=2.0.0",
        "numpy<2.0.0",
        "scikit-learn>=1.3.0",
        "networkx>=3.1",
        "seqeval>=1.2.2",
        "llama-cpp-python>=0.2.78",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "jupyter>=1.0.0",
        ],
    },
)
