"""
DEBUG VERSION - Shows detailed output to troubleshoot issues
FIXED: Screenshot functionality now matches WORKINGSCREENSHOTRECORDER.py
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

# Load OpenRouter API key
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

print(f"\n🔑 API Key Status: {'SET ✅' if OPENROUTER_API_KEY else 'NOT SET ❌'}")
if OPENROUTER_API_KEY:
    print(f"   Key prefix: {OPENROUTER_API_KEY[:20]}...")

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
        self.ai_enabled = OPENROUTER_API_KEY is not None
        
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
    
    def analyze_question_with_openrouter(self, question, options, image_url=None):
        """Use OpenRouter with Llama 4 Scout (FREE vision model)"""
        if not self.ai_enabled:
            print("      [AI] Disabled - no API key")
            return 0
            
        try:
            from openai import OpenAI
            
            print(f"\n      [AI] Building prompt...")
            
            # Build the prompt text
            prompt_parts = [
                "You are an expert AP exam test-taker analyzing a multiple choice question.",
                f"\nQuestion: {question}",
                "\nAnswer choices:"
            ]
            
            for i, option in enumerate(options, 1):
                if option.strip():
                    prompt_parts.append(f"{i}. {option}")
            
            if image_url:
                prompt_parts.extend([
                    "\n⚠️ CRITICAL INSTRUCTIONS:",
                    "- Study the image/passage provided - it contains key information",
                    "- Use BOTH the image AND the question text to determine the BEST answer",
                    "- Your response must be ONLY a single digit: 1, 2, 3, 4, or 5",
                    "- Do NOT write any explanation, reasoning, or other text",
                    "- Do NOT write 'The answer is' or similar phrases",
                    "- ONLY output the digit itself",
                    "\nYour answer (digit only):"
                ])
            else:
                prompt_parts.extend([
                    "\n⚠️ CRITICAL INSTRUCTIONS:",
                    "- Your response must be ONLY a single digit: 1, 2, 3, 4, 5",
                    "- Do NOT write any explanation, reasoning, or other text",
                    "- Do NOT write 'The answer is' or similar phrases",
                    "- ONLY output the digit itself",
                    "\nYour answer (digit only):"
                ])
            
            prompt_text = "\n".join(prompt_parts)
            
            # Get OpenRouter API key from environment
            openrouter_key = os.environ.get('OPENROUTER_API_KEY')
            
            if not openrouter_key:
                print("      [AI] ❌ No OPENROUTER_API_KEY in .env file")
                return 0
            
            # Initialize OpenAI client with OpenRouter base URL
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key,
            )
            
            # Build message content (with or without image)
            message_content = []
            
            # Add the text prompt FIRST
            message_content.append({
                "type": "text",
                "text": prompt_text
            })
            
            # Add image if available (AFTER text)
            if image_url:
                print(f"      [AI] 📸 Including image: {image_url[:50]}...")
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
                print(f"      [AI] Using Llama 4 Scout (FREE vision model)")
            else:
                print(f"      [AI] Using Llama 4 Scout (text only)")
            
            # Always use Llama 4 Scout (supports both text and images, and it's FREE!)
            model = "meta-llama/llama-4-scout:free"
            
            print(f"      [AI] Calling OpenRouter...")
            
            # Call the API
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://github.com/APClassroom-QuestionExtractor",
                    "X-Title": "AP Classroom Question Extractor",
                },
                extra_body={},
                model=model,
                messages=[{
                    "role": "user",
                    "content": message_content
                }],
                max_tokens=10,
                temperature=0.1
            )
            
            print(f"      [AI] Response received")
            
            # Extract answer
            answer_text = completion.choices[0].message.content.strip()
            print(f"      [AI] Raw answer: '{answer_text}'")
            
            # Extract number
            try:
                answer_num = int(answer_text)
                if 1 <= answer_num <= 5:
                    print(f"      [AI] ✅ Detected answer: {answer_num}")
                    return answer_num
            except ValueError:
                # Try to find first digit
                for char in answer_text:
                    if char.isdigit():
                        num = int(char)
                        if 1 <= num <= 5:
                            print(f"      [AI] ✅ Extracted answer: {num}")
                            return num
            
            print(f"      [AI] ⚠️  Could not parse answer")
            return 0
            
        except ImportError:
            print(f"      [AI] ❌ OpenAI library not installed")
            print(f"      [AI] Run: pip install openai")
            return 0
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle rate limiting
            if "429" in error_msg or "rate" in error_msg.lower():
                print(f"      [AI] ⚠️  Rate limit - waiting 10s...")
                time.sleep(10)
                return self.analyze_question_with_openrouter(question, options, image_url)
            
            # Handle other errors
            print(f"      [AI] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
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
        """Take screenshot of passage/source material - FIXED VERSION from WORKINGSCREENSHOTRECORDER.py"""
        try:
            images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
            os.makedirs(images_folder, exist_ok=True)
            
            screenshots = []
            
            print(f"   📷 Searching for left panel content...")
            
            # STRATEGY 1: Find by the EXACT class combination (most reliable)
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
                print(f"    ⚠️  Strategy 1 failed: {str(e)[:50]}")
            
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
                print(f"    ⚠️  Strategy 2 failed: {str(e)[:50]}")
            
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
                print(f"    ⚠️  Strategy 3 failed: {str(e)[:50]}")
            
            # STRATEGY 4: Find by ID pattern
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, '[id$="-container"]')
                
                for container in containers:
                    if not container.is_displayed():
                        continue
                    
                    widget_type = container.get_attribute('data-lrn-widget-type')
                    if widget_type == 'feature':
                        rect = container.rect
                        
                        if rect['width'] > 200 and rect['height'] > 200:
                            print(f"    ✅ Found LEFT PANEL by ID pattern!")
                            print(f"    📏 Panel size: {rect['width']}x{rect['height']}")
                            
                            self.driver.execute_script("arguments[0].scrollTop = 0;", container)
                            time.sleep(0.3)
                            
                            screenshot_data = container.screenshot_as_png
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
                print(f"    ⚠️  Strategy 4 failed: {str(e)[:50]}")
            
            # STRATEGY 5: Parent traversal from lrn_sharedpassage
            try:
                shared_passage = self.driver.find_element(By.CSS_SELECTOR, '.lrn_sharedpassage')
                
                if shared_passage and shared_passage.is_displayed():
                    # Try to get parent container
                    parent_container = self.driver.execute_script(
                        "return arguments[0].parentElement.parentElement;", 
                        shared_passage
                    )
                    
                    if parent_container and parent_container.is_displayed():
                        rect = parent_container.rect
                        
                        if rect['width'] > 200 and rect['height'] > 200:
                            print(f"    ✅ Found shared passage container!")
                            print(f"    📏 Container size: {rect['width']}x{rect['height']}")
                            
                            self.driver.execute_script("arguments[0].scrollTop = 0;", parent_container)
                            time.sleep(0.3)
                            
                            screenshot_data = parent_container.screenshot_as_png
                            filename = f"Q{question_num}_passage_panel.png"
                            filepath = os.path.join(images_folder, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(screenshot_data)
                            
                            screenshots.append({
                                'filename': filename,
                                'description': 'Shared Passage Panel'
                            })
                            
                            print(f"    ✅ Captured shared passage at 50% zoom!")
                            return screenshots
                            
            except Exception as e:
                print(f"    ⚠️  Strategy 5 failed: {str(e)[:50]}")
            
            # FALLBACK: Capture any significant images
            print(f"    ⚠️  Could not find panel - trying fallback...")
            try:
                all_images = self.driver.find_elements(By.TAG_NAME, 'img')
                
                for img in all_images:
                    if img.is_displayed() and img.size['width'] > 100 and img.size['height'] > 100:
                        rect = img.rect
                        
                        # Only capture images in the main content area
                        if 50 < rect['y'] < 800:
                            print(f"    ⚠️  FALLBACK: Capturing image")
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
                            
                            print(f"    ⚠️  Only captured image at 50% zoom")
                            return screenshots
                            
            except Exception as e:
                print(f"    ❌ Fallback failed: {str(e)[:50]}")
            
            # Nothing captured
            print(f"    ❌ No visual content found for this question")
            return screenshots
            
        except Exception as e:
            print(f"    ❌ Screenshot error: {e}")
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
            print("🤖 ANALYZING ANSWERS WITH AI...")
        else:
            print("💾 SAVING RESULTS (No AI)")
        print("="*70)
        
        with open(unique_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            writer.writerow(['Question Text', 'Question Type', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Option 5', 'Correct Answer', 'Time in seconds', 'Image Link'])
            
            ai_detected = 0
            ai_uncertain = 0
            
            for idx, result in enumerate(self.ocr_results, 1):
                if result['question_text'].startswith('[Question'):
                    continue
                
                question = result['question_text']
                
                options = result['answers'][:5]
                while len(options) < 5:
                    options.append("")
                
                # Get PASSAGE PANEL image URL (prioritize the panel screenshot)
                image_link = ""
                if result['screenshots']:
                    # Look for the passage panel screenshot first
                    for screenshot in result['screenshots']:
                        if 'passage_panel' in screenshot['filename']:
                            key = f"Q{result['question_num']}_{screenshot['filename']}"
                            image_link = self.uploaded_image_urls.get(key, "")
                            break
                    
                    # If no passage panel, use first screenshot
                    if not image_link and result['screenshots']:
                        primary_screenshot = result['screenshots'][0]
                        key = f"Q{result['question_num']}_{primary_screenshot['filename']}"
                        image_link = self.uploaded_image_urls.get(key, "")
                
                correct_answer = ""
                if self.ai_enabled:
                    print(f"\n   [{idx}] Analyzing question {result['question_num']}...")
                    print(f"      Q: {question[:60]}...")
                    
                    answer_num = self.analyze_question_with_openrouter(question, options, image_link)
                    
                    if answer_num > 0:
                        correct_answer = str(answer_num)
                        ai_detected += 1
                        print(f"      ✅ Answer: Option {answer_num}")
                    else:
                        ai_uncertain += 1
                        print(f"      ⚠️  Uncertain")
                
                writer.writerow([
                    question,
                    "Multiple Choice",
                    options[0],
                    options[1],
                    options[2],
                    options[3],
                    options[4],
                    correct_answer,
                    "60",
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
    
    if not OPENROUTER_API_KEY:
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
