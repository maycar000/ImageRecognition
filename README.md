# AP Classroom Question Extractor 🎓

Automated tool to extract questions, answers, and images from AP Classroom assignments and export them to Quizizz-compatible CSV format with **AI-powered answer detection**.

## ✨ Features

- 📝 **Automated Question Extraction** - Extracts questions and multiple choice answers
- 📸 **Smart Screenshot Capture** - Captures full passage panels with images and text
- 🤖 **AI Answer Detection** - Uses free AI vision models to automatically detect correct answers
- 🌐 **Image Hosting** - Uploads images to ImgBB for easy Quizizz import
- 📊 **Quizizz Export** - Generates CSV files ready for Quizizz import
- ⏸️ **Stop Anytime** - Press ESC to gracefully stop at any point

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- Google Chrome browser
- Tesseract OCR (optional, for advanced features)

### Installation

1. **Clone or download this repository**

2. **Install required packages:**
```bash
pip install selenium webdriver-manager pillow pytesseract requests python-dotenv openai
```

3. **Optional: Install keyboard support (for ESC key stopping):**
```bash
pip install keyboard
```

4. **Install Tesseract OCR** (optional):
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - Mac: `brew install tesseract`
   - Linux: `sudo apt-get install tesseract-ocr`

### Configuration

1. **Run the setup script:**
```bash
python setup.py
```

2. **Enter the required information:**
   - Website URL (your AP Classroom assignment URL)
   - Next button selector (usually default works)
   - Number of questions to extract
   - Wait time between questions (default: 2 seconds)

3. **Optional: Enable AI Answer Detection**
   
   Create a `.env` file in the project directory:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```
   
   Get a free API key from [OpenRouter.ai](https://openrouter.ai/)
   - The script uses Llama 4 Scout which is **100% FREE**
   - No credit card required

## 📖 Usage

### Basic Usage (Without AI)

```bash
python screenshot_automation.py
```

1. Browser will open automatically
2. Log in to AP Classroom
3. Navigate to the FIRST question of your assignment
4. Press ENTER in the terminal to start
5. Script will automatically:
   - Extract each question and answers
   - Capture screenshots of passages/images
   - Click "Next" to move to the next question
6. Press ESC at any time to stop gracefully

### With AI Answer Detection

1. Set up your `.env` file with OpenRouter API key (see Configuration)
2. Run the script normally:
```bash
python screenshot_automation.py
```

The AI will:
- Analyze each question with the passage/image
- Determine the most likely correct answer
- Populate the "Correct Answer" column in the CSV

## 📂 Output Files

After running, you'll get:

1. **CSV File** - `ocr_results_quizizz_TIMESTAMP.csv`
   - Ready for Quizizz import
   - Contains questions, options, and image links
   - Includes AI-detected answers (if enabled)

2. **Images Folder** - `output/quizizz_images/`
   - All captured screenshots
   - Named by question number

## 🎯 Importing to Quizizz

1. Go to [Quizizz.com](https://quizizz.com)
2. Click **Create** → **Quiz**
3. Click **Import from Spreadsheet**
4. Upload the generated CSV file
5. Images will automatically load from ImgBB URLs
6. Review and publish your quiz!

## 🔧 Configuration Options

Edit `config.py` or run `setup.py` again to change:

- `WEBSITE_URL` - Your AP Classroom URL
- `MAX_CLICKS` - Number of questions to extract
- `WAIT_TIME` - Seconds to wait between questions
- `BUTTON_SELECTOR` - CSS selector for Next button
- `OUTPUT_FOLDER` - Where to save files

## 🤖 AI Models

The script uses **Llama 4 Scout** via OpenRouter:
- ✅ Completely FREE
- ✅ Supports vision (can analyze images)
- ✅ No credit card required
- ✅ Great for AP exam questions

## 🛠️ Troubleshooting

### "No API key" warning
- This is normal if you haven't set up AI
- Script works fine without AI, just no automatic answer detection

### Screenshots not capturing full panels
- Ensure browser zoom is set to 50% (script does this automatically)
- Try increasing `WAIT_TIME` in config

### AI giving wrong answers
- AI is not perfect, always review answers before using
- Some questions require very specific knowledge
- Consider manually verifying important questions

### "Cannot click Next" error
- Check if you've reached the last question
- Verify the BUTTON_SELECTOR in config.py is correct
- Try increasing WAIT_TIME

### Browser not opening
- Ensure Chrome is installed
- Try: `pip install --upgrade selenium webdriver-manager`

### Images not uploading
- Check your internet connection
- ImgBB may have rate limits, wait a few minutes

## 📊 Success Rates

Typical performance:
- **Question Extraction**: 95%+ success rate
- **Screenshot Capture**: 90%+ full panels captured
- **AI Answer Detection**: 60-80% accuracy (varies by subject)

## ⚠️ Important Notes

- **Educational Use Only**: This tool is for personal study and organization
- **Review AI Answers**: Always verify AI-detected answers before using
- **Respect Rate Limits**: Don't run the script too frequently
- **AP Classroom Terms**: Ensure your use complies with College Board's terms

## 🔒 Privacy & Security

- API keys stored locally in `.env` file only
- Images uploaded to ImgBB (publicly accessible URLs)
- No data is stored by the script developer
- OpenRouter doesn't store conversation data

## 📝 File Structure

```
project/
├── screenshot_automation.py    # Main script
├── config.py                   # Configuration file
├── setup.py                    # Setup wizard
├── .env                        # API keys (create this)
├── output/                     # Output folder
│   ├── quizizz_images/        # Screenshots
│   └── ocr_results_*.csv      # CSV exports
└── README.md                   # This file
```

## 🐛 Known Issues

1. **AI occasionally gives explanations instead of numbers**
   - Prompt has been optimized to minimize this
   - Parser will try to extract the number anyway

2. **Some complex images may not capture properly**
   - Fallback captures individual images
   - Usually sufficient for AI analysis

3. **Rate limiting on free AI tier**
   - Script automatically retries after 10 seconds
   - Very rarely an issue with normal use

## 🤝 Contributing

Found a bug or have a suggestion? Please let us know!

## 📄 License

This project is provided as-is for educational purposes.

## 🎓 Best Practices

1. **Start Small**: Test with 5-10 questions first
2. **Review Output**: Always check the CSV before importing
3. **Manual Verification**: Verify AI answers, especially for important quizzes
4. **Save Backups**: Keep the original AP Classroom assignments
5. **Stable Internet**: Ensure good connection for image uploads

## 🚀 Advanced Tips

### Optimizing AI Accuracy
- Ensure screenshots capture full passages (not just images)
- Higher quality images = better AI analysis
- Some subjects work better than others (History > Math)

### Batch Processing
- Run multiple assignments separately
- Combine CSVs later if needed
- Keep question numbers organized

### Custom Configurations
- Adjust `temperature` in AI code for different behavior
- Modify screenshot strategies for different layouts
- Change ImgBB API key if you hit limits

## 📞 Support

For issues:
1. Check the Troubleshooting section
2. Review terminal output for error messages
3. Ensure all dependencies are installed
4. Try running with default settings

---

**Happy Learning! 🎉**

*Remember: This tool is meant to help you study more efficiently. Always review and understand the content yourself!*
