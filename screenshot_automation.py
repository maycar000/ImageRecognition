"""
DEBUG VERSION - Shows detailed output to troubleshoot issues
"""
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
import base64
import requests
import datetime
import sys
import io
import json

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed")

# Load Gemini API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

print(f"\n🔑 API Key Status: {'SET ✅' if GEMINI_API_KEY else 'NOT SET ❌'}")
if GEMINI_API_KEY:
    print(f"   Key prefix: {GEMINI_API_KEY[:20]}...")

# Try to import keyboard
KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass

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
    
    print(f"\n📋 Config loaded:")
    print(f"   URL: {WEBSITE_URL}")
    print(f"   Max clicks: {MAX_CLICKS}")
    print(f"   Wait time: {WAIT_TIME}s")
    
except ImportError:
    print("Error: config.py not found! Run setup.py first.")
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
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Initialize driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1920, 1080)
        
        # Set zoom to 50%
        self.driver.execute_script("document.body.style.zoom='50%'")
        print("🔍 Browser zoom set to 50%")
        
        self.ocr_results = []
        self.uploaded_image_urls = {}
        self.imgbb_api_key = "0de54180b4129154bf273314eaf01ef5"
        self.should_stop = False
        self.ai_enabled = GEMINI_API_KEY is not None
        
        print(f"🤖 AI Status: {'ENABLED ✅' if self.ai_enabled else 'DISABLED ❌'}")

    def setup_escape_listener(self):
        """Set up ESC key listener"""
        if not KEYBOARD_AVAILABLE:
            print("    ℹ️  Press Ctrl+C to stop")
            return
            
        def on_esc_pressed():
            print("\n\n🛑 ESC pressed! Stopping...")
            self.should_stop = True
        
        try:
            keyboard.on_press_key('esc', lambda _: on_esc_pressed())
            print("    ℹ️  Press ESC to stop")
        except:
            print("    ℹ️  Press Ctrl+C to stop")

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
        """Clean text"""
        if not text:
            return text
            
        replacements = {
            'â€™': "'",
            'â€œ': '"',
            'â€': '"',
            'â€˜': "'",
            'â€¦': '...',
            'â€"': '–',
            'â€"': '—',
        }
        
        cleaned_text = text
        for bad_char, good_char in replacements.items():
            cleaned_text = cleaned_text.replace(bad_char, good_char)
        
        return cleaned_text
    
    def analyze_all_questions_with_gemini(self, questions_data, retry_count=0):
        """Analyze ALL questions in a single API request"""
        if not self.ai_enabled:
            print("      [AI] Disabled - no API key")
            return {}
        
        if retry_count >= 3:
            print(f"      [AI] ⚠️  Too many rate limits, skipping")
            return {}
            
        try:
            print(f"\n      [AI] Building batch prompt for {len(questions_data)} questions...")
            
            # Build one large prompt with all questions
            prompt_parts = [
                "You are an expert AP exam test-taker. I will give you multiple questions.",
                "For each question, determine the correct answer (1-5).",
                "Respond with ONLY a JSON array of numbers, like: [3, 1, 4, 2, 5]",
                "Use 0 if uncertain. No explanations, just the JSON array.",
                "\n=== QUESTIONS ===\n"
            ]
            
            for idx, q_data in enumerate(questions_data, 1):
                prompt_parts.append(f"\nQUESTION {idx}:")
                prompt_parts.append(q_data['question'])
                prompt_parts.append("\nOptions:")
                for i, option in enumerate(q_data['options'], 1):
                    if option.strip():
                        prompt_parts.append(f"  {i}. {option}")
                prompt_parts.append("")
            
            prompt_parts.append("\nRespond with ONLY the JSON array of answers: [answer1, answer2, ...]")
            
            prompt = "\n".join(prompt_parts)
            
            print(f"      [AI] Calling Gemini API (single request)...")
            
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 100,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            
            print(f"      [AI] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"      [AI] Response received!")
                
                if 'candidates' in data and len(data['candidates']) > 0:
                    candidate = data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        answer_text = candidate['content']['parts'][0]['text'].strip()
                        print(f"      [AI] Raw response: {answer_text[:200]}...")
                        
                        # Try to extract JSON array
                        try:
                            # Remove markdown code blocks if present
                            clean_text = answer_text.replace('```json', '').replace('```', '').strip()
                            
                            # Find JSON array
                            import re
                            match = re.search(r'\[[\d,\s]+\]', clean_text)
                            if match:
                                json_str = match.group(0)
                                answers = json.loads(json_str)
                                
                                print(f"      [AI] ✅ Parsed answers: {answers}")
                                
                                # Create result dictionary
                                results = {}
                                for idx, answer in enumerate(answers, 1):
                                    if isinstance(answer, int) and 0 <= answer <= 5:
                                        results[idx] = answer
                                
                                return results
                            else:
                                print(f"      [AI] ⚠️  No JSON array found in response")
                        except Exception as e:
                            print(f"      [AI] ⚠️  Could not parse JSON: {e}")
                
            elif response.status_code == 429:
                wait_time = 15 * (retry_count + 1)
                print(f"      [AI] ⚠️  Rate limit - waiting {wait_time}s (attempt {retry_count + 1}/3)...")
                time.sleep(wait_time)
                return self.analyze_all_questions_with_gemini(questions_data, retry_count + 1)
            else:
                print(f"      [AI] ❌ API Error: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"      [AI] Error: {error_data.get('error', {}).get('message', 'Unknown')}")
                except:
                    pass
            
            return {}
            
        except Exception as e:
            print(f"      [AI] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def extract_question_and_answers(self):
        """Extract question and answers"""
        try:
            time.sleep(2)
            
            print(f"      [Extract] Running JavaScript...")
            
            script = r"""
            function extractCurrentQuestionData() {
                let result = {question: '', answers: [], debug: {}};
                
                const allQuestionContainers = document.querySelectorAll('.learnosity-item, [class*="question"], .lrn-assessment-wrapper, .lrn_assessment');
                let activeContainer = null;
                
                for (let container of allQuestionContainers) {
                    const style = window.getComputedStyle(container);
                    const rect = container.getBoundingClientRect();
                    
                    const isVisible = style.display !== 'none' && 
                                     style.visibility !== 'hidden' && 
                                     style.opacity !== '0' &&
                                     rect.width > 100 && 
                                     rect.height > 100 &&
                                     rect.top >= 0 &&
                                     rect.top < window.innerHeight;
                    
                    if (isVisible) {
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
                        
                        if (!result.question) {
                            result.question = stimulusContent.innerText || stimulusContent.textContent || '';
                            result.question = result.question.trim().substring(0, 500);
                        }
                        
                        result.debug.foundStimulus = true;
                        result.debug.paragraphCount = paragraphs.length;
                    }
                    
                    const radioInputs = activeContainer.querySelectorAll('input[type="radio"]');
                    result.debug.foundInputs = radioInputs.length;
                    
                    const seenAnswers = new Set();
                    
                    for (let input of radioInputs) {
                        const label = document.querySelector('label[for="' + input.id + '"]');
                        
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
                                        
                                        let cleanText = text.replace(/^Option\s+[A-E],?\s*/i, '');
                                        cleanText = cleanText.replace(/^[A-E]\.?\s*/, '');
                                        
                                        if (cleanText.length > 2 && !seenAnswers.has(cleanText) && !/^[A-E]$/.test(cleanText)) {
                                            seenAnswers.add(cleanText);
                                            result.answers.push(cleanText);
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
            
            print(f"      [Extract] Containers: {data['debug'].get('totalContainers', 0)}")
            print(f"      [Extract] Active found: {data['debug'].get('containerFound', False)}")
            print(f"      [Extract] Question #: {data['debug'].get('currentQuestion', 'Unknown')}")
            print(f"      [Extract] Answers found: {data['debug'].get('answerCount', 0)}")
            print(f"      [Extract] Question length: {data['debug'].get('questionLength', 0)}")
            
            if 'error' in data['debug']:
                print(f"      [Extract] ❌ {data['debug']['error']}")
            
            if data.get('question'):
                print(f"      [Extract] Question preview: {data['question'][:80]}...")
            
            if data.get('answers'):
                print(f"      [Extract] Answers preview:")
                for i, ans in enumerate(data['answers'][:3], 1):
                    print(f"         {i}. {ans[:60]}...")
            
            if not data['question'] or len(data['question']) < 10:
                print(f"      [Extract] ⚠️  Question too short")
                return None
                
            if not data['answers'] or len(data['answers']) < 2:
                print(f"      [Extract] ⚠️  Not enough answers")
                return None
            
            return {
                'question': data['question'],
                'answers': data['answers'],
                'question_num': data['debug'].get('currentQuestion', 'Unknown')
            }
            
        except Exception as e:
            print(f"      [Extract] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def take_precise_screenshot(self, question_num):
        """Take screenshot - with detailed logging"""
        try:
            images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
            os.makedirs(images_folder, exist_ok=True)
            
            screenshots = []
            
            print(f"      [Screenshot] Searching for panels...")
            
            # Try multiple strategies
            strategies = [
                ('.two-columns.left-column.question-content', 'Class combo'),
                ('[data-lrn-widget-type="feature"]', 'Data attribute'),
                ('[class*="left-column"]', 'Left column class'),
                ('.lrn_sharedpassage', 'Shared passage'),
            ]
            
            for selector, strategy_name in strategies:
                try:
                    print(f"      [Screenshot] Trying: {strategy_name}")
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"      [Screenshot]   Found {len(elements)} elements")
                    
                    for elem in elements:
                        if elem.is_displayed():
                            rect = elem.rect
                            print(f"      [Screenshot]   Size: {rect['width']}x{rect['height']}")
                            
                            if rect['width'] > 200 and rect['height'] > 200:
                                print(f"      [Screenshot]   ✅ Suitable element found!")
                                
                                self.driver.execute_script("arguments[0].scrollTop = 0;", elem)
                                time.sleep(0.3)
                                
                                screenshot_data = elem.screenshot_as_png
                                filename = f"Q{question_num}_passage_panel.png"
                                filepath = os.path.join(images_folder, filename)
                                
                                with open(filepath, 'wb') as f:
                                    f.write(screenshot_data)
                                
                                screenshots.append({
                                    'filename': filename,
                                    'description': f'{strategy_name} Panel'
                                })
                                
                                print(f"      [Screenshot]   ✅ Saved: {filename}")
                                return screenshots
                                
                except Exception as e:
                    print(f"      [Screenshot]   ⚠️  {strategy_name} failed: {e}")
            
            print(f"      [Screenshot] ❌ No panels captured")
            return screenshots
            
        except Exception as e:
            print(f"      [Screenshot] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def upload_image_to_imgbb(self, image_path):
        """Upload image to ImgBB"""
        try:
            if not os.path.exists(image_path):
                print(f"         [Upload] ❌ File not found: {image_path}")
                return None
            
            with open(image_path, 'rb') as file:
                image_data = base64.b64encode(file.read()).decode('utf-8')
            
            print(f"         [Upload] Uploading to ImgBB...")
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                'key': self.imgbb_api_key,
                'image': image_data,
            }
            
            response = requests.post(url, data=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    img_url = result['data']['url']
                    print(f"         [Upload] ✅ Success: {img_url[:50]}...")
                    return img_url
            else:
                print(f"         [Upload] ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"         [Upload] ❌ Error: {e}")
        
        return None

    def upload_all_screenshots(self):
        """Upload all screenshots"""
        print("\n📤 Uploading screenshots to ImgBB...")
        
        total_uploaded = 0
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        
        if not os.path.exists(images_folder):
            print("   ⚠️  No images folder found")
            return 0
        
        for result in self.ocr_results:
            if result['screenshots']:
                for screenshot in result['screenshots']:
                    image_path = os.path.join(images_folder, screenshot['filename'])
                    print(f"   Uploading {screenshot['filename']}...")
                    image_url = self.upload_image_to_imgbb(image_path)
                    if image_url:
                        key = f"Q{result['question_num']}_{screenshot['filename']}"
                        self.uploaded_image_urls[key] = image_url
                        total_uploaded += 1
        
        print(f"✅ Uploaded {total_uploaded} images")
        return total_uploaded

    def run_automation(self, max_clicks, wait_time, output_folder):
        """Main automation loop"""
        
        os.makedirs(output_folder, exist_ok=True)
        
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'class': By.CLASS_NAME,
        }
        by_method = selector_map.get(SELECTOR_TYPE, By.CSS_SELECTOR)
        
        self.setup_escape_listener()
        
        for i in range(max_clicks):
            if self.should_stop:
                print(f"\n🛑 Stopped after {i} questions")
                break
                
            print(f"\n{'='*70}")
            print(f"📝 QUESTION {i + 1}/{max_clicks}")
            print(f"{'='*70}")
            
            self.wait_for_load()
            time.sleep(wait_time)
            
            print(f"   🔍 Extracting content...")
            extracted_data = self.extract_question_and_answers()
            
            if extracted_data:
                cleaned_question = self.clean_text(extracted_data['question'])
                cleaned_answers = [self.clean_text(answer) for answer in extracted_data['answers']]
                
                print(f"   📸 Capturing screenshots...")
                screenshots = self.take_precise_screenshot(i + 1)
                
                self.ocr_results.append({
                    'question_num': i + 1,
                    'question_text': cleaned_question,
                    'answers': cleaned_answers,
                    'screenshots': screenshots
                })
                
                print(f"   ✅ Extracted successfully!")
                print(f"      Question: {cleaned_question[:60]}...")
                print(f"      Screenshots: {len(screenshots)}")
                print(f"      Answers: {len(cleaned_answers)}")
            else:
                print(f"   ❌ Extraction failed")
                self.ocr_results.append({
                    'question_num': i + 1,
                    'question_text': f"[Question {i + 1} - Failed]",
                    'answers': [],
                    'screenshots': []
                })
            
            if i < max_clicks - 1 and not self.should_stop:
                try:
                    print(f"   ⏭️  Clicking Next...")
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by_method, BUTTON_SELECTOR))
                    )
                    next_btn.click()
                    time.sleep(2)
                    print(f"   ✓ Next loaded")
                except Exception as e:
                    print(f"   ⚠️  Cannot click Next: {e}")
                    break

    def save_results_quizizz_csv(self, output_file):
        """Save results with AI analysis"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(output_file)[0]
        unique_file = f"{base_name}_{timestamp}.csv"
        
        print("\n" + "="*70)
        if self.ai_enabled:
            print("🤖 ANALYZING ANSWERS WITH GEMINI AI...")
        else:
            print("💾 SAVING RESULTS (No AI)")
        print("="*70)
        
        # Prepare all questions for batch analysis
        ai_answers = {}
        if self.ai_enabled:
            questions_data = []
            valid_indices = []
            
            for idx, result in enumerate(self.ocr_results, 1):
                if not result['question_text'].startswith('[Question'):
                    options = result['answers'][:5]
                    while len(options) < 5:
                        options.append("")
                    
                    questions_data.append({
                        'question': result['question_text'],
                        'options': options
                    })
                    valid_indices.append(idx)
            
            if questions_data:
                print(f"\n   📦 Sending {len(questions_data)} questions in ONE request...")
                ai_answers = self.analyze_all_questions_with_gemini(questions_data)
        
        # Now write CSV with the answers
        with open(unique_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Question', 'Question Type', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Option 5', 'Correct Answer', 'Image Link'])
            
            ai_detected = 0
            ai_uncertain = 0
            valid_idx = 0
            
            for idx, result in enumerate(self.ocr_results, 1):
                if result['question_text'].startswith('[Question'):
                    continue
                
                valid_idx += 1
                question = result['question_text']
                
                options = result['answers'][:5]
                while len(options) < 5:
                    options.append("")
                
                image_link = ""
                if result['screenshots']:
                    for screenshot in result['screenshots']:
                        key = f"Q{result['question_num']}_{screenshot['filename']}"
                        image_link = self.uploaded_image_urls.get(key, "")
                        if image_link:
                            break
                
                correct_answer = ""
                if self.ai_enabled and valid_idx in ai_answers:
                    answer_num = ai_answers[valid_idx]
                    if answer_num > 0:
                        correct_answer = str(answer_num)
                        ai_detected += 1
                        print(f"   [{valid_idx}] Q{result['question_num']}: Answer = Option {answer_num}")
                    else:
                        ai_uncertain += 1
                        print(f"   [{valid_idx}] Q{result['question_num']}: Uncertain")
                
                writer.writerow([
                    question,
                    "Multiple Choice",
                    options[0],
                    options[1],
                    options[2],
                    options[3],
                    options[4],
                    correct_answer,
                    image_link
                ])
        
        if self.ai_enabled:
            print(f"\n🎯 AI Results:")
            print(f"   ✅ Detected: {ai_detected}")
            print(f"   ⚠️  Uncertain: {ai_uncertain}")
            if ai_detected + ai_uncertain > 0:
                print(f"   📊 Success: {int(ai_detected/(ai_detected+ai_uncertain)*100)}%")
        
        print(f"\n💾 Saved: {unique_file}")
        return unique_file

    def cleanup(self):
        """Close browser"""
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        self.driver.quit()


def main():
    print("=" * 80)
    print("AP CLASSROOM EXTRACTOR - DEBUG VERSION")
    print("=" * 80)
    
    if not GEMINI_API_KEY:
        print("\n⚠️  No API key - continuing without AI")
        choice = input("Continue? [Y/n]: ").strip().lower()
        if choice == 'n':
            return
    
    ocr = APClassroomOCR(tesseract_path=TESSERACT_PATH)
    
    try:
        print(f"\n🌐 Opening: {WEBSITE_URL}")
        ocr.navigate_to_url(WEBSITE_URL)
        
        print("\n" + "=" * 80)
        print("SETUP:")
        print("  1. Log in")
        print("  2. Go to FIRST question")
        print("  3. Press ENTER to start")
        print("=" * 80)
        input()
        
        print(f"\n▶  Starting...")
        print(f"   Questions: {MAX_CLICKS}")
        print(f"   Wait: {WAIT_TIME}s")
        print(f"   AI: {'ON' if ocr.ai_enabled else 'OFF'}\n")
        
        ocr.run_automation(MAX_CLICKS, WAIT_TIME, OUTPUT_FOLDER)
        
        if not ocr.ocr_results:
            print("❌ No results!")
            return
        
        total_uploaded = ocr.upload_all_screenshots()
        
        base_output_path = os.path.splitext(OCR_RESULTS_FILE)[0]
        csv_file = f"{base_output_path}_quizizz.csv"
        final_csv = ocr.save_results_quizizz_csv(csv_file)
        
        successful = len([r for r in ocr.ocr_results if not r['question_text'].startswith('[Question')])
        
        print("\n" + "=" * 80)
        print("✅ COMPLETE!")
        print("=" * 80)
        print(f"✓ Questions: {successful}")
        print(f"🌐 Images: {total_uploaded}")
        print(f"📊 CSV: {final_csv}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ocr.cleanup()
        print("\n👋 Done")

if __name__ == "__main__":
    main()
