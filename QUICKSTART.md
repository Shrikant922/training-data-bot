# 🚀 QUICK START GUIDE - Test Your Training Data Bot

**Ready to test?** Follow these simple steps!

---

## ⚡ FASTEST WAY TO TEST (5 Minutes)

### Step 1: Install Dependencies

Open your terminal in the project directory and run:

```bash
pip install pydantic pydantic-settings httpx aiofiles PyMuPDF beautifulsoup4 python-docx python-dotenv rich
```

*OR simply:*
```bash
pip install -r requirements.txt
```

---

### Step 2: Set Up API Key

**You need an API key from OpenAI or Anthropic.**

#### Option A: OpenAI (Recommended for testing)
1. Go to: https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

#### Option B: Anthropic (Claude)
1. Go to: https://console.anthropic.com/
2. Sign up or log in  
3. Get API key from settings
4. Copy the key (starts with `sk-ant-`)

---

### Step 3: Create `.env` File

Create a file named `.env` in your project root:

**For OpenAI:**
```env
TRAINING_DATA_BOT_OPENAI_API_KEY=sk-your-key-here
TRAINING_DATA_BOT_DEFAULT_AI_PROVIDER=openai
```

**For Anthropic:**
```env
TRAINING_DATA_BOT_ANTHROPIC_API_KEY=sk-ant-your-key-here
TRAINING_DATA_BOT_DEFAULT_AI_PROVIDER=anthropic
```

---

### Step 4: Run the Quick Test!

```bash
python quick_test.py
```

**That's it!** 🎉

---

## 📝 What the Test Does

1. ✅ Loads `sample.txt` (already created for you)
2. ✅ Generates Q&A pairs using AI
3. ✅ Exports to `output/test_output.jsonl`
4. ✅ Shows you the results!

---

## 📊 Expected Output

```
======================================================================
🤖 TRAINING DATA BOT - QUICK TEST
======================================================================

🔧 Initializing Training Data Bot...

📚 Test 1: Loading document...
   ✅ Loaded 1 document(s)
      Title: sample
      Type: txt
      Words: 589

🔄 Test 2: Generating Q&A pairs...
   (This will call the AI API - please wait...)
   ✅ Generated 5 Q&A pairs

   Sample Q&A:
   Q: What is Machine Learning?
   A: Machine Learning is a subset of artificial intelligence...

💾 Test 3: Exporting dataset...
   ✅ Exported to: output\test_output.jsonl

📊 Test 4: Getting statistics...
   documents_loaded: 1
   datasets_created: 1
   total_examples: 5
   jobs_running: 0

======================================================================
✅ ALL TESTS PASSED!
======================================================================
```

---

## 🎯 Next Steps After Successful Test

### Try Different Task Types:

**1. Classification:**
```python
import asyncio
from training_data_bot import TrainingDataBot

async def test_classification():
    async with TrainingDataBot() as bot:
        docs = await bot.load_documents(["sample.txt"])
        dataset = await bot.process_documents(
            docs,
            task_type="classification",
            task_config={"categories": ["technical", "educational", "general"]}
        )
        await bot.export_dataset(dataset, "output/classification.jsonl")
        print(f"✅ Generated {len(dataset.examples)} classifications")

asyncio.run(test_classification())
```

**2. Summarization:**
```python
async def test_summarization():
    async with TrainingDataBot() as bot:
        docs = await bot.load_documents(["sample.txt"])
        dataset = await bot.process_documents(
            docs,
            task_type="summarization",
            task_config={"style": "concise"}
        )
        await bot.export_dataset(dataset, "output/summaries.jsonl")
        print(f"✅ Generated {len(dataset.examples)} summaries")

asyncio.run(test_summarization())
```

---

## 🧪 Test with Your Own Files

```python
import asyncio
from training_data_bot import TrainingDataBot

async def test_your_files():
    async with TrainingDataBot() as bot:
        # Load YOUR files
        docs = await bot.load_documents([
            "your_document.pdf",
            "your_notes.txt",
            "https://your-favorite-website.com"
        ])
        
        # Process them
        dataset = await bot.process_documents(docs, task_type="qa_generation")
        
        # Export
        await bot.export_dataset(dataset, "output/my_training_data.jsonl")
        print(f"✅ Created {len(dataset.examples)} examples!")

asyncio.run(test_your_files())
```

---

## 🐛 Troubleshooting

### Problem: "No module named 'training_data_bot'"
**Solution:**
```bash
pip install -e .
```

### Problem: "API key not found"
**Solution:**
- Check your `.env` file exists
- Make sure the key doesn't have extra spaces
- Verify the key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)

### Problem: "File not found: sample.txt"
**Solution:**
- Make sure you're running from the project root directory
- Check if `sample.txt` exists (it should be created automatically)
- Use absolute path: `r"S:\JavaScript Projects\Training Data Bot\sample.txt"`

### Problem: Rate limit or timeout errors
**Solution:**
- Wait a few minutes
- Try with a smaller file
- Reduce concurrent requests in task_config

---

## 📖 View Your Results

After running tests, check the output:

```bash
# View the JSONL file
cat output/test_output.jsonl

# Or open in your text editor
notepad output/test_output.jsonl
```

Each line is a training example:
```json
{"input": "What is Machine Learning?", "output": "Machine Learning is...", "task_type": "qa_generation"}
```

---

## 🎓 Learn More

- **Full examples**: Check `examples/basic_usage.py` and `examples/advanced_usage.py`
- **Complete guide**: Read `TESTING_GUIDE.md`
- **Documentation**: See `README.md`
- **Architecture**: Check `BUILD_COMPLETE.md`

---

## ✨ You're All Set!

Your Training Data Bot is ready to:
- ✅ Load any document (PDF, DOCX, TXT, URLs, etc.)
- ✅ Generate training data (Q&A, Classification, Summarization)
- ✅ Evaluate quality
- ✅ Export to standard formats

**Happy Testing! 🚀**

---

## 💡 Pro Tips

1. **Start small**: Test with small documents first
2. **Monitor costs**: Each API call costs money (usually cents)
3. **Save outputs**: Keep your generated datasets for reuse
4. **Experiment**: Try different task types and configurations
5. **Read errors**: Error messages usually tell you exactly what's wrong

---

## 📞 Need Help?

1. Check error messages carefully
2. Review `TESTING_GUIDE.md` for detailed troubleshooting
3. Make sure all dependencies are installed
4. Verify API keys are valid and active
5. Try with the simple `sample.txt` first before your own files

**Now go test it!** 🎉
