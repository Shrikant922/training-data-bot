"""
Core Data Models - The Factory Blueprints

This module contains all Pydantic data models used throughout the Training Data Bot.
Models are organized into families: Base, Enums, Document, Task, Training, Quality, Operations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# FOUNDATION: BaseEntity (The Master Template)
# =============================================================================

class BaseEntity(BaseModel):
    """
    Master blueprint that all entities inherit from.

    Provides:
    - Unique identifier (UUID)
    - Creation timestamp
    - Optional update timestamp
    - Flexible metadata dictionary
    """
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# ENUMS: The Sorting System (Categories)
# =============================================================================

class DocumentType(str, Enum):
    """What kind of files can we handle?"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    URL = "url"


class TaskType(str, Enum):
    """What jobs can our robots do?"""
    QA_GENERATION = "qa_generation"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    NER = "named_entity_recognition"
    RED_TEAMING = "red_teaming"
    INSTRUCTION_RESPONSE = "instruction_response"


class QualityMetric(str, Enum):
    """How do we check if work is good?"""
    TOXICITY = "toxicity"
    BIAS = "bias"
    DIVERSITY = "diversity"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"


class ProcessingStatus(str, Enum):
    """Status of a processing job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportFormat(str, Enum):
    """Supported export formats"""
    JSONL = "jsonl"
    JSON = "json"
    CSV = "csv"


# =============================================================================
# DOCUMENT FAMILY: Our Input Data
# =============================================================================

class Document(BaseEntity):
    """
    Original source document loaded into the system.

    Example:
        - Title: "Harry Potter and the Sorcerer's Stone"
        - Content: All the words inside
        - Source: "School library"
        - Type: "Physical book"
        - Word count: "About 77,000 words"
    """
    title: str
    content: str
    source: str
    doc_type: DocumentType
    word_count: int
    char_count: int


class TextChunk(BaseEntity):
    """
    Bite-sized pieces of a document for efficient AI processing.

    Large documents are cut into smaller, manageable chunks so the AI
    can process them efficiently.

    Example:
        - Original Document: "The Adventures of Tom Sawyer"
        - Chunk 1: Pages 1-10
        - Chunk 2: Pages 11-20
        - Chunk 3: Pages 21-30
    """
    document_id: UUID
    content: str
    start_index: int
    end_index: int
    chunk_index: int
    token_count: int


# =============================================================================
# TASK FAMILY: Our Work Instructions
# =============================================================================

class TaskTemplate(BaseEntity):
    """
    Recipe card that defines a task for the AI to execute.

    Example:
        - Name: "Mom's Famous Chocolate Chip Cookies"
        - Type: "Dessert"
        - Description: "Soft, chewy cookies"
        - Instructions: "Mix flour and butter, add eggs, bake at 350°F..."
        - Parameters: "Temperature: 350°F, Time: 12 minutes"
    """
    name: str
    task_type: TaskType
    description: str
    prompt_template: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseEntity):
    """
    Finished product from executing a task template on a text chunk.

    Example:
        - Task: "Read paragraph about dinosaurs and make 3 questions"
        - Input: "Dinosaurs lived millions of years ago..."
        - Output:
            - "What did dinosaurs eat?"
            - "How big were dinosaurs?"
            - "When did dinosaurs live?"
        - Confidence: 95%
        - Quality: Good questions, relevant to topic
        - Time: 2.3 seconds
    """
    task_id: UUID
    input_chunk_id: UUID
    output: str
    confidence: float
    quality_scores: Dict[str, float] = Field(default_factory=dict)
    processing_time: float


# =============================================================================
# TRAINING FAMILY: Our Final Products
# =============================================================================

class TrainingExample(BaseEntity):
    """
    One perfect input-output pair for LLM fine-tuning.

    Example:
        - Input: "What's 2 + 2?"
        - Output: "4"
        - Task Type: "Math Problem"
        - Source: "Math Textbook, Page 15"
        - Quality: "Perfect example"
    """
    input_text: str
    output_text: str
    task_type: TaskType
    source_document_id: UUID
    source_chunk_id: Optional[UUID] = None
    quality_scores: Dict[str, float] = Field(default_factory=dict)


class Dataset(BaseEntity):
    """
    A complete collection of training examples ready for export.

    Example:
        - Name: "Complete Science Study Pack"
        - Description: "Everything needed for the science test"
        - Examples: 500 questions and answers
        - Splits: 80% for training, 10% for validation, 10% for testing
    """
    name: str
    description: str
    examples: List[TrainingExample] = Field(default_factory=list)
    total_examples: int = 0
    train_split: float = 0.8
    validation_split: float = 0.1
    test_split: float = 0.1


# =============================================================================
# QUALITY FAMILY: Our Inspectors
# =============================================================================

class QualityReport(BaseEntity):
    """
    Report card with quality scores for a dataset or example.

    Example:
        - Student: "Math Test #3"
        - Overall Grade: 87%
        - Passed: Yes
        - Detailed Grades: Addition: 95%, Subtraction: 90%, Word Problems: 75%
        - Issues: "Needs to show more work on problem #7"
        - Warnings: "Watch out for careless mistakes"
    """
    target_id: UUID
    overall_score: float
    passed: bool
    metric_scores: Dict[str, float] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# OPERATIONS FAMILY: Our Factory Managers
# =============================================================================

class ProcessingJob(BaseEntity):
    """
    Work order tracking for batch processing operations.

    Example:
        - Order: "Large Pepperoni Pizza for Smith Family"
        - Type: "Food Delivery"
        - Status: "Out for Delivery"
        - Progress: "Delivered 8 out of 10 orders"
        - Started: "6:30 PM"
        - Estimated Arrival: "7:15 PM"
    """
    name: str
    job_type: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    total_items: int = 0
    processed_items: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None