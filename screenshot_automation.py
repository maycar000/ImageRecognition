from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageEnhance
import pytesseract
import time
import os
import re
import csv

# Import config
try:
    import config
    WEBSITE_URL = config.WEBSITE_URL
    BUTTON_SELECTOR = config.BUTTON_SELECTOR
    SELECTOR_TYPE = config.SELECTOR_TYPE
    MAX_CLICKS = config.MAX_CLICKS
    WAIT_TIME = config.WAIT_TIME
    TESSERACT_PATH = config.TESSERACT_PATH
    OUTPUT_FOLDER = config.OUTPUT_FOLDER
    OCR_RESULTS_FILE = config.OCR_RESULTS_FILE
except ImportError:
    print("❌ config.py not found! Run setup.py first.")
    exit(1)

class APClassroomOCR:
    def __init__(self, tesseract_path=None):
        """Initialize with settings optimized for text extraction"""
        
        # Set up Tesseract
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif os.name == 'nt':
            default_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(default_path):
                pytesseract.pytesseract.tesseract_cmd = default_path
        
        # Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--force-device-scale-factor=1.5')
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
        
        self.ocr_results = []
    
    def navigate_to_url(self, url):
        """Navigate to website"""
        self.driver.get(url)
        time.sleep(3)
    
    def wait_for_load(self):
        """Wait for page to fully load"""
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1.5)
    
    def clean_text(self, text):
        """Clean text by removing/replacing problematic characters"""
        if not text:
            return text
            
        # Replace common problematic Unicode characters
        replacements = {
            'â€™': "'",   # Curly apostrophe
            'â€œ': '"',   # Left double quote
            'â€': '"',    # Right double quote
            'â€˜': "'",   # Left single quote
            'â€¦': '...', # Ellipsis
            'â€”': '—',   # Em dash
            'â€“': '–',   # En dash
            'â€¢': '•',   # Bullet
            'â€¡': '‡',   # Double dagger
            'â€°': '‰',   # Per mille
            'â€¹': '‹',   # Single left-pointing angle quotation
            'â€º': '›',   # Single right-pointing angle quotation
            'Ã©': 'é',    # e acute
            'Ã¨': 'è',    # e grave
            'Ãª': 'ê',    # e circumflex
            'Ã±': 'ñ',    # n tilde
            'Ã³': 'ó',    # o acute
            'Ã¶': 'ö',    # o umlaut
            'Ã¼': 'ü',    # u umlaut
            'Ã¡': 'á',    # a acute
            'Ã¢': 'â',    # a circumflex
            'Ã£': 'ã',    # a tilde
            'Ã¤': 'ä',    # a umlaut
            'Ã»': 'û',    # u circumflex
            'Ã»': 'û',    # u circumflex
            'Ã§': 'ç',    # c cedilla
        }
        
        cleaned_text = text
        for bad_char, good_char in replacements.items():
            cleaned_text = cleaned_text.replace(bad_char, good_char)
        
        return cleaned_text
    
    def extract_question_and_answers(self):
        """
        Extract ONLY the currently visible question and answers
        """
        try:
            # Wait for content to load
            time.sleep(2)
            
            script = """
            function extractCurrentQuestionData() {
                let result = {question: '', answers: [], debug: {}};
                
                // DIRECT APPROACH: Find the currently visible question container
                const allQuestionContainers = document.querySelectorAll('.learnosity-item, [class*="question"], .lrn-assessment-wrapper, .lrn_assessment');
                let activeContainer = null;
                
                for (let container of allQuestionContainers) {
                    const style = window.getComputedStyle(container);
                    const rect = container.getBoundingClientRect();
                    
                    // Check if container is actually visible and has substantial size
                    const isVisible = style.display !== 'none' && 
                                     style.visibility !== 'hidden' && 
                                     style.opacity !== '0' &&
                                     rect.width > 100 && 
                                     rect.height > 100 &&
                                     rect.top >= 0 &&
                                     rect.top < window.innerHeight;
                    
                    if (isVisible) {
                        // Additional check: container should have question content
                        const hasStimulus = container.querySelector('.lrn_stimulus_content');
                        const hasRadioInputs = container.querySelector('input[type="radio"]');
                        
                        if (hasStimulus || hasRadioInputs) {
                            activeContainer = container;
                            break;
                        }
                    }
                }
                
                result.debug.containerFound = !!activeContainer;
                result.debug.totalContainers = allQuestionContainers.length;
                
                if (activeContainer) {
                    // Extract question text
                    const stimulusContent = activeContainer.querySelector('.lrn_stimulus_content');
                    
                    if (stimulusContent) {
                        const paragraphs = stimulusContent.querySelectorAll('p');
                        
                        for (let p of paragraphs) {
                            const text = p.innerText || p.textContent || '';
                            if (text.trim().length > 20) {
                                if (text.includes('?') || text.includes('following')) {
                                    result.question = text.trim();
                                    break;
                                } else if (!result.question) {
                                    result.question = text.trim();
                                }
                            }
                        }
                        
                        // Fallback: get any text from stimulus
                        if (!result.question) {
                            result.question = stimulusContent.innerText || stimulusContent.textContent || '';
                            result.question = result.question.trim().substring(0, 200); // Limit length
                        }
                        
                        result.debug.foundStimulus = true;
                        result.debug.paragraphCount = paragraphs.length;
                    }
                    
                    // Extract answers from this container only
                    const radioInputs = activeContainer.querySelectorAll('input[type="radio"]');
                    result.debug.foundInputs = radioInputs.length;
                    
                    const seenAnswers = new Set();
                    
                    for (let input of radioInputs) {
                        const label = document.querySelector(`label[for="${input.id}"]`);
                        
                        if (label) {
                            const possibleAnswer = label.querySelector('.lrn-possible-answer');
                            
                            if (possibleAnswer) {
                                const contentWrappers = possibleAnswer.querySelectorAll('.lrn_contentWrapper');
                                
                                for (let wrapper of contentWrappers) {
                                    if (wrapper.closest('.sr-only')) {
                                        continue;
                                    }
                                    
                                    const p = wrapper.querySelector('p');
                                    if (p) {
                                        const text = (p.innerText || p.textContent || '').trim();
                                        
                                        if (text.length > 2 && !seenAnswers.has(text) && !/^[A-E]$/.test(text)) {
                                            seenAnswers.add(text);
                                            result.answers.push(text);
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    result.answers = result.answers.slice(0, 5);
                    result.debug.answerCount = result.answers.length;
                    result.debug.questionLength = result.question.length;
                    
                    // Try to find question number
                    const questionNumElement = activeContainer.querySelector('.item-number');
                    if (questionNumElement) {
                        const numText = questionNumElement.innerText.trim();
                        if (numText && !isNaN(numText)) {
                            result.debug.currentQuestion = parseInt(numText);
                        }
                    }
                } else {
                    result.debug.error = "No active container found";
                }
                
                return result;
            }
            
            return extractCurrentQuestionData();
            """
            
            data = self.driver.execute_script(script)
            
            # Debug output
            print(f"   [DEBUG] Total containers: {data['debug'].get('totalContainers', 0)}")
            print(f"   [DEBUG] Container found: {data['debug'].get('containerFound', False)}")
            print(f"   [DEBUG] Current question: {data['debug'].get('currentQuestion', 'Unknown')}")
            print(f"   [DEBUG] Stimulus: {data['debug'].get('foundStimulus', False)}")
            print(f"   [DEBUG] Radio inputs: {data['debug'].get('foundInputs', 0)}")
            print(f"   [DEBUG] Answers: {data['debug'].get('answerCount', 0)}")
            print(f"   [DEBUG] Q length: {data['debug'].get('questionLength', 0)}")
            
            if 'error' in data['debug']:
                print(f"   ❌ {data['debug']['error']}")
            
            # Validate data with more lenient criteria
            if not data['question'] or len(data['question']) < 10:
                print(f"   ❌ Question too short or missing")
                return None
                
            if not data['answers'] or len(data['answers']) < 2:
                print(f"   ❌ Need at least 2 answers (found {len(data['answers'])})")
                return None
            
            # CLEAN THE TEXT HERE - this is the key fix!
            cleaned_question = self.clean_text(data['question'])
            cleaned_answers = [self.clean_text(answer) for answer in data['answers']]
            
            # Format output with cleaned text
            question_num = data['debug'].get('currentQuestion', 'Unknown')
            formatted = f"{cleaned_question}\n\n"
            
            # Add answers with letters
            letters = ['A', 'B', 'C', 'D', 'E']
            for idx, ans in enumerate(cleaned_answers[:5]):
                formatted += f"{letters[idx]}. {ans}\n"
            
            return formatted
            
        except Exception as e:
            print(f"  ⚠ Extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_automation(self, max_clicks, wait_time, output_folder):
        """Main automation loop"""
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'class': By.CLASS_NAME,
        }
        by_method = selector_map.get(SELECTOR_TYPE, By.CSS_SELECTOR)
        
        for i in range(max_clicks):
            print(f"\n{'='*70}")
            print(f"📝 QUESTION {i + 1}/{max_clicks}")
            print(f"{'='*70}")
            
            # Wait for page load
            self.wait_for_load()
            time.sleep(wait_time)
            
            # Extract content
            print(f"   🔍 Extracting content...")
            extracted_text = self.extract_question_and_answers()
            
            if extracted_text:
                self.ocr_results.append({
                    'question_num': i + 1,
                    'text': extracted_text
                })
                print(f"   ✅ Successfully extracted!")
                
                # Show preview
                lines = extracted_text.split('\n')
                preview = lines[0][:60] + "..." if len(lines[0]) > 60 else lines[0]
                print(f"   📄 {preview}")
            else:
                print(f"   ❌ Extraction failed")
                self.ocr_results.append({
                    'question_num': i + 1,
                    'text': f"[Question {i + 1} - Extraction Failed]\n\n"
                })
            
            # Click next
            if i < max_clicks - 1:
                try:
                    print(f"   ⏭  Clicking Next...")
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by_method, BUTTON_SELECTOR))
                    )
                    next_btn.click()
                    time.sleep(2)
                    print(f"   ✓ Next question loaded")
                except Exception as e:
                    print(f"   ⚠ Cannot click Next: {e}")
                    print(f"   Stopping...")
                    break
    
    def save_results_txt(self, output_file):
        """Save results in clean text format"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("AP CLASSROOM - QUESTIONS & ANSWERS\n")
            f.write("=" * 80 + "\n\n")
            
            for result in self.ocr_results:
                f.write(f"QUESTION {result['question_num']}\n")
                f.write("-" * 80 + "\n")
                f.write(result['text'])
                f.write("\n")
        
        print(f"\n💾 Saved TXT: {output_file}")
    
    def save_results_csv(self, output_file):
        """Save results in CSV format for Blooket import with ALL 5 answers"""
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Write header row with ALL 5 answers + CorrectAnswer column
            writer.writerow(['Question', 'Answer1', 'Answer2', 'Answer3', 'Answer4', 'Answer5', 'CorrectAnswer'])
            
            for result in self.ocr_results:
                if result['text'].startswith('[Question'):
                    continue  # Skip failed extractions
                
                # Parse the question and answers from the text
                lines = result['text'].strip().split('\n')
                if len(lines) < 3:
                    continue
                
                question = lines[0].strip()  # Already cleaned during extraction
                answers = []
                
                # Extract answers (A, B, C, D, E)
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith(('A.', 'B.', 'C.', 'D.', 'E.')):
                        answer_text = line[2:].strip()  # Remove "A. ", "B. ", etc.
                        answers.append(answer_text)  # Already cleaned during extraction
                
                # Ensure we have exactly 5 answer columns (fill empty if needed)
                while len(answers) < 5:
                    answers.append("")
                
                # Keep only first 5 answers if there are more
                answers = answers[:5]
                
                # Leave CorrectAnswer column EMPTY for user to fill in
                correct_answer = ""
                
                # Write to CSV (Question, 5 answers, empty correct answer)
                writer.writerow([question, answers[0], answers[1], answers[2], answers[3], answers[4], correct_answer])
        
        print(f"\n💾 Saved CSV: {output_file}")
        print("📋 CSV Format: Ready for Blooket import!")
        print("   Columns: Question, Answer1, Answer2, Answer3, Answer4, Answer5, CorrectAnswer")
        print("   Note: CorrectAnswer column is left EMPTY for you to fill in")
        print("   Blooket will use Answer1-Answer4, but all 5 are preserved for your reference")
    
    def cleanup(self):
        """Close browser"""
        self.driver.quit()


def main():
    print("=" * 80)
    print("AP CLASSROOM EXTRACTOR - WITH BLOOKET CSV EXPORT")
    print("=" * 80)
    
    ocr = APClassroomOCR(tesseract_path=TESSERACT_PATH)
    
    try:
        print(f"\n🌐 Opening: {WEBSITE_URL}")
        ocr.navigate_to_url(WEBSITE_URL)
        
        # Pause for login
        print("\n" + "=" * 80)
        print("⚠️  SETUP:")
        print("    1. Log in to AP Classroom")
        print("    2. Go to the FIRST question")
        print("    3. Wait for it to fully load")
        print("    4. Press ENTER to start")
        print("=" * 80)
        input()
        
        print(f"\n▶  Starting...")
        print(f"    Questions: {MAX_CLICKS}")
        print(f"    Wait: {WAIT_TIME}s\n")
        
        # Run automation
        ocr.run_automation(MAX_CLICKS, WAIT_TIME, OUTPUT_FOLDER)
        
        # Ask user for output format
        print("\n" + "=" * 80)
        print("📁 OUTPUT FORMAT SELECTION")
        print("=" * 80)
        print("Choose output format:")
        print("  1. TXT file (readable format)")
        print("  2. CSV file (for Blooket import)")
        print("  3. BOTH files")
        
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
        
        # Generate base filename without extension
        base_output_path = os.path.splitext(OCR_RESULTS_FILE)[0]
        
        if choice == '1':
            # Save as TXT only
            txt_file = f"{base_output_path}.txt"
            ocr.save_results_txt(txt_file)
        elif choice == '2':
            # Save as CSV only
            csv_file = f"{base_output_path}.csv"
            ocr.save_results_csv(csv_file)
        elif choice == '3':
            # Save both formats
            txt_file = f"{base_output_path}.txt"
            csv_file = f"{base_output_path}.csv"
            ocr.save_results_txt(txt_file)
            ocr.save_results_csv(csv_file)
        else:
            print("❌ Invalid choice. Saving as TXT by default.")
            txt_file = f"{base_output_path}.txt"
            ocr.save_results_txt(txt_file)
        
        # Summary
        successful = len([r for r in ocr.ocr_results if not r['text'].startswith('[Question')])
        failed = len(ocr.ocr_results) - successful
        
        print("\n" + "=" * 80)
        print("✅ DONE!")
        print("=" * 80)
        print(f"✓ Success: {successful}/{len(ocr.ocr_results)}")
        if failed > 0:
            print(f"⚠ Failed: {failed}")
        
        if choice in ['1', '3']:
            print(f"📄 TXT File: {base_output_path}.txt")
        if choice in ['2', '3']:
            print(f"📊 CSV File: {base_output_path}.csv")
            print("\n🎮 BLOOKET IMPORT INSTRUCTIONS:")
            print("   1. Go to Blooket.com")
            print("   2. Create a new set")
            print("   3. Click 'Import from CSV'")
            print("   4. Upload the CSV file")
            print("   5. Review questions and fill in CorrectAnswer column")
            print("   6. Blooket will use Answer1-Answer4, but all 5 answers are preserved")
        
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ocr.cleanup()
        print("\n👋 Closed")

if __name__ == "__main__":
    main()
