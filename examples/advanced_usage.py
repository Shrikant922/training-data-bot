"""
Advanced Usage Example - Training Data Bot

Demonstrates advanced features like custom templates, quality filtering,
and working with individual components.
"""

import asyncio
from uuid import uuid4

from training_data_bot import (
    TrainingDataBot,
    QAGenerator,
    ClassificationGenerator,
    TextPreprocessor,
    QualityEvaluator,
)
from training_data_bot.core.models import TaskTemplate, TaskType


async def custom_template_example():
    """Using custom task templates."""
    print("=" * 60)
    print("Custom Template Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        # Create a custom template for instruction-following
        custom_template = TaskTemplate(
            id=uuid4(),
            name="Instruction Following",
            task_type=TaskType.INSTRUCTION_RESPONSE,
            description="Generate instruction-response pairs",
            prompt_template="""Generate an instruction and response based on this text.

The instruction should ask the model to do something related to the content.
The response should fulfill that instruction.

Text:
{text}

Format:
Instruction: [instruction]
Response: [response]""",
            parameters={
                "temperature": 0.7,
                "max_tokens": 800
            }
        )

        # Register the template
        bot.task_manager.register_template(custom_template)

        print("✅ Custom template registered")


async def component_usage_example():
    """Using individual components directly."""
    print("\n" + "=" * 60)
    print("Component Usage Example")
    print("=" * 60)

    # 1. Text Preprocessing
    print("\n1️⃣ Text Preprocessing:")
    preprocessor = TextPreprocessor(aggressive=False)

    raw_text = "This   is  some    messy     text!!!!   "
    clean_text = preprocessor.preprocess(raw_text)
    print(f"  Raw: '{raw_text}'")
    print(f"  Clean: '{clean_text}'")

    # 2. Quality Evaluation
    print("\n2️⃣ Quality Evaluation:")
    evaluator = QualityEvaluator(threshold=0.7)

    from training_data_bot.core.models import TrainingExample
    example = TrainingExample(
        input_text="What is Python?",
        output_text="Python is a high-level programming language.",
        task_type=TaskType.QA_GENERATION,
        source_document_id=uuid4()
    )

    report = await evaluator.evaluate_example(example)
    print(f"  Quality score: {report.overall_score:.2f}")
    print(f"  Passed: {report.passed}")

    # 3. Direct QA Generation
    print("\n3️⃣ Direct QA Generation:")
    from training_data_bot.tasks import TaskManager
    from training_data_bot.core.models import TextChunk, Document

    # Create a sample document and chunk
    doc = Document(
        title="AI Basics",
        content="Artificial Intelligence is the simulation of human intelligence by machines.",
        source="sample.txt",
        doc_type="txt",
        word_count=10,
        char_count=100
    )

    chunk = TextChunk(
        document_id=doc.id,
        content=doc.content,
        start_index=0,
        end_index=len(doc.content),
        chunk_index=0,
        token_count=20
    )

    task_manager = TaskManager()
    qa_gen = QAGenerator(task_manager=task_manager)

    examples = await qa_gen.generate_from_chunk(chunk, num_questions=2)
    print(f"  Generated {len(examples)} Q&A pairs")

    await task_manager.close()


async def batch_processing_example():
    """Processing multiple documents in batches."""
    print("\n" + "=" * 60)
    print("Batch Processing Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        # Load multiple document sources
        sources = [
            "doc1.txt",
            "doc2.pdf",
            "https://example.com/article1",
            "https://example.com/article2",
        ]

        print(f"\n📚 Loading {len(sources)} sources...")
        documents = await bot.load_documents(sources, max_workers=4)
        print(f"✅ Loaded {len(documents)} documents")

        # Process each document type differently
        pdf_docs = [d for d in documents if d.doc_type.value == "pdf"]
        web_docs = [d for d in documents if d.doc_type.value == "url"]

        if pdf_docs:
            print(f"\n📄 Processing {len(pdf_docs)} PDFs for summarization...")
            pdf_dataset = await bot.process_documents(
                pdf_docs,
                task_type="summarization",
                task_config={"style": "detailed"}
            )
            await bot.export_dataset(pdf_dataset, "output/pdf_summaries.jsonl")

        if web_docs:
            print(f"\n🌐 Processing {len(web_docs)} web pages for Q&A...")
            web_dataset = await bot.process_documents(
                web_docs,
                task_type="qa_generation"
            )
            await bot.export_dataset(web_dataset, "output/web_qa.jsonl")


async def quality_filtering_example():
    """Advanced quality filtering."""
    print("\n" + "=" * 60)
    print("Quality Filtering Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        documents = await bot.load_documents(["sample.txt"])

        # Generate dataset without filtering
        print("\n🔄 Generating dataset (no filtering)...")
        dataset = await bot.process_documents(
            documents,
            task_type="qa_generation",
            filter_quality=False
        )
        print(f"  Total examples: {len(dataset.examples)}")

        # Evaluate
        report = await bot.evaluate_dataset(dataset)
        print(f"  Quality score: {report['overall_score']:.2f}")

        # Apply custom filtering
        print("\n🔍 Applying custom quality filter (min_score=0.8)...")
        filtered_dataset = await bot.evaluator.filter_dataset(
            dataset,
            min_score=0.8
        )
        print(f"  After filtering: {len(filtered_dataset.examples)} examples")

        # Export both versions
        await bot.export_dataset(dataset, "output/unfiltered.jsonl")
        await bot.export_dataset(filtered_dataset, "output/filtered.jsonl")


async def main():
    """Run all advanced examples."""
    try:
        await custom_template_example()
        await component_usage_example()
        # await batch_processing_example()  # Uncomment to run
        # await quality_filtering_example()  # Uncomment to run

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
