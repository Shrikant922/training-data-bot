#!/usr/bin/env python3
"""
Training Data Bot - Interactive Menu Interface

Easy-to-use menu system for testing all features without writing code!
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from training_data_bot import TrainingDataBot


# ============================================================================
# MENU DISPLAY
# ============================================================================

def clear_screen():
    """Clear the terminal screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def show_banner():
    """Display the welcome banner."""
    print("\n" + "=" * 70)
    print("  TRAINING DATA BOT - Interactive Menu")
    print("=" * 70)


def show_main_menu():
    """Display the main menu."""
    show_banner()
    print("\nWhat would you like to do?\n")
    print("  [1] Generate Q&A Pairs")
    print("  [2] Generate Summaries")
    print("  [3] Generate Classifications")
    print("  [4] Load Multiple Sources")
    print("  [5] Quick Test (sample.txt)")
    print("  [6] View Statistics")
    print("  [7] Help & Examples")
    print("  [0] Exit")
    print("\n" + "-" * 70)


def show_source_menu():
    """Display source selection menu."""
    print("\nHow would you like to load your data?\n")
    print("  [1] Website URL")
    print("  [2] Local File (PDF, DOCX, TXT, etc.)")
    print("  [3] Multiple URLs")
    print("  [4] Directory (all files)")
    print("  [5] Mix Files and URLs")
    print("  [0] Back to Main Menu")
    print("\n" + "-" * 70)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_input(prompt, default=None):
    """Get user input with optional default value."""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        result = user_input if user_input else default
        # Ensure path starts with output/ if it's a filename
        if result and not result.startswith(('output/', 'output\\')) and result.endswith('.jsonl'):
            result = f"output/{result}"
        return result
    return input(f"{prompt}: ").strip()


def ensure_output_dir():
    """Ensure output directory exists."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    return output_dir


def get_choice(max_choice):
    """Get a menu choice from user."""
    while True:
        try:
            choice = input("\nEnter your choice: ").strip()
            choice_num = int(choice)
            if 0 <= choice_num <= max_choice:
                return choice_num
            print(f"Please enter a number between 0 and {max_choice}")
        except ValueError:
            print("Please enter a valid number")


def pause():
    """Wait for user to press Enter."""
    input("\nPress Enter to continue...")


# ============================================================================
# FEATURE 1: Q&A GENERATION
# ============================================================================

async def generate_qa():
    """Generate Q&A pairs from user input."""
    clear_screen()
    show_banner()
    print("\n[*] Q&A GENERATION")
    print("-" * 70)

    # Get source
    show_source_menu()
    source_choice = get_choice(5)

    if source_choice == 0:
        return

    sources = []

    if source_choice == 1:
        # Single URL
        url = get_input("\nEnter website URL", "https://en.wikipedia.org/wiki/Python_(programming_language)")
        sources = [url]

    elif source_choice == 2:
        # Single file
        filepath = get_input("\nEnter file path", "sample.txt")
        sources = [filepath]

    elif source_choice == 3:
        # Multiple URLs
        print("\nEnter URLs (one per line, empty line to finish):")
        while True:
            url = input("  URL: ").strip()
            if not url:
                break
            sources.append(url)

    elif source_choice == 4:
        # Directory
        directory = get_input("\nEnter directory path", ".")
        sources = [directory]

    elif source_choice == 5:
        # Mixed
        print("\nEnter sources (one per line, empty line to finish):")
        print("  (Can be URLs or file paths)")
        while True:
            source = input("  Source: ").strip()
            if not source:
                break
            sources.append(source)

    if not sources:
        print("\n[!] No sources provided!")
        pause()
        return

    # Get output filename
    ensure_output_dir()  # Make sure output folder exists
    output_file = get_input("\nOutput filename", "output/qa_pairs.jsonl")

    # Process
    print("\n" + "=" * 70)
    print("Processing...")
    print("=" * 70)

    try:
        async with TrainingDataBot() as bot:
            print(f"\n[1/3] Loading {len(sources)} source(s)...")
            documents = await bot.load_documents(sources)
            print(f"      [OK] Loaded {len(documents)} document(s)")

            for doc in documents[:5]:  # Show first 5
                print(f"      - {doc.title} ({doc.word_count} words)")

            print(f"\n[2/3] Generating Q&A pairs...")
            dataset = await bot.process_documents(
                documents,
                task_type="qa_generation"
            )
            print(f"      [OK] Generated {len(dataset.examples)} Q&A pairs")

            # Check if empty
            if len(dataset.examples) == 0:
                print("\n      [!] WARNING: No examples were generated!")
                print("      This could mean:")
                print("        - The document was too short or empty")
                print("        - API error occurred")
                print("        - All examples were filtered out")
                pause()
                return

            # Show samples
            if dataset.examples:
                print("\n      Sample Q&A:")
                for i, ex in enumerate(dataset.examples[:2], 1):
                    print(f"\n      Q{i}: {ex.input_text[:60]}...")
                    print(f"      A{i}: {ex.output_text[:60]}...")

            print(f"\n[3/3] Exporting to {output_file}...")
            await bot.export_dataset(dataset, output_file)
            print(f"      [OK] Saved successfully!")

            print("\n" + "=" * 70)
            print(f"SUCCESS! Created {len(dataset.examples)} Q&A pairs")
            print(f"Output: {output_file}")
            print("=" * 70)

    except Exception as e:
        print(f"\n[X] Error: {e}")
        import traceback
        traceback.print_exc()

    pause()


# ============================================================================
# FEATURE 2: SUMMARIZATION
# ============================================================================

async def generate_summaries():
    """Generate summaries from user input."""
    clear_screen()
    show_banner()
    print("\n[*] SUMMARIZATION")
    print("-" * 70)

    # Get source (simplified)
    source = get_input("\nEnter source (URL or file path)", "https://en.wikipedia.org/wiki/Machine_learning")

    # Get style
    print("\nSummary style:")
    print("  [1] Concise (2-3 sentences)")
    print("  [2] Detailed (4-6 sentences)")
    print("  [3] Bullet Points")
    style_choice = get_choice(3)

    if style_choice == 0:
        return

    styles = {1: "concise", 2: "detailed", 3: "bullet_points"}
    style = styles.get(style_choice, "concise")

    ensure_output_dir()  # Make sure output folder exists
    output_file = get_input("\nOutput filename", "output/summaries.jsonl")

    # Process
    print("\n" + "=" * 70)
    print("Processing...")
    print("=" * 70)

    try:
        async with TrainingDataBot() as bot:
            print(f"\n[1/3] Loading source...")
            documents = await bot.load_documents([source])
            print(f"      [OK] Loaded: {documents[0].title} ({documents[0].word_count} words)")

            print(f"\n[2/3] Generating summaries ({style} style)...")
            dataset = await bot.process_documents(
                documents,
                task_type="summarization",
                task_config={"style": style}
            )
            print(f"      [OK] Generated {len(dataset.examples)} summaries")

            # Show sample
            if dataset.examples:
                ex = dataset.examples[0]
                print(f"\n      Sample:")
                print(f"      Original: {ex.input_text[:80]}...")
                print(f"      Summary: {ex.output_text[:150]}...")

            print(f"\n[3/3] Exporting...")
            await bot.export_dataset(dataset, output_file)
            print(f"      [OK] Saved to {output_file}")

            print("\n" + "=" * 70)
            print(f"SUCCESS! Created {len(dataset.examples)} summaries")
            print("=" * 70)

    except Exception as e:
        print(f"\n[X] Error: {e}")

    pause()


# ============================================================================
# FEATURE 3: CLASSIFICATION
# ============================================================================

async def generate_classifications():
    """Generate classifications from user input."""
    clear_screen()
    show_banner()
    print("\n[*] CLASSIFICATION")
    print("-" * 70)

    source = get_input("\nEnter source (URL or file path)", "sample.txt")

    # Get categories
    print("\nEnter classification categories (one per line, empty to finish):")
    print("  Examples: technical, business, general")
    print("            positive, negative, neutral")
    categories = []
    while True:
        cat = input("  Category: ").strip()
        if not cat:
            break
        categories.append(cat)

    if not categories:
        categories = ["technical", "educational", "general"]
        print(f"\n[!] Using default categories: {categories}")

    ensure_output_dir()  # Make sure output folder exists
    output_file = get_input("\nOutput filename", "output/classifications.jsonl")

    # Process
    print("\n" + "=" * 70)
    print("Processing...")
    print("=" * 70)

    try:
        async with TrainingDataBot() as bot:
            print(f"\n[1/3] Loading source...")
            documents = await bot.load_documents([source])
            print(f"      [OK] Loaded: {documents[0].title}")

            print(f"\n[2/3] Classifying into: {', '.join(categories)}...")
            dataset = await bot.process_documents(
                documents,
                task_type="classification",
                task_config={"categories": categories}
            )
            print(f"      [OK] Generated {len(dataset.examples)} classifications")

            # Show samples
            if dataset.examples:
                print("\n      Samples:")
                for i, ex in enumerate(dataset.examples[:3], 1):
                    print(f"      {i}. Text: {ex.input_text[:50]}...")
                    print(f"         Category: {ex.output_text}")

            print(f"\n[3/3] Exporting...")
            await bot.export_dataset(dataset, output_file)
            print(f"      [OK] Saved to {output_file}")

            print("\n" + "=" * 70)
            print(f"SUCCESS! Created {len(dataset.examples)} classifications")
            print("=" * 70)

    except Exception as e:
        print(f"\n[X] Error: {e}")

    pause()


# ============================================================================
# FEATURE 4: MULTIPLE SOURCES
# ============================================================================

async def load_multiple_sources():
    """Load and process multiple sources at once."""
    clear_screen()
    show_banner()
    print("\n[*] MULTIPLE SOURCES PROCESSING")
    print("-" * 70)

    print("\nEnter sources (one per line, empty line to finish):")
    print("  Examples:")
    print("    https://wikipedia.org/wiki/Python")
    print("    document.pdf")
    print("    notes.txt")

    sources = []
    while True:
        source = input("  Source: ").strip()
        if not source:
            break
        sources.append(source)

    if not sources:
        print("\n[!] No sources provided!")
        pause()
        return

    # Choose task type
    print("\nTask type:")
    print("  [1] Q&A Generation")
    print("  [2] Summarization")
    print("  [3] Classification")
    task_choice = get_choice(3)

    if task_choice == 0:
        return

    task_types = {1: "qa_generation", 2: "summarization", 3: "classification"}
    task_type = task_types.get(task_choice, "qa_generation")

    ensure_output_dir()  # Make sure output folder exists
    output_file = get_input("\nOutput filename", f"output/multiple_{task_type}.jsonl")

    # Process
    print("\n" + "=" * 70)
    print("Processing...")
    print("=" * 70)

    try:
        async with TrainingDataBot() as bot:
            print(f"\n[1/3] Loading {len(sources)} sources...")
            documents = await bot.load_documents(sources)
            print(f"      [OK] Loaded {len(documents)} documents")

            print(f"\n[2/3] Processing with {task_type}...")
            dataset = await bot.process_documents(documents, task_type=task_type)
            print(f"      [OK] Generated {len(dataset.examples)} examples")

            print(f"\n[3/3] Exporting...")
            await bot.export_dataset(dataset, output_file)
            print(f"      [OK] Saved to {output_file}")

            print("\n" + "=" * 70)
            print(f"SUCCESS! Processed {len(documents)} documents")
            print(f"Created {len(dataset.examples)} examples")
            print("=" * 70)

    except Exception as e:
        print(f"\n[X] Error: {e}")

    pause()


# ============================================================================
# FEATURE 5: QUICK TEST
# ============================================================================

async def quick_test():
    """Run quick test with sample.txt."""
    clear_screen()
    show_banner()
    print("\n[*] QUICK TEST")
    print("-" * 70)
    print("\nThis will test with sample.txt (fast test)")

    # Check if sample.txt exists
    if not Path("sample.txt").exists():
        print("\n[X] sample.txt not found!")
        print("    Please make sure sample.txt exists in the project directory")
        pause()
        return

    print("\nTask type:")
    print("  [1] Q&A Generation")
    print("  [2] Summarization")
    print("  [3] Classification")
    task_choice = get_choice(3)

    if task_choice == 0:
        return

    task_types = {1: "qa_generation", 2: "summarization", 3: "classification"}
    task_type = task_types[task_choice]

    ensure_output_dir()  # Make sure output folder exists

    print("\n" + "=" * 70)
    print("Running quick test...")
    print("=" * 70)

    try:
        async with TrainingDataBot() as bot:
            documents = await bot.load_documents(["sample.txt"])
            dataset = await bot.process_documents(documents, task_type=task_type)
            await bot.export_dataset(dataset, f"output/quick_test_{task_type}.jsonl")

            print(f"\n[OK] Test complete!")
            print(f"     Generated {len(dataset.examples)} examples")
            print(f"     Saved to: output/quick_test_{task_type}.jsonl")

    except Exception as e:
        print(f"\n[X] Error: {e}")

    pause()


# ============================================================================
# FEATURE 6: STATISTICS
# ============================================================================

def show_statistics():
    """Show output directory statistics."""
    clear_screen()
    show_banner()
    print("\n[*] STATISTICS")
    print("-" * 70)

    output_dir = Path("output")

    if not output_dir.exists():
        print("\n[!] Output directory doesn't exist yet")
        print("    Run some tests first to generate data!")
        pause()
        return

    files = list(output_dir.glob("*.jsonl"))

    if not files:
        print("\n[!] No output files found")
        print("    Run some tests to generate training data!")
        pause()
        return

    print(f"\nFound {len(files)} output file(s):\n")

    total_lines = 0
    for f in files:
        line_count = len(f.read_text().strip().split('\n'))
        total_lines += line_count
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name}")
        print(f"    - {line_count} examples")
        print(f"    - {size_kb:.2f} KB")
        print()

    print("-" * 70)
    print(f"TOTAL: {total_lines} training examples across {len(files)} files")
    print("=" * 70)

    pause()


# ============================================================================
# FEATURE 7: HELP
# ============================================================================

def show_help():
    """Show help and examples."""
    clear_screen()
    show_banner()
    print("\n[*] HELP & EXAMPLES")
    print("-" * 70)

    print("""
QUICK START:
1. Choose option [1] for Q&A Generation
2. Select [1] for Website URL
3. Enter a URL (or press Enter for default)
4. Wait for processing
5. Check the output folder!

TASK TYPES:
- Q&A Generation: Creates question-answer pairs
- Summarization: Creates summaries (concise/detailed/bullets)
- Classification: Categorizes text into your categories

INPUT SOURCES:
- Website URLs: https://example.com
- Local files: document.pdf, notes.txt, etc.
- Directories: my_folder/ (loads all files)
- Mix: Combine URLs and files!

OUTPUT:
- All results saved to output/ folder
- JSONL format (one example per line)
- Can be used directly for LLM training

TIPS:
- Start with Quick Test [5] to verify setup
- Check Statistics [6] to see what you've generated
- Use short documents for testing (faster & cheaper)
- Each API call costs a few cents

NEED MORE HELP?
- Check README.md for full documentation
- See examples/ folder for code samples
- Read TESTING_GUIDE.md for detailed instructions
    """)

    pause()


# ============================================================================
# MAIN LOOP
# ============================================================================

async def main():
    """Main menu loop."""
    while True:
        clear_screen()
        show_main_menu()

        choice = get_choice(7)

        if choice == 0:
            print("\nThank you for using Training Data Bot!")
            print("Check the output/ folder for your generated files.\n")
            break

        elif choice == 1:
            await generate_qa()

        elif choice == 2:
            await generate_summaries()

        elif choice == 3:
            await generate_classifications()

        elif choice == 4:
            await load_multiple_sources()

        elif choice == 5:
            await quick_test()

        elif choice == 6:
            show_statistics()

        elif choice == 7:
            show_help()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
