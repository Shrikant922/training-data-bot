# PROJECT MEMORY: Training Data Bot

**Last Updated**: 2026-08-24  
**Project Status**: Initial setup complete, ready for implementation  
**Current Phase**: Foundation building

---

## 📚 PROJECT OVERVIEW

### What Is This Project?
A **final year project** to build an enterprise-grade AI training data curation bot that:
- Converts various document types (PDFs, DOCX, TXT, MD, HTML, JSON, CSV, URLs) into high-quality training datasets
- Generates training examples for fine-tuning Large Language Models (LLMs)
- Provides quality evaluation and filtering
- Exports datasets in standard formats (JSONL, JSON)

### Core Concept (Factory Metaphor)
The entire system is designed like a **robot factory** where:
- **Reception Desk** = Package entry point (`__init__.py`)
- **Factory Manager** = Main bot class (`TrainingDataBot`)
- **Blueprints** = Data models (Pydantic)
- **Highway System** = Document loading pipeline
- **Specialist Trucks** = Individual loaders (PDF, Web, Document)
- **Workers** = Task generators (QA, Classification, Summarization)
- **Quality Inspectors** = Evaluation system

---

## 📖 SOURCE DOCUMENTATION

The user provided a comprehensive PDF tutorial: **"Production AI Tutorial.pdf"** (52 pages)

### Tutorial Structure (5 Steps):
1. **Step 1**: Package Entry Point (`__init__.py`) - The reception desk
2. **Step 2**: Factory Manager (Main Bot Class) - `TrainingDataBot` orchestration
3. **Step 3**: Factory Blueprints (Core Data Models) - Pydantic models for all entities
4. **Step 4**: Document Highway System - `UnifiedLoader` auto-routing system
5. **Step 5**: Specialist Trucks - Individual loaders (`PDFLoader`, `WebLoader`, `DocumentLoader`)

### Key Design Principles from Tutorial:
- ✅ Modular, extensible architecture
- ✅ Async/await for concurrent operations
- ✅ Type safety with Pydantic validation
- ✅ Consistent interface pattern (BaseLoader, BaseEntity)
- ✅ Comprehensive error handling
- ✅ Auto-detection and routing (UnifiedLoader)
- ✅ Parallel processing for performance

---

## 📝 DETAILED IMPLEMENTATION FROM TUTORIAL

### Step 1: Package Entry Point (`training_data_bot/__init__.py`)
```python
"""
Training Data Curation Bot
Enterprise-grade training data curation bot for LLM fine-tuning
using Decodo + Python automation.
"""

__version__ = "0.1.0"
__author__ = "Training Data Bot Team"
__email__ = "team@company.com"
__description__ = "Enterprise-grade training data curation bot for LLM fine-tuning"

# Core imports for easy access
from .core.config import settings
from .core.logging import get_logger
from .core.exceptions import TrainingDataBotError

# Main bot class
from .bot import TrainingDataBot

# Document Processing Workers
from .sources import (
    PDFLoader,
    WebLoader,
    DocumentLoader,
    UnifiedLoader,
)

# Task Creation Department
from .tasks import (
    QAGenerator,
    ClassificationGenerator,
    SummarizationGenerator,
    TaskTemplate,
)

# Support Services
from .decodo import DecodoClient
from .preprocessing import TextPreprocessor
from .evaluation import QualityEvaluator
from .storage import DatasetExporter

__all__ = [
    # Core
    "TrainingDataBot",
    "settings",
    "get_logger",
    "TrainingDataBotError",
    # Sources
    "PDFLoader",
    "WebLoader",
    "DocumentLoader",
    "UnifiedLoader",
    # Tasks
    "QAGenerator",
    "ClassificationGenerator",
    "SummarizationGenerator",
    "TaskTemplate",
    # Services
    "DecodoClient",
    "TextPreprocessor",
    "QualityEvaluator",
    "DatasetExporter",
]
```

### Step 2: Main Bot Class (`training_data_bot/bot.py`)
**Imports:**
```python
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from uuid import UUID

from .core.config import settings
from .core.logging import get_logger, LogContext
from .core.exceptions import TrainingDataBotError, ConfigurationError

# Component imports
from .sources import UnifiedLoader
from .decodo import DecodoClient
from .ai import AIClient
from .tasks import TaskManager
from .preprocessing import TextPreprocessor
from .evaluation import QualityEvaluator
from .storage import DatasetExporter, DatabaseManager
```

**Class Structure:**
```python
class TrainingDataBot:
    """Main Training Data Bot class."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger("training_data_bot")
        self.config = config or {}
        self._init_components()
        self.logger.info("Training Data Bot initialized successfully")
    
    def _init_components(self):
        try:
            self.loader = UnifiedLoader()
            self.decodo_client = DecodoClient()
            self.ai_client = AIClient()
            self.task_manager = TaskManager()
            self.preprocessor = TextPreprocessor()
            self.evaluator = QualityEvaluator()
            self.exporter = DatasetExporter()
            self.db_manager = DatabaseManager()
            
            # State (Memory boxes)
            self.documents: Dict[UUID, Document] = {}
            self.datasets: Dict[UUID, Dataset] = {}
            self.jobs: Dict[UUID, ProcessingJob] = {}
        except Exception as e:
            raise ConfigurationError("Failed to initialize bot components", ...)
    
    # 4 Main Superpowers:
    # 1. load_documents() - async document loading
    # 2. process_documents() - async document processing with task templates
    # 3. evaluate_dataset() - quality evaluation
    # 4. export_dataset() - export to JSONL/JSON
    
    # Plus:
    # - get_statistics() - progress reporting
    # - cleanup() - resource management
    # - __aenter__ / __aexit__ - context manager support
    # - quick_process() - one-line operation
```

### Step 3: Core Data Models (`training_data_bot/core/models.py`)
**BaseEntity (Master Template):**
```python
class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Enums:**
```python
class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    URL = "url"

class TaskType(str, Enum):
    QA_GENERATION = "qa_generation"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    NER = "named_entity_recognition"
    RED_TEAMING = "red_teaming"
    INSTRUCTION_RESPONSE = "instruction_response"

class QualityMetric(str, Enum):
    TOXICITY = "toxicity"
    BIAS = "bias"
    DIVERSITY = "diversity"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportFormat(str, Enum):
    JSONL = "jsonl"
    JSON = "json"
    CSV = "csv"
```

**Document Family:**
```python
class Document(BaseEntity):
    title: str
    content: str
    source: str
    doc_type: DocumentType
    word_count: int
    char_count: int

class TextChunk(BaseEntity):
    document_id: UUID
    content: str
    start_index: int
    end_index: int
    chunk_index: int
    token_count: int
```

**Task Family:**
```python
class TaskTemplate(BaseEntity):
    name: str
    task_type: TaskType
    description: str
    prompt_template: str
    parameters: dict

class TaskResult(BaseEntity):
    task_id: UUID
    input_chunk_id: UUID
    output: str
    confidence: float
    quality_scores: dict
    processing_time: float
```

**Training Family:**
```python
class TrainingExample(BaseEntity):
    input_text: str
    output_text: str
    task_type: TaskType
    source_document_id: UUID
    quality_scores: dict

class Dataset(BaseEntity):
    name: str
    description: str
    examples: List[TrainingExample]
    total_examples: int
    train_split: float
    validation_split: float
    test_split: float
```

**Quality Family:**
```python
class QualityReport(BaseEntity):
    target_id: UUID
    overall_score: float
    passed: bool
    metric_scores: dict
    issues: List[str]
    warnings: List[str]
```

**Operations Family:**
```python
class ProcessingJob(BaseEntity):
    name: str
    job_type: str
    status: ProcessingStatus
    total_items: int
    processed_items: int
    started_at: datetime
    estimated_completion: datetime
```

### Step 4: Document Highway System (`training_data_bot/sources/unified.py`)
```python
class UnifiedLoader(BaseLoader):
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.pdf_loader = PDFLoader()
        self.web_loader = WebLoader()
        self.supported_formats = list(DocumentType)
    
    async def load_single(self, source, **kwargs) -> Document:
        # Step 1: Is it a website?
        if source.startswith(('http://', 'https://')):
            return await self.web_loader.load_single(source)
        
        # Step 2: Is it a file?
        source = Path(source)
        if not source.exists():
            raise DocumentLoadError(f"File not found: {source}")
        
        # Step 3: What type of file?
        suffix = source.suffix.lower().lstrip('.')
        doc_type = DocumentType(suffix)
        
        if doc_type == DocumentType.PDF:
            return await self.pdf_loader.load_single(source)
        elif doc_type in [DocumentType.TXT, DocumentType.DOCX, 
                         DocumentType.MD, DocumentType.HTML,
                         DocumentType.JSON, DocumentType.CSV]:
            return await self.document_loader.load_single(source)
        else:
            raise DocumentLoadError(f"Unsupported format: {doc_type}")
    
    async def load_multiple(self, sources, max_workers=4):
        # Parallel loading with semaphore
        semaphore = asyncio.Semaphore(max_workers)
        
        async def load_with_semaphore(source):
            async with semaphore:
                return await self.load_single(source)
        
        tasks = [load_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        documents = []
        for result in results:
            if isinstance(result, Document):
                documents.append(result)
            else:
                logger.error(f"Failed to load: {result}")
        return documents
    
    async def load_directory(self, directory, recursive=True):
        # Find all supported files
        patterns = ["*.pdf", "*.txt", "*.md", "*.html", 
                   "*.docx", "*.json", "*.csv"]
        sources = []
        for pattern in patterns:
            if recursive:
                sources.extend(Path(directory).rglob(pattern))
            else:
                sources.extend(Path(directory).glob(pattern))
        return await self.load_multiple(sources)
```

### Step 5: Specialist Loaders (`training_data_bot/sources/`)
**BaseLoader (`base.py`):**
```python
class BaseLoader(ABC):
    def __init__(self):
        self.logger = get_logger(f"loader.{self.__class__.__name__}")
        self.supported_formats: List[DocumentType] = []
    
    @abstractmethod
    async def load_single(self, source, **kwargs) -> Document:
        pass
    
    async def load_multiple(self, sources, max_workers=4):
        semaphore = asyncio.Semaphore(max_workers)
        async def load_with_semaphore(source):
            async with semaphore:
                return await self.load_single(source)
        tasks = [load_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    def get_document_type(self, source):
        if source.startswith('http'):
            return DocumentType.URL
        source = Path(source)
        suffix = source.suffix.lower().lstrip('.')
        return DocumentType(suffix)
    
    def create_document(self, title, content, source, doc_type, **kwargs):
        return Document(
            id=uuid4(),
            title=title,
            content=content,
            source=source,
            doc_type=doc_type,
            word_count=len(content.split()),
            created_at=datetime.utcnow(),
            **kwargs
        )
```

**DocumentLoader (`document.py`):**
```python
class DocumentLoader(BaseLoader):
    def __init__(self):
        super().__init__()
        self.supported_formats = [
            DocumentType.TXT, DocumentType.MD, DocumentType.HTML,
            DocumentType.JSON, DocumentType.CSV, DocumentType.DOCX
        ]
    
    async def load_single(self, source, encoding="utf-8"):
        doc_type = self.get_document_type(source)
        
        if doc_type == DocumentType.TXT:
            content = await self._load_text(source, encoding)
        elif doc_type == DocumentType.MD:
            content = await self._load_markdown(source, encoding)
        elif doc_type == DocumentType.HTML:
            content = await self._load_html(source, encoding)
        elif doc_type == DocumentType.JSON:
            content = await self._load_json(source, encoding)
        elif doc_type == DocumentType.CSV:
            content = await self._load_csv(source, encoding)
        elif doc_type == DocumentType.DOCX:
            content = await self._load_docx(source)
        else:
            raise DocumentLoadError(f"Unsupported format: {doc_type}")
        
        return self.create_document(
            title=Path(source).stem,
            content=content,
            source=source,
            doc_type=doc_type
        )
    
    # Methods: _load_text, _load_markdown, _load_html, _load_json, _load_csv, _load_docx
```

**PDFLoader (`pdf.py`):**
```python
class PDFLoader(BaseLoader):
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentType.PDF]
    
    async def load_single(self, source):
        source = Path(source)
        if not source.exists():
            raise DocumentLoadError(f"File not found: {source}")
        
        content = await self._extract_pdf_text(source)
        return self.create_document(
            title=source.stem,
            content=content,
            source=source,
            doc_type=DocumentType.PDF,
            extraction_method="PDFLoader.pymupdf"
        )
    
    async def _extract_pdf_text(self, path):
        def _extract_text():
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            text_parts = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"Page {page_num + 1}:\n{text}")
            doc.close()
            return "\n\n".join(text_parts)
        return await asyncio.to_thread(_extract_text)
```

**WebLoader (`web.py`):**
```python
class WebLoader(BaseLoader):
    def __init__(self):
        super().__init__()
        self.supported_formats = [DocumentType.URL]
    
    async def load_single(self, source):
        if not source.startswith(('http://', 'https://')):
            raise DocumentLoadError(f"Invalid URL: {source}")
        
        content = await self._fetch_url_content(source)
        title = self._extract_title(source, content)
        
        return self.create_document(
            title=title,
            content=content,
            source=source,
            doc_type=DocumentType.URL,
            extraction_method="WebLoader.httpx"
        )
    
    async def _fetch_url_content(self, url):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                return self._extract_html_text(response.text)
            else:
                return response.text
    
    def _extract_html_text(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split(" "))
        return ' '.join(chunk for chunk in chunks if chunk)
    
    def _extract_title(self, url, content):
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            title_tag = soup.find('title')
            if title_tag and title_tag.text.strip():
                return title_tag.text.strip()
        except ImportError:
            pass
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc + parsed.path or url
```

### Remaining Modules to Build:
- `core/config.py` - Settings with Pydantic BaseSettings
- `core/logging.py` - Structured logging with LogContext
- `core/exceptions.py` - Custom exceptions (TrainingDataBotError, ConfigurationError, DocumentLoadError)
- `preprocessing/chunker.py` - TextChunker
- `preprocessing/preprocessor.py` - TextPreprocessor
- `ai/client.py` - AIClient
- `tasks/manager.py` - TaskManager
- `tasks/qa_generation.py` - QAGenerator
- `tasks/classification.py` - ClassificationGenerator
- `tasks/summarization.py` - SummarizationGenerator
- `evaluation/evaluator.py` - QualityEvaluator
- `storage/exporter.py` - DatasetExporter
- `storage/database.py` - DatabaseManager
- `decodo/client.py` - DecodoClient

---

## 🏗️ PROJECT STRUCTURE (COMPLETED)

```
training-data-bot/
├── training_data_bot/          # Main package
│   ├── __init__.py            # ✅ Entry point with all exports
│   ├── bot.py                 # ⏳ Main TrainingDataBot class (TO BUILD)
│   ├── core/                  # Core utilities
│   │   ├── __init__.py        # ✅ Created
│   │   ├── models.py          # ⏳ Data models (TO BUILD)
│   │   ├── config.py          # ⏳ Configuration (TO BUILD)
│   │   ├── logging.py         # ⏳ Logging setup (TO BUILD)
│   │   └── exceptions.py      # ⏳ Custom exceptions (TO BUILD)
│   ├── sources/               # Document loaders
│   │   ├── __init__.py        # ✅ Created
│   │   ├── base.py            # ⏳ BaseLoader (TO BUILD)
│   │   ├── unified.py         # ⏳ UnifiedLoader (TO BUILD)
│   │   ├── pdf.py             # ⏳ PDFLoader (TO BUILD)
│   │   ├── web.py             # ⏳ WebLoader (TO BUILD)
│   │   └── document.py        # ⏳ DocumentLoader (TO BUILD)
│   ├── tasks/                 # Task generators
│   │   ├── __init__.py        # ✅ Created
│   │   ├── manager.py         # ⏳ TaskManager (TO BUILD)
│   │   ├── qa_generation.py   # ⏳ QAGenerator (TO BUILD)
│   │   ├── classification.py  # ⏳ ClassificationGenerator (TO BUILD)
│   │   └── summarization.py   # ⏳ SummarizationGenerator (TO BUILD)
│   ├── preprocessing/         # Text preprocessing
│   │   ├── __init__.py        # ✅ Created
│   │   ├── preprocessor.py    # ⏳ TextPreprocessor (TO BUILD)
│   │   └── chunker.py         # ⏳ TextChunker (TO BUILD)
│   ├── evaluation/            # Quality evaluation
│   │   ├── __init__.py        # ✅ Created
│   │   └── evaluator.py       # ⏳ QualityEvaluator (TO BUILD)
│   ├── storage/               # Data export
│   │   ├── __init__.py        # ✅ Created
│   │   ├── exporter.py        # ⏳ DatasetExporter (TO BUILD)
│   │   └── database.py        # ⏳ DatabaseManager (TO BUILD)
│   ├── decodo/                # Web scraping
│   │   ├── __init__.py        # ✅ Created
│   │   └── client.py          # ⏳ DecodoClient (TO BUILD)
│   └── ai/                    # AI client
│       ├── __init__.py        # ✅ Created
│       └── client.py          # ⏳ AIClient (TO BUILD)
├── tests/
│   ├── unit/                  # ✅ Created
│   └── integration/           # ✅ Created
├── docs/                      # ✅ Created
├── examples/                  # ✅ Created
├── .gitignore                 # ✅ Created
├── .env.example               # ✅ Created
├── LICENSE                    # ✅ Created (MIT)
├── README.md                  # ✅ Created
├── pyproject.toml             # ✅ Created
├── requirements.txt           # ✅ Created
└── requirements-dev.txt       # ✅ Created
```

---

## 🎯 CORE ARCHITECTURE

### Main Bot Class: `TrainingDataBot`
The factory manager with **4 main superpowers**:
1. **load_documents()** - Ingests documents from any source
2. **process_documents()** - Converts to training examples
3. **evaluate_dataset()** - Quality checks
4. **export_dataset()** - Packages results

Also provides:
- **quick_process()** - One-line operation
- **get_statistics()** - Progress reporting
- Context manager support (async with)
- Async/await throughout

### Data Models (Blueprints)

#### Base Entity
All models inherit from `BaseEntity`:
- `id: UUID` - Unique identifier
- `created_at: datetime` - Creation timestamp
- `updated_at: Optional[datetime]` - Update timestamp
- `metadata: Dict[str, Any]` - Extra information

#### Enums
- **DocumentType**: PDF, DOCX, TXT, MD, HTML, JSON, CSV, URL
- **TaskType**: QA_GENERATION, CLASSIFICATION, SUMMARIZATION, NER, RED_TEAMING, INSTRUCTION_RESPONSE
- **QualityMetric**: TOXICITY, BIAS, DIVERSITY, COHERENCE, RELEVANCE
- **ProcessingStatus**: PENDING, PROCESSING, COMPLETED, FAILED
- **ExportFormat**: JSONL, JSON, CSV

#### Document Family
- **Document**: Original source document
- **TextChunk**: Bite-sized pieces for processing

#### Task Family
- **TaskTemplate**: Recipe card for tasks
- **TaskResult**: Output from task execution

#### Training Family
- **TrainingExample**: One input-output pair
- **Dataset**: Complete collection of examples

#### Quality Family
- **QualityReport**: Report card with scores

#### Operations Family
- **ProcessingJob**: Work order tracking

### Document Loading Pipeline

#### UnifiedLoader (Traffic Controller)
Auto-detects document type and routes to correct loader:
1. Check if URL (http/https) → WebLoader
2. Check if file exists
3. Get file extension
4. Route to specialized loader
5. Return standardized Document object

#### Specialized Loaders
- **BaseLoader**: Master blueprint all loaders follow
- **DocumentLoader**: Handles TXT, MD, HTML, JSON, CSV, DOCX
- **PDFLoader**: Uses PyMuPDF for PDF extraction
- **WebLoader**: Uses httpx + BeautifulSoup for web content

All loaders:
- Follow same interface (`load_single`, `load_multiple`)
- Support parallel processing
- Return standardized Document objects
- Handle errors gracefully

### Data Flow
```
Raw Documents 
  → UnifiedLoader (auto-detect)
  → Specialized Loader 
  → Document Objects
  → TextPreprocessor (chunk)
  → TextChunks
  → TaskManager + AIClient
  → TaskResults
  → TrainingExamples
  → QualityEvaluator (filter)
  → Dataset
  → DatasetExporter (JSONL/JSON)
```

---

## 🔧 TECHNOLOGIES & DEPENDENCIES

### Core Dependencies
- **pydantic>=2.0.0** - Data validation and models
- **httpx>=0.24.0** - Async HTTP requests
- **aiofiles>=23.0.0** - Async file operations
- **PyMuPDF>=1.23.0** - PDF text extraction
- **beautifulsoup4>=4.12.0** - HTML parsing
- **python-docx>=1.0.0** - Word document reading
- **python-dotenv>=1.0.0** - Environment variables
- **rich>=13.0.0** - Terminal formatting

### Dev Dependencies
- **pytest>=7.4.0** - Testing framework
- **pytest-asyncio>=0.21.0** - Async test support
- **pytest-cov>=4.1.0** - Code coverage
- **black>=23.0.0** - Code formatter
- **ruff>=0.1.0** - Linter
- **mypy>=1.5.0** - Type checker

---

## 📝 COMPLETED TASKS

### Session 1: 2026-08-24
1. ✅ Read and understood complete PDF tutorial (52 pages)
2. ✅ Created project directory structure
3. ✅ Created all configuration files:
   - pyproject.toml
   - requirements.txt
   - requirements-dev.txt
   - .gitignore
   - .env.example
   - LICENSE (MIT)
4. ✅ Created README.md with comprehensive documentation
5. ✅ Created all `__init__.py` files with proper imports/exports
6. ✅ Set up test structure (unit + integration)

---

## 🎯 NEXT STEPS (PRIORITY ORDER)

### Immediate Next: Build Core Foundation
1. ✅ **core/models.py** - All Pydantic data models (BaseEntity, enums, all model families)
2. ✅ **core/config.py** - Configuration management with environment variables
3. **core/logging.py** - Logging setup with LogContext
4. **core/exceptions.py** - Custom exception classes

### Then: Document Loading System
5. **sources/base.py** - BaseLoader abstract class
6. **sources/document.py** - DocumentLoader for text formats
7. **sources/pdf.py** - PDFLoader for PDF files
8. **sources/web.py** - WebLoader for websites
9. **sources/unified.py** - UnifiedLoader auto-routing

### Then: Main Bot Class
10. **bot.py** - TrainingDataBot orchestration class

### Then: Processing Pipeline
11. **preprocessing/chunker.py** - TextChunker
12. **preprocessing/preprocessor.py** - TextPreprocessor
13. **ai/client.py** - AIClient for LLM calls
14. **tasks/manager.py** - TaskManager
15. **tasks/qa_generation.py** - QAGenerator
16. **tasks/classification.py** - ClassificationGenerator
17. **tasks/summarization.py** - SummarizationGenerator

### Then: Quality & Export
18. **evaluation/evaluator.py** - QualityEvaluator
19. **storage/exporter.py** - DatasetExporter
20. **storage/database.py** - DatabaseManager (optional)
21. **decodo/client.py** - DecodoClient (optional)

### Finally: Testing & Examples
22. Write unit tests
23. Write integration tests
24. Create example scripts

---

## 💡 IMPORTANT DESIGN DECISIONS

1. **Async First**: All I/O operations use async/await
2. **Type Safety**: Full Pydantic validation, mypy compliance
3. **Modular**: Each component is independent and replaceable
4. **Extensible**: Easy to add new loaders, generators, exporters
5. **Error Handling**: Graceful degradation, detailed logging
6. **Performance**: Parallel processing where possible
7. **User Friendly**: Simple API, context managers, one-line operations

---

## 🚨 REMEMBER WHEN IMPLEMENTING

### Code Style
- Use type hints everywhere
- Follow Black formatting (line length 100)
- Write docstrings for all classes and methods
- Use async/await for I/O operations
- Handle errors gracefully with try/except
- Log important operations

### Testing
- Write tests as you build
- Test async operations with pytest-asyncio
- Mock external services (AI, web requests)
- Aim for >80% code coverage

### Documentation
- Keep README updated
- Add docstrings explaining the "why" not just "what"
- Create examples for common use cases

---

## 🎓 USER CONTEXT

- This is a **final year project**
- User wants to understand the full implementation
- User may restart PC between sessions - **ALWAYS READ THIS FILE FIRST**
- User prefers building step-by-step with explanations
- User has the PDF tutorial as reference

---

## 📌 BEFORE STARTING ANY NEW TASK

1. **READ THIS FILE** to understand current state
2. **CHECK** what's already built (marked with ✅)
3. **IDENTIFY** what needs to be built next (marked with ⏳)
4. **REFERENCE** the PDF tutorial for implementation details
5. **FOLLOW** the design principles and architecture
6. **TEST** as you build
7. **UPDATE** this file when completing major milestones

---

**END OF PROJECT MEMORY**
