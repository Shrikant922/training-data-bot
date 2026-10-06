"""
Basic Usage Example - Training Data Bot

This example demonstrates the basic usage of the Training Data Bot
to create training datasets from various document sources.
"""

import asyncio
from training_data_bot import TrainingDataBot


async def basic_example():
    """Basic usage example."""
    print("=" * 60)
    print("Training Data Bot - Basic Example")
    print("=" * 60)

    # Initialize the bot
    async with TrainingDataBot() as bot:

        # Example 1: Load documents from various sources
        print("\n📚 Loading documents...")
        documents = await bot.load_documents([
            "sample.pdf",           # PDF file
            "notes.txt",            # Text file
            "https://example.com",  # Website
        ])
        print(f"✅ Loaded {len(documents)} documents")

        # Example 2: Process documents into Q&A training data
        print("\n🔄 Processing documents for Q&A generation...")
        qa_dataset = await bot.process_documents(
            documents,
            task_type="qa_generation",
            filter_quality=True
        )
        print(f"✅ Generated {len(qa_dataset.examples)} Q&A pairs")

        # Example 3: Export to JSONL format
        print("\n💾 Exporting dataset...")
        output_path = await bot.export_dataset(
            qa_dataset,
            "output/training_qa.jsonl",
            format="jsonl"
        )
        print(f"✅ Exported to: {output_path}")

        # Example 4: Get statistics
        stats = bot.get_statistics()
        print("\n📊 Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")


async def quick_process_example():
    """One-liner quick processing example."""
    print("\n" + "=" * 60)
    print("Quick Process Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        # One line: load → process → export
        dataset = await bot.quick_process(
            source="documents/",
            output_path="output/training_data.jsonl",
            task_type="qa_generation"
        )
        print(f"✅ Quick process complete: {len(dataset.examples)} examples")


async def classification_example():
    """Classification training data example."""
    print("\n" + "=" * 60)
    print("Classification Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        # Load documents
        documents = await bot.load_documents(["reviews.txt"])

        # Process for classification
        dataset = await bot.process_documents(
            documents,
            task_type="classification",
            task_config={
                "categories": ["positive", "negative", "neutral"],
                "max_concurrent": 5
            }
        )
        print(f"✅ Generated {len(dataset.examples)} classification examples")

        # Evaluate quality
        report = await bot.evaluate_dataset(dataset)
        print(f"📊 Quality score: {report['overall_score']:.2f}")
        print(f"📊 Passed: {report['passed']}")

        # Export
        await bot.export_dataset(dataset, "output/classification.jsonl")


async def summarization_example():
    """Summarization training data example."""
    print("\n" + "=" * 60)
    print("Summarization Example")
    print("=" * 60)

    async with TrainingDataBot() as bot:
        # Load documents
        documents = await bot.load_documents(["articles/"])

        # Process for summarization
        dataset = await bot.process_documents(
            documents,
            task_type="summarization",
            task_config={
                "style": "concise",  # or "detailed", "bullet_points"
                "max_concurrent": 5
            }
        )
        print(f"✅ Generated {len(dataset.examples)} summaries")

        # Export with train/val/test split
        paths = await bot.export_dataset(
            dataset,
            output_path="output/",
            format="jsonl",
            split=True
        )
        print(f"✅ Exported split dataset:")
        for split_name, path in paths.items():
            print(f"  {split_name}: {path}")


async def main():
    """Run all examples."""
    try:
        await basic_example()
        # await quick_process_example()  # Uncomment to run
        # await classification_example()  # Uncomment to run
        # await summarization_example()   # Uncomment to run

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
