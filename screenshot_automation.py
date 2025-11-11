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

# Try to load from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except ImportError:
    pass

# Load Gemini API key
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Try to import keyboard (optional - for ESC key functionality)
KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    print("Note: 'keyboard' module not available. ESC key stopping disabled.")
    print("      You can stop by closing the terminal or pressing Ctrl+C")

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
        
        # Set zoom to 50% to capture more content without scrolling
        self.driver.execute_script("document.body.style.zoom='50%'")
        print("🔍 Browser zoom set to 50% to capture full content")
        
        self.ocr_results = []
        self.uploaded_image_urls = {}
        self.imgbb_api_key = "0de54180b4129154bf273314eaf01ef5"
        self.should_stop = False
        self.ai_enabled = GEMINI_API_KEY is not None

    def setup_escape_listener(self):
        """Set up ESC key listener to stop the process (if keyboard module available)"""
        if not KEYBOARD_AVAILABLE:
            print("    ℹ️  Press Ctrl+C to stop the process")
            return
            
        def on_esc_pressed():
            print("\n\n🛑 ESC pressed! Stopping after current question...")
            self.should_stop = True
        
        try:
            keyboard.on_press_key('esc', lambda _: on_esc_pressed())
            print("    ℹ️  Press ESC at any time to stop the process")
        except:
            print("    ℹ️  Press Ctrl+C to stop the process")

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
    
    def analyze_question_with_gemini(self, question, options, image_url=None):
        """
        Use Google Gemini API to analyze question and determine correct answer
        """
        if not self.ai_enabled:
            return 0
            
        try:
            # Build the prompt
            prompt_parts = [
                "You are an expert AP exam test-taker analyzing a multiple choice question.",
                f"\nQuestion: {question}",
                "\nAnswer choices:"
            ]
            
            for i, option in enumerate(options, 1):
                if option.strip():
                    prompt_parts.append(f"{i}. {option}")
            
            prompt_parts.extend([
                "\nAnalyze this question carefully using your knowledge and reasoning.",
                "Determine which answer is most likely correct.",
                "Respond with ONLY a single number (1-5) representing the correct answer.",
                "Do not include any explanation, just the number.",
                "If you cannot determine the answer with high confidence, respond with '0'."
            ])
            
            if image_url:
                prompt_parts.append(f"\nNote: This question has an associated image/passage. Consider that visual context may be important.")
            
            prompt = "\n".join(prompt_parts)
            
            # Call Gemini API
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.1,  # Low temperature for consistent answers
                    "maxOutputTokens": 10,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract answer from Gemini response
                if 'candidates' in data and len(data['candidates']) > 0:
                    candidate = data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        answer_text = candidate['content']['parts'][0]['text'].strip()
                        
                        # Extract number from response
                        try:
                            answer_num = int(answer_text)
                            if 1 <= answer_num <= 5:
                                return answer_num
                        except ValueError:
                            # Try to find first digit in response
                            for char in answer_text:
                                if char.isdigit():
                                    num = int(char)
                                    if 1 <= num <= 5:
                                        return num
            elif response.status_code == 429:
                print(f"\n    ⚠️ Rate limit exceeded. Waiting 60s...")
                time.sleep(60)
                return self.analyze_question_with_gemini(question, options, image_url)
            
            return 0  # Could not determine
            
        except Exception as e:
            print(f"\n    ⚠️ AI analysis error: {e}")
            return 0
    
    def extract_question_and_answers(self):
        """
        Extract ONLY the currently visible question and answers
        """
        try:
            # Wait for content to load
            time.sleep(2)
            
            script = r"""
            function extractCurrentQuestionData() {
                let result = {question: '', answers: [], debug: {}};
                
                // Find the currently visible question container
                const allQuestionContainers = document.querySelectorAll('.learnosity-item, [class*="question"], .lrn-assessment-wrapper, .lrn_assessment');
                let activeContainer = null;
                
                for (let container of allQuestionContainers) {
                    const style = window.getComputedStyle(container);
                    const rect = container.getBoundingClientRect();
                    
                    // Check if container is actually visible
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
                    // Extract question text from stimulus
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
                            result.question = result.question.trim().substring(0, 500);
                        }
                        
                        result.debug.foundStimulus = true;
                        result.debug.paragraphCount = paragraphs.length;
                    }
                    
                    // Extract answers from radio buttons
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
                                        
                                        // Clean the answer text - remove "Option A," prefixes
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
            
            # Validate data
            if not data['question'] or len(data['question']) < 10:
                print(f"   ⚠️ Question too short or missing")
                return None
                
            if not data['answers'] or len(data['answers']) < 2:
                print(f"   ⚠️ Need at least 2 answers (found {len(data['answers'])})")
                return None
            
            return {
                'question': data['question'],
                'answers': data['answers'],
                'question_num': data['debug'].get('currentQuestion', 'Unknown')
            }
            
        except Exception as e:
            print(f"  ⚠️ Extraction error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def take_precise_screenshot(self, question_num):
        """Take screenshot of passage/source material - simplified without stitching"""
        try:
            images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
            os.makedirs(images_folder, exist_ok=True)
            
            screenshots = []
            
            print(f"   📸 Searching for left panel content...")
            
            # STRATEGY 1: Find by the EXACT class combination
            try:
                left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                    '.two-columns.left-column.question-content')
                
                if left_panel and left_panel.is_displayed():
                    rect = left_panel.rect
                    print(f"    ✅ Found LEFT PANEL by class combination!")
                    print(f"    📏 Panel size: {rect['width']}x{rect['height']}")
                    
                    # Scroll to top
                    self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                    time.sleep(0.3)
                    
                    # Capture screenshot
                    screenshot_data = left_panel.screenshot_as_png
                    filename = f"Q{question_num}_passage_panel.png"
                    filepath = os.path.join(images_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_data)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Full Passage Panel'
                    })
                    
                    print(f"    ✅ Captured full panel at 50% zoom!")
                    return screenshots
                    
            except Exception as e:
                print(f"    ⚠️ Strategy 1 failed: {e}")
            
            # STRATEGY 2: Find by data-lrn-widget-type="feature"
            try:
                left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                    '[data-lrn-widget-type="feature"][class*="left-column"]')
                
                if left_panel and left_panel.is_displayed():
                    rect = left_panel.rect
                    print(f"    ✅ Found LEFT PANEL by data attribute!")
                    print(f"    📏 Panel size: {rect['width']}x{rect['height']}")
                    
                    self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                    time.sleep(0.3)
                    
                    screenshot_data = left_panel.screenshot_as_png
                    filename = f"Q{question_num}_passage_panel.png"
                    filepath = os.path.join(images_folder, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(screenshot_data)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Full Passage Panel'
                    })
                    
                    print(f"    ✅ Captured full panel at 50% zoom!")
                    return screenshots
                    
            except Exception as e:
                print(f"    ⚠️ Strategy 2 failed: {e}")
            
            # STRATEGY 3: Find any element with left-column class
            try:
                left_panels = self.driver.find_elements(By.CSS_SELECTOR, '[class*="left-column"]')
                
                for panel in left_panels:
                    if not panel.is_displayed():
                        continue
                        
                    rect = panel.rect
                    
                    # Should be substantial size and on the left side
                    if rect['width'] > 200 and rect['height'] > 200 and rect['x'] < 800:
                        print(f"    ✅ Found LEFT PANEL by class search!")
                        print(f"    📏 Panel size: {rect['width']}x{rect['height']}")
                        
                        self.driver.execute_script("arguments[0].scrollTop = 0;", panel)
                        time.sleep(0.3)
                        
                        screenshot_data = panel.screenshot_as_png
                        filename = f"Q{question_num}_passage_panel.png"
                        filepath = os.path.join(images_folder, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(screenshot_data)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Full Passage Panel'
                        })
                        
                        print(f"    ✅ Captured panel at 50% zoom!")
                        return screenshots
                        
            except Exception as e:
                print(f"    ⚠️ Strategy 3 failed: {e}")
            
            # FALLBACK: Capture just the image
            print(f"    ⚠️ Could not find full panel - trying fallback...")
            try:
                all_images = self.driver.find_elements(By.TAG_NAME, 'img')
                
                for img in all_images:
                    if img.is_displayed() and img.size['width'] > 100 and img.size['height'] > 100:
                        rect = img.rect
                        
                        if 50 < rect['y'] < 800:
                            print(f"    ⚠️ FALLBACK: Capturing only the image")
                            print(f"    📏 Image size: {img.size['width']}x{img.size['height']}")
                            
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", 
                                img
                            )
                            time.sleep(0.3)
                            
                            screenshot_data = img.screenshot_as_png
                            filename = f"Q{question_num}_image_only.png"
                            filepath = os.path.join(images_folder, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(screenshot_data)
                            
                            screenshots.append({
                                'filename': filename,
                                'description': 'Image Only (Fallback)'
                            })
                            
                            print(f"    ⚠️ Only captured image at 50% zoom")
                            return screenshots
                            
            except Exception as e:
                print(f"    ❌ Fallback also failed: {e}")
            
            # Nothing captured
            print(f"    ❌ No content captured for this question")
            return screenshots
            
        except Exception as e:
            print(f"    ❌ Screenshot error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def upload_image_to_imgbb(self, image_path):
        """Upload image to ImgBB and return direct URL"""
        try:
            if not os.path.exists(image_path):
                return None
            
            with open(image_path, 'rb') as file:
                image_data = base64.b64encode(file.read()).decode('utf-8')
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                'key': self.imgbb_api_key,
                'image': image_data,
            }
            
            response = requests.post(url, data=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    return result['data']['url']
                
        except Exception as e:
            print(f"    ❌ Upload error: {e}")
        
        return None

    def upload_all_screenshots(self):
        """Upload all screenshots to ImgBB"""
        print("\n📤 Uploading screenshots to ImgBB...")
        
        total_uploaded = 0
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        
        if not os.path.exists(images_folder):
            return 0
        
        for result in self.ocr_results:
            if result['screenshots']:
                for screenshot in result['screenshots']:
                    image_path = os.path.join(images_folder, screenshot['filename'])
                    if os.path.exists(image_path):
                        print(f"    📤 Uploading {screenshot['filename']}...")
                        image_url = self.upload_image_to_imgbb(image_path)
                        if image_url:
                            key = f"Q{result['question_num']}_{screenshot['filename']}"
                            self.uploaded_image_urls[key] = image_url
                            total_uploaded += 1
                            print(f"    ✅ Uploaded!")
                        else:
                            print(f"    ❌ Failed to upload")
        
        print(f"✅ Uploaded {total_uploaded} images")
        return total_uploaded

    def run_automation(self, max_clicks, wait_time, output_folder):
        """Main automation loop with images"""
        
        # Create output folder
        os.makedirs(output_folder, exist_ok=True)
        
        selector_map = {
            'css': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'class': By.CLASS_NAME,
        }
        by_method = selector_map.get(SELECTOR_TYPE, By.CSS_SELECTOR)
        
        # Setup escape listener
        self.setup_escape_listener()
        
        for i in range(max_clicks):
            if self.should_stop:
                print(f"\n🛑 Stopped by user after {i} questions")
                break
                
            print(f"\n{'='*70}")
            print(f"📝 QUESTION {i + 1}/{max_clicks}")
            print(f"{'='*70}")
            
            # Wait for page load
            self.wait_for_load()
            time.sleep(wait_time)
            
            # Extract content
            print(f"   📖 Extracting content...")
            extracted_data = self.extract_question_and_answers()
            
            if extracted_data:
                # Clean the text
                cleaned_question = self.clean_text(extracted_data['question'])
                cleaned_answers = [self.clean_text(answer) for answer in extracted_data['answers']]
                
                # Take screenshots
                print(f"   📸 Capturing passage/source material...")
                screenshots = self.take_precise_screenshot(i + 1)
                
                self.ocr_results.append({
                    'question_num': i + 1,
                    'question_text': cleaned_question,
                    'answers': cleaned_answers,
                    'screenshots': screenshots
                })
                
                print(f"   ✅ Successfully extracted!")
                print(f"   📄 {cleaned_question[:60]}...")
                print(f"   📷 Screenshots: {len(screenshots)}")
                print(f"   📝 Answers: {len(cleaned_answers)}")
            else:
                print(f"   ❌ Extraction failed")
                self.ocr_results.append({
                    'question_num': i + 1,
                    'question_text': f"[Question {i + 1} - Extraction Failed]",
                    'answers': [],
                    'screenshots': []
                })
            
            # Click next
            if i < max_clicks - 1 and not self.should_stop:
                try:
                    print(f"   ⏭️  Clicking Next...")
                    next_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by_method, BUTTON_SELECTOR))
                    )
                    next_btn.click()
                    time.sleep(2)
                    print(f"   ✓ Next question loaded")
                except Exception as e:
                    print(f"   ⚠️ Cannot click Next: {e}")
                    print(f"   Stopping...")
                    break

    def save_results_quizizz_csv(self, output_file):
        """Save results in Quizizz CSV format with AI-detected answers"""
        # Create unique filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(output_file)[0]
        unique_file = f"{base_name}_{timestamp}.csv"
        
        print("\n" + "="*70)
        if self.ai_enabled:
            print("🤖 ANALYZING ANSWERS WITH GEMINI AI...")
        else:
            print("💾 SAVING RESULTS (AI disabled - no API key)")
        print("="*70)
        
        with open(unique_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # Quizizz CSV header
            writer.writerow(['Question', 'Question Type', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Option 5', 'Correct Answer', 'Image Link'])
            
            ai_detected = 0
            ai_uncertain = 0
            
            for idx, result in enumerate(self.ocr_results, 1):
                if result['question_text'].startswith('[Question'):
                    continue
                
                question = result['question_text']
                
                # Ensure we have exactly 5 options
                options = result['answers'][:5]
                while len(options) < 5:
                    options.append("")
                
                # Get PASSAGE PANEL image URL
                image_link = ""
                if result['screenshots']:
                    for screenshot in result['screenshots']:
                        if 'passage_panel' in screenshot['filename']:
                            key = f"Q{result['question_num']}_{screenshot['filename']}"
                            image_link = self.uploaded_image_urls.get(key, "")
                            break
                    
                    if not image_link and result['screenshots']:
                        primary_screenshot = result['screenshots'][0]
                        key = f"Q{result['question_num']}_{primary_screenshot['filename']}"
                        image_link = self.uploaded_image_urls.get(key, "")
                
                # AI ANALYSIS HERE
                correct_answer = ""
                if self.ai_enabled:
                    print(f"    [{idx}/{len([r for r in self.ocr_results if not r['question_text'].startswith('[Question')])}] Analyzing... ", end="", flush=True)
                    
                    answer_num = self.analyze_question_with_gemini(question, options, image_link)
                    
                    if answer_num > 0:
                        correct_answer = str(answer_num)
                        ai_detected += 1
                        print(f"✅ Option {answer_num}")
                    else:
                        ai_uncertain += 1
                        print("⚠️ Uncertain")
                
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
            print(f"\n🎯 AI Analysis Results:")
            print(f"   ✅ Answers detected: {ai_detected}")
            print(f"   ⚠️  Uncertain: {ai_uncertain}")
            if ai_detected + ai_uncertain > 0:
                print(f"   📊 Success rate: {int(ai_detected/(ai_detected+ai_uncertain)*100)}%")
        
        print(f"\n💾 Saved Quizizz CSV: {unique_file}")
        return unique_file

    def cleanup(self):
        """Close browser and cleanup"""
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        self.driver.quit()


def main():
    print("=" * 80)
    print("AP CLASSROOM EXTRACTOR - WITH AI ANSWER DETECTION")
    print("=" * 80)
    
    # Check for Gemini API key
    if not GEMINI_API_KEY:
        print("\n⚠️  WARNING: GEMINI_API_KEY not found!")
        print("=" * 80)
        print("The script will extract questions but won't detect answers.")
        print("\nTo enable AI answer detection:")
        print("1. Get FREE API key: https://makersuite.google.com/app/apikey")
        print("2. Create .env file with: GEMINI_API_KEY=your-key-here")
        print("3. Or set environment variable")
        print("=" * 80)
        
        choice = input("\nContinue without AI? [Y/n]: ").strip().lower()
        if choice == 'n':
            print("\n👋 Exiting. Please set up your API key first.")
            return
        print("\n▶️  Continuing without AI answer detection...\n")
    else:
        print("\n✅ Gemini AI enabled - answers will be automatically detected!")
        print("=" * 80)
    
    ocr = APClassroomOCR(tesseract_path=TESSERACT_PATH)
    
    try:
        print(f"\n🌐 Opening: {WEBSITE_URL}")
        ocr.navigate_to_url(WEBSITE_URL)
        
        print("\n" + "=" * 80)
        print("⚠️  SETUP:")
        print("    1. Log in to AP Classroom")
        print("    2. Go to the FIRST question")
        print("    3. Wait for it to fully load")
        print("    4. Press ENTER to start")
        if KEYBOARD_AVAILABLE:
            print("    5. Press ESC at any time to stop")
        else:
            print("    5. Press Ctrl+C to stop")
        print("=" * 80)
        input()
        
        print(f"\n▶  Starting extraction...")
        print(f"    Questions: {MAX_CLICKS}")
        print(f"    Wait time: {WAIT_TIME}s")
        if ocr.ai_enabled:
            print(f"    AI: ENABLED ✅")
        else:
            print(f"    AI: DISABLED ⚠️")
        print()
        
        # Run automation
        ocr.run_automation(MAX_CLICKS, WAIT_TIME, OUTPUT_FOLDER)
        
        if not ocr.ocr_results:
            print("❌ No results to save!")
            return
        
        # Upload screenshots
        print(f"\n📤 Uploading images to ImgBB...")
        total_uploaded = ocr.upload_all_screenshots()
        
        # Save Quizizz CSV (with AI-detected answers)
        base_output_path = os.path.splitext(OCR_RESULTS_FILE)[0]
        csv_file = f"{base_output_path}_quizizz.csv"
        final_csv = ocr.save_results_quizizz_csv(csv_file)
        
        # Summary
        successful = len([r for r in ocr.ocr_results if not r['question_text'].startswith('[Question')])
        
        print("\n" + "=" * 80)
        print("✅ EXTRACTION COMPLETE!")
        print("=" * 80)
        print(f"✓ Questions extracted: {successful}")
        print(f"🌐 Images uploaded: {total_uploaded}")
        print(f"📊 Quizizz CSV: {final_csv}")
        
        if ocr.ai_enabled:
            print("\n🤖 AI ANSWER DETECTION:")
            print("   ✅ Answers automatically detected and added to CSV!")
            print("   💡 Review answers marked 'Uncertain' before importing")
        else:
            print("\n⚠️  AI DISABLED:")
            print("   Correct answers column is empty")
            print("   You'll need to add them manually or run ai_answer_detector_gemini.py")
        
        print("\n🎮 QUIZIZZ IMPORT STEPS:")
        print("   1. Go to quizizz.com → Create → Quiz")
        print("   2. Click 'Import from Spreadsheet'")
        print("   3. Upload the CSV file")
