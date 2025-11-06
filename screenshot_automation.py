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
import keyboard
import datetime
import io

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
print(“❌ config.py not found! Run setup.py first.”)
exit(1)

class APClassroomOCR:
def **init**(self, tesseract_path=None):
“”“Initialize with settings optimized for text extraction”””

```
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
    
    self.ocr_results = []
    self.uploaded_image_urls = {}
    self.imgbb_api_key = "0de54180b4129154bf273314eaf01ef5"
    self.should_stop = False

def setup_escape_listener(self):
    """Set up ESC key listener to stop the process"""
    def on_esc_pressed():
        print("\n\n🛑 ESC pressed! Stopping after current question...")
        self.should_stop = True
    
    keyboard.on_press_key('esc', lambda _: on_esc_pressed())
    print("    ℹ️  Press ESC at any time to stop the process")

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
    """Take screenshot of passage/source material - ADAPTIVE DETECTION with visibility checks"""
    try:
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        os.makedirs(images_folder, exist_ok=True)
        
        screenshots = []
        
        print(f"   🔍 Searching for content to capture...")
        
        # Get viewport width for adaptive positioning
        viewport_width = self.driver.execute_script("return window.innerWidth;")
        viewport_height = self.driver.execute_script("return window.innerHeight;")
        left_threshold = viewport_width * 0.4  # Left 40% of screen
        
        print(f"       Viewport: {viewport_width}x{viewport_height}px, left threshold: {int(left_threshold)}px")
        
        # Helper function to check if element is truly visible in current viewport
        def is_truly_visible(element):
            try:
                # Check display/visibility styles
                is_displayed = element.is_displayed()
                if not is_displayed:
                    return False
                
                # Check if in viewport
                rect = element.rect
                
                # Must have substantial size
                if rect['width'] < 100 or rect['height'] < 100:
                    return False
                
                # Must be within viewport bounds (not scrolled off-screen)
                if rect['y'] + rect['height'] < 0:  # Above viewport
                    return False
                if rect['y'] > viewport_height + 200:  # Below viewport (with buffer)
                    return False
                if rect['x'] + rect['width'] < 0:  # Left of viewport
                    return False
                if rect['x'] > viewport_width:  # Right of viewport
                    return False
                
                # Check opacity and visibility via JavaScript
                is_visible = self.driver.execute_script("""
                    const el = arguments[0];
                    const style = window.getComputedStyle(el);
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           el.offsetParent !== null;
                """, element)
                
                return is_visible
            except:
                return False
        
        # STRATEGY 1: Look for LEFT PANEL first (most reliable identifier)
        left_panel = None
        
        try:
            potential_panels = self.driver.find_elements(By.CSS_SELECTOR, 
                '.two-columns.left-column.question-content, [data-lrn-widget-type="feature"][class*="left-column"], [class*="left-column"]')
            
            print(f"       Found {len(potential_panels)} potential left panel candidates")
            
            for panel in potential_panels:
                # Check if truly visible
                if not is_truly_visible(panel):
                    continue
                
                rect = panel.rect
                
                # Must be on LEFT side
                if rect['x'] >= left_threshold:
                    continue
                
                # Must be substantial size
                if rect['width'] < 300 or rect['height'] < 300:
                    continue
                
                # Verify it actually contains content
                has_text = len(panel.text.strip()) > 50
                has_image = len(panel.find_elements(By.TAG_NAME, 'img')) > 0
                
                if has_text or has_image:
                    # IMPORTANT: Check if this panel is in the current viewport
                    # (not from a question that's loaded but not visible)
                    in_viewport = self.driver.execute_script("""
                        const el = arguments[0];
                        const rect = el.getBoundingClientRect();
                        return (
                            rect.top >= -100 &&
                            rect.left >= -100 &&
                            rect.bottom <= (window.innerHeight + 100) &&
                            rect.right <= window.innerWidth
                        );
                    """, panel)
                    
                    if in_viewport:
                        left_panel = panel
                        print(f"    ✅ Found VISIBLE LEFT PANEL (Questions 3-5 type)")
                        print(f"       Position: x={rect['x']}px, y={rect['y']}px")
                        break
                    else:
                        print(f"       Skipping left panel at y={rect['y']}px (not in viewport)")
            
        except Exception as e:
            print(f"       Left panel search error: {e}")
        
        # If we found a left panel, capture it
        if left_panel:
            rect = left_panel.rect
            scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", left_panel)
            
            print(f"    📏 Panel dimensions:")
            print(f"       - Visible height: {rect['height']}px")
            print(f"       - Total content height: {scroll_height}px")
            print(f"       - Width: {rect['width']}px")
            
            # Check if content is taller than visible area
            if scroll_height > rect['height'] + 50:
                print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                
                zoom_needed = rect['height'] / scroll_height
                zoom_level = max(0.25, min(0.5, zoom_needed))
                
                print(f"       Setting zoom to {int(zoom_level * 100)}%")
                
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", left_panel)
                time.sleep(0.5)
                
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                self.driver.execute_script("arguments[0].style.zoom = '1';", left_panel)
                time.sleep(0.3)
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured FULL panel with zoom!")
                print(f"       Final dimensions: {img.width}x{img.height}px")
                return screenshots
            
            else:
                print(f"    📸 Content fits in viewport - normal capture")
                
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured panel!")
                return screenshots
        
        # STRATEGY 2: No left panel - look for CENTER/TOP content
        print(f"    ℹ️ No left panel found - checking for centered content...")
        
        try:
            stimulus_candidates = self.driver.find_elements(By.CSS_SELECTOR, 
                '.lrn_stimulus_content, .lrn-stimulus-content, .lrn_stimulus, [class*="stimulus"]')
            
            print(f"       Found {len(stimulus_candidates)} stimulus candidates")
            
            best_stimulus = None
            best_score = 0
            
            for stimulus in stimulus_candidates:
                # Check if truly visible
                if not is_truly_visible(stimulus):
                    continue
                
                rect = stimulus.rect
                
                # Skip if too small
                if rect['width'] < 200 or rect['height'] < 100:
                    continue
                
                # Skip if on far left (would be left panel)
                if rect['x'] < left_threshold:
                    continue
                
                # CRITICAL: Check if in current viewport
                in_viewport = self.driver.execute_script("""
                    const el = arguments[0];
                    const rect = el.getBoundingClientRect();
                    return (
                        rect.top >= -100 &&
                        rect.left >= 0 &&
                        rect.bottom <= (window.innerHeight + 100) &&
                        rect.right <= window.innerWidth
                    );
                """, stimulus)
                
                if not in_viewport:
                    print(f"       Skipping stimulus at y={rect['y']}px (not in viewport)")
                    continue
                
                # Calculate score
                score = 0
                
                # Has image? +100 points
                images = stimulus.find_elements(By.TAG_NAME, 'img')
                large_images = [img for img in images if img.is_displayed() and img.size['width'] > 200]
                if large_images:
                    score += 100
                
                # Has text? +50 points
                text_length = len(stimulus.text.strip())
                if text_length > 50:
                    score += 50
                
                # Size matters
                score += (rect['width'] * rect['height']) / 10000
                
                # More centered is better
                center_x = rect['x'] + rect['width'] / 2
                viewport_center = viewport_width / 2
                distance_from_center = abs(center_x - viewport_center)
                centrality_score = max(0, 100 - (distance_from_center / viewport_width * 100))
                score += centrality_score
                
                # Bonus: Higher on page is better (likely the main content)
                if rect['y'] < 300:
                    score += 50
                
                print(f"       Candidate at y={rect['y']}px scored {int(score)}")
                
                if score > best_score:
                    best_score = score
                    best_stimulus = stimulus
            
            if best_stimulus:
                rect = best_stimulus.rect
                print(f"    ✅ Found VISIBLE CENTER/TOP content (Questions 1-2 type)")
                print(f"       Position: x={rect['x']}px, y={rect['y']}px (score: {int(best_score)})")
                print(f"       Size: {rect['width']}x{rect['height']}px")
                
                stimulus_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", best_stimulus)
                parent = self.driver.execute_script("return arguments[0].parentElement;", best_stimulus)
                parent_rect = parent.rect
                parent_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", parent)
                
                print(f"       Content height: {stimulus_scroll}px, visible: {rect['height']}px")
                
                # Check if scrollable
                if stimulus_scroll > rect['height'] + 50 or parent_scroll > parent_rect['height'] + 50:
                    print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                    
                    max_scroll = max(stimulus_scroll, parent_scroll)
                    max_visible = max(rect['height'], parent_rect['height'])
                    zoom_needed = max_visible / max_scroll
                    zoom_level = max(0.25, min(0.5, zoom_needed))
                    
                    print(f"       Setting zoom to {int(zoom_level * 100)}%")
                    
                    self.driver.execute_script("arguments[0].scrollTop = 0;", parent)
                    time.sleep(0.3)
                    
                    self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", best_stimulus)
                    time.sleep(0.5)
                    
                    screenshot_data = best_stimulus.screenshot_as_png
                    img = Image.open(io.BytesIO(screenshot_data))
                    
                    self.driver.execute_script("arguments[0].style.zoom = '1';", best_stimulus)
                    time.sleep(0.3)
                    
                    filename = f"Q{question_num}_stimulus.png"
                    filepath = os.path.join(images_folder, filename)
                    img.save(filepath, 'PNG', quality=95)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Full Centered Content'
                    })
                    
                    print(f"    ✅ Captured FULL centered content with zoom!")
                    print(f"       Final dimensions: {img.width}x{img.height}px")
                    return screenshots
                
                else:
                    print(f"    📸 Content fits - normal capture")
                    
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});", 
                        best_stimulus
                    )
                    time.sleep(0.3)
                    
                    screenshot_data = best_stimulus.screenshot_as_png
                    img = Image.open(io.BytesIO(screenshot_data))
                    
                    filename = f"Q{question_num}_stimulus.png"
                    filepath = os.path.join(images_folder, filename)
                    img.save(filepath, 'PNG', quality=95)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Centered Content'
                    })
                    
                    print(f"    ✅ Captured centered content!")
                    return screenshots
            
            print(f"    ⚠️ No visible content found in viewport")
            
        except Exception as e:
            print(f"    ❌ Center content detection failed: {e}")
            import traceback
            traceback.print_exc()
        
        return screenshots
        
    except Exception as e:
        print(f"    ❌ Screenshot error: {e}")
        import traceback
        traceback.print_exc()
        return []
    try:
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        os.makedirs(images_folder, exist_ok=True)
        
        screenshots = []
        
        print(f"   🔍 Searching for content to capture...")
        
        # Get viewport width for adaptive positioning
        viewport_width = self.driver.execute_script("return window.innerWidth;")
        left_threshold = viewport_width * 0.4  # Left 40% of screen
        
        print(f"       Viewport width: {viewport_width}px, left threshold: {int(left_threshold)}px")
        
        # STRATEGY 1: Look for LEFT PANEL first (most reliable identifier)
        # Left panels have specific classes and are always on the left
        left_panel = None
        
        try:
            # Try exact class match first
            potential_panels = self.driver.find_elements(By.CSS_SELECTOR, 
                '.two-columns.left-column.question-content, [data-lrn-widget-type="feature"][class*="left-column"], [class*="left-column"]')
            
            for panel in potential_panels:
                if not panel.is_displayed():
                    continue
                
                rect = panel.rect
                
                # Must be on LEFT side and substantial size
                if rect['x'] < left_threshold and rect['width'] > 300 and rect['height'] > 300:
                    # Verify it actually contains content (not just a wrapper)
                    has_text = len(panel.text.strip()) > 50
                    has_image = len(panel.find_elements(By.TAG_NAME, 'img')) > 0
                    
                    if has_text or has_image:
                        left_panel = panel
                        print(f"    ✅ Found LEFT PANEL (Questions 3-5 type)")
                        print(f"       Position: x={rect['x']}px (left side)")
                        break
            
        except Exception as e:
            print(f"       Left panel search error: {e}")
        
        # If we found a left panel, capture it
        if left_panel:
            rect = left_panel.rect
            scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", left_panel)
            
            print(f"    📏 Panel dimensions:")
            print(f"       - Visible height: {rect['height']}px")
            print(f"       - Total content height: {scroll_height}px")
            print(f"       - Width: {rect['width']}px")
            
            # Check if content is taller than visible area
            if scroll_height > rect['height'] + 50:
                print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                
                zoom_needed = rect['height'] / scroll_height
                zoom_level = max(0.25, min(0.5, zoom_needed))
                
                print(f"       Setting zoom to {int(zoom_level * 100)}%")
                
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", left_panel)
                time.sleep(0.5)
                
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                self.driver.execute_script("arguments[0].style.zoom = '1';", left_panel)
                time.sleep(0.3)
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured FULL panel with zoom!")
                print(f"       Final dimensions: {img.width}x{img.height}px")
                return screenshots
            
            else:
                print(f"    📸 Content fits in viewport - normal capture")
                
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured panel!")
                return screenshots
        
        # STRATEGY 2: No left panel - look for CENTER/TOP content (Questions 1-2 type)
        print(f"    ℹ️ No left panel found - checking for centered content...")
        
        try:
            # Look for stimulus areas that might contain images/text
            stimulus_candidates = self.driver.find_elements(By.CSS_SELECTOR, 
                '.lrn_stimulus_content, .lrn-stimulus-content, .lrn_stimulus, [class*="stimulus"]')
            
            best_stimulus = None
            best_score = 0
            
            for stimulus in stimulus_candidates:
                if not stimulus.is_displayed():
                    continue
                
                rect = stimulus.rect
                
                # Skip if it's too small or off-screen
                if rect['width'] < 200 or rect['height'] < 100:
                    continue
                
                # Skip if it's on the far left (would have been caught as left panel)
                if rect['x'] < left_threshold:
                    continue
                
                # Calculate score based on content
                score = 0
                
                # Has image? +100 points
                images = stimulus.find_elements(By.TAG_NAME, 'img')
                large_images = [img for img in images if img.is_displayed() and img.size['width'] > 200]
                if large_images:
                    score += 100
                
                # Has text? +50 points
                text_length = len(stimulus.text.strip())
                if text_length > 50:
                    score += 50
                
                # Size matters (bigger is more likely to be the main content)
                score += (rect['width'] * rect['height']) / 10000
                
                # More centered is better
                center_x = rect['x'] + rect['width'] / 2
                viewport_center = viewport_width / 2
                distance_from_center = abs(center_x - viewport_center)
                centrality_score = max(0, 100 - (distance_from_center / viewport_width * 100))
                score += centrality_score
                
                if score > best_score:
                    best_score = score
                    best_stimulus = stimulus
            
            if best_stimulus:
                rect = best_stimulus.rect
                print(f"    ✅ Found CENTER/TOP content (Questions 1-2 type)")
                print(f"       Position: x={rect['x']}px (score: {int(best_score)})")
                print(f"       Size: {rect['width']}x{rect['height']}px")
                
                # Get scrolling info
                stimulus_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", best_stimulus)
                
                # Get parent for scrolling control
                parent = self.driver.execute_script("return arguments[0].parentElement;", best_stimulus)
                parent_rect = parent.rect
                parent_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", parent)
                
                print(f"       Content height: {stimulus_scroll}px, visible: {rect['height']}px")
                
                # Check if scrollable
                if stimulus_scroll > rect['height'] + 50 or parent_scroll > parent_rect['height'] + 50:
                    print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                    
                    max_scroll = max(stimulus_scroll, parent_scroll)
                    max_visible = max(rect['height'], parent_rect['height'])
                    zoom_needed = max_visible / max_scroll
                    zoom_level = max(0.25, min(0.5, zoom_needed))
                    
                    print(f"       Setting zoom to {int(zoom_level * 100)}%")
                    
                    self.driver.execute_script("arguments[0].scrollTop = 0;", parent)
                    time.sleep(0.3)
                    
                    self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", best_stimulus)
                    time.sleep(0.5)
                    
                    screenshot_data = best_stimulus.screenshot_as_png
                    img = Image.open(io.BytesIO(screenshot_data))
                    
                    self.driver.execute_script("arguments[0].style.zoom = '1';", best_stimulus)
                    time.sleep(0.3)
                    
                    filename = f"Q{question_num}_stimulus.png"
                    filepath = os.path.join(images_folder, filename)
                    img.save(filepath, 'PNG', quality=95)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Full Centered Content'
                    })
                    
                    print(f"    ✅ Captured FULL centered content with zoom!")
                    print(f"       Final dimensions: {img.width}x{img.height}px")
                    return screenshots
                
                else:
                    print(f"    📸 Content fits - normal capture")
                    
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});", 
                        best_stimulus
                    )
                    time.sleep(0.3)
                    
                    screenshot_data = best_stimulus.screenshot_as_png
                    img = Image.open(io.BytesIO(screenshot_data))
                    
                    filename = f"Q{question_num}_stimulus.png"
                    filepath = os.path.join(images_folder, filename)
                    img.save(filepath, 'PNG', quality=95)
                    
                    screenshots.append({
                        'filename': filename,
                        'description': 'Centered Content'
                    })
                    
                    print(f"    ✅ Captured centered content!")
                    return screenshots
            
            print(f"    ⚠️ No suitable content found")
            
        except Exception as e:
            print(f"    ❌ Center content detection failed: {e}")
            import traceback
            traceback.print_exc()
        
        return screenshots
        
    except Exception as e:
        print(f"    ❌ Screenshot error: {e}")
        import traceback
        traceback.print_exc()
        return []
    try:
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        os.makedirs(images_folder, exist_ok=True)
        
        screenshots = []
        
        print(f"   🔍 Searching for content to capture...")
        
        # STRATEGY 1: Check for TOP/CENTER image layout FIRST (questions 1, 2)
        # This is the most common layout, so check it before left panels
        try:
            # Look for images in the center/top area
            all_images = self.driver.find_elements(By.TAG_NAME, 'img')
            
            for img in all_images:
                if not img.is_displayed():
                    continue
                
                # Check if image is substantial size
                img_size = img.size
                img_rect = img.rect
                
                if img_size['width'] < 200 or img_size['height'] < 200:
                    continue
                
                # Check if image is in the CENTER area (not on left side)
                # Left panels are typically x < 700, center images are x > 700
                if img_rect['x'] > 700 and img_rect['x'] < 1500:
                    print(f"    ✅ Found CENTERED image at top")
                    print(f"       Position: x={img_rect['x']}px, y={img_rect['y']}px")
                    print(f"       Size: {img_size['width']}x{img_size['height']}px")
                    
                    # Find the container that holds this image (usually .lrn_stimulus_content)
                    # Go up the DOM tree to find the stimulus container
                    stimulus = self.driver.execute_script("""
                        let el = arguments[0];
                        while (el && el.parentElement) {
                            el = el.parentElement;
                            if (el.classList && (
                                el.classList.contains('lrn_stimulus_content') ||
                                el.classList.contains('lrn-stimulus-content') ||
                                el.className.includes('stimulus')
                            )) {
                                return el;
                            }
                        }
                        return null;
                    """, img)
                    
                    if not stimulus:
                        # If no stimulus container found, try capturing just the image with some padding
                        print(f"       No stimulus container - capturing image with context")
                        
                        # Scroll image into view
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", 
                            img
                        )
                        time.sleep(0.5)
                        
                        # Capture the image
                        screenshot_data = img.screenshot_as_png
                        screenshot_img = Image.open(io.BytesIO(screenshot_data))
                        
                        filename = f"Q{question_num}_image.png"
                        filepath = os.path.join(images_folder, filename)
                        screenshot_img.save(filepath, 'PNG', quality=95)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Centered Question Image'
                        })
                        
                        print(f"    ✅ Captured centered image!")
                        return screenshots
                    
                    # Found stimulus container - check if it's scrollable
                    stimulus_rect = stimulus.rect
                    stimulus_scroll = self.driver.execute_script("return arguments[0].scrollHeight;", stimulus)
                    
                    print(f"       Stimulus container found")
                    print(f"       Content height: {stimulus_scroll}px, visible: {stimulus_rect['height']}px")
                    
                    # Check if we need to zoom
                    if stimulus_scroll > stimulus_rect['height'] + 50:
                        print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                        
                        # Get parent for scrolling
                        parent = self.driver.execute_script("return arguments[0].parentElement;", stimulus)
                        
                        # Calculate zoom needed
                        zoom_needed = stimulus_rect['height'] / stimulus_scroll
                        zoom_level = max(0.25, min(0.5, zoom_needed))
                        
                        print(f"       Setting zoom to {int(zoom_level * 100)}%")
                        
                        # Scroll to top
                        self.driver.execute_script("arguments[0].scrollTop = 0;", parent)
                        time.sleep(0.3)
                        
                        # Apply zoom
                        self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", stimulus)
                        time.sleep(0.5)
                        
                        # Take screenshot
                        screenshot_data = stimulus.screenshot_as_png
                        screenshot_img = Image.open(io.BytesIO(screenshot_data))
                        
                        # Reset zoom
                        self.driver.execute_script("arguments[0].style.zoom = '1';", stimulus)
                        time.sleep(0.3)
                        
                        filename = f"Q{question_num}_stimulus.png"
                        filepath = os.path.join(images_folder, filename)
                        screenshot_img.save(filepath, 'PNG', quality=95)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Full Centered Stimulus'
                        })
                        
                        print(f"    ✅ Captured FULL centered stimulus with zoom!")
                        print(f"       Final dimensions: {screenshot_img.width}x{screenshot_img.height}px")
                        return screenshots
                    
                    else:
                        # Content fits - normal capture
                        print(f"    📸 Content fits - normal capture")
                        
                        # Scroll to make fully visible
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});", 
                            stimulus
                        )
                        time.sleep(0.3)
                        
                        screenshot_data = stimulus.screenshot_as_png
                        screenshot_img = Image.open(io.BytesIO(screenshot_data))
                        
                        filename = f"Q{question_num}_stimulus.png"
                        filepath = os.path.join(images_folder, filename)
                        screenshot_img.save(filepath, 'PNG', quality=95)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Centered Stimulus'
                        })
                        
                        print(f"    ✅ Captured centered stimulus!")
                        return screenshots
            
            print(f"    ℹ️ No centered images found - checking for left panel...")
            
        except Exception as e:
            print(f"    ⚠️ Center image detection failed: {e}")
            import traceback
            traceback.print_exc()
        
        # STRATEGY 2: Find left panel (for questions 3, 4, 5 type)
        left_panel = None
        
        try:
            left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                '.two-columns.left-column.question-content')
            if left_panel and left_panel.is_displayed():
                print(f"    ✅ Found LEFT PANEL")
        except:
            pass
        
        if not left_panel:
            try:
                left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                    '[data-lrn-widget-type="feature"][class*="left-column"]')
                if left_panel and left_panel.is_displayed():
                    print(f"    ✅ Found LEFT PANEL by data attribute")
            except:
                pass
        
        if not left_panel:
            try:
                panels = self.driver.find_elements(By.CSS_SELECTOR, '[class*="left-column"]')
                for panel in panels:
                    if panel.is_displayed():
                        rect = panel.rect
                        # Left panels should be on the LEFT side (x < 700) and substantial size
                        if rect['width'] > 400 and rect['height'] > 400 and rect['x'] < 700:
                            left_panel = panel
                            print(f"    ✅ Found LEFT PANEL by class search")
                            break
            except:
                pass
        
        # If we found a left panel, capture it
        if left_panel:
            rect = left_panel.rect
            scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", left_panel)
            
            print(f"    📏 Panel dimensions:")
            print(f"       - Position: x={rect['x']}px")
            print(f"       - Visible height: {rect['height']}px")
            print(f"       - Total content height: {scroll_height}px")
            print(f"       - Width: {rect['width']}px")
            
            # Check if content is taller than visible area
            if scroll_height > rect['height'] + 50:
                print(f"    🔍 Content is scrollable - using ZOOM OUT method...")
                
                # Calculate zoom level needed to fit all content
                zoom_needed = rect['height'] / scroll_height
                zoom_level = max(0.25, min(0.5, zoom_needed))
                
                print(f"       Setting zoom to {int(zoom_level * 100)}%")
                
                # Scroll to top
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                # Apply zoom to the panel
                self.driver.execute_script(f"arguments[0].style.zoom = '{zoom_level}';", left_panel)
                time.sleep(0.5)
                
                # Take screenshot
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                # Reset zoom
                self.driver.execute_script("arguments[0].style.zoom = '1';", left_panel)
                time.sleep(0.3)
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured FULL panel with zoom!")
                print(f"       Final dimensions: {img.width}x{img.height}px")
                return screenshots
            
            else:
                # Content fits, normal capture
                print(f"    📸 Content fits in viewport - normal capture")
                
                self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
                time.sleep(0.3)
                
                screenshot_data = left_panel.screenshot_as_png
                img = Image.open(io.BytesIO(screenshot_data))
                
                filename = f"Q{question_num}_passage_panel.png"
                filepath = os.path.join(images_folder, filename)
                img.save(filepath, 'PNG', quality=95)
                
                screenshots.append({
                    'filename': filename,
                    'description': 'Full Passage Panel'
                })
                
                print(f"    ✅ Captured panel!")
                return screenshots
        
        # STRATEGY 3: Nothing found
        print(f"    ⚠️ No content found to capture")
        return screenshots
        
    except Exception as e:
        print(f"    ❌ Screenshot error: {e}")
        import traceback
        traceback.print_exc()
        return []
    """Take screenshot of passage/source material - SCROLL AND STITCH METHOD"""
    try:
        images_folder = os.path.join(OUTPUT_FOLDER, "quizizz_images")
        os.makedirs(images_folder, exist_ok=True)
        
        screenshots = []
        
        print(f"   🔍 Searching for left panel content...")
        
        # Try to find the left panel using multiple strategies
        left_panel = None
        
        # STRATEGY 1: Find by exact class combination
        try:
            left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                '.two-columns.left-column.question-content')
            if left_panel and left_panel.is_displayed():
                print(f"    ✅ Found LEFT PANEL by class combination!")
        except:
            pass
        
        # STRATEGY 2: Find by data attribute
        if not left_panel:
            try:
                left_panel = self.driver.find_element(By.CSS_SELECTOR, 
                    '[data-lrn-widget-type="feature"][class*="left-column"]')
                if left_panel and left_panel.is_displayed():
                    print(f"    ✅ Found LEFT PANEL by data attribute!")
            except:
                pass
        
        # STRATEGY 3: Find by class search
        if not left_panel:
            try:
                panels = self.driver.find_elements(By.CSS_SELECTOR, '[class*="left-column"]')
                for panel in panels:
                    if panel.is_displayed():
                        rect = panel.rect
                        if rect['width'] > 400 and rect['height'] > 400 and rect['x'] < 800:
                            left_panel = panel
                            print(f"    ✅ Found LEFT PANEL by class search!")
                            break
            except:
                pass
        
        # STRATEGY 4: Find by ID pattern
        if not left_panel:
            try:
                containers = self.driver.find_elements(By.CSS_SELECTOR, '[id$="-container"]')
                for container in containers:
                    if not container.is_displayed():
                        continue
                    widget_type = container.get_attribute('data-lrn-widget-type')
                    if widget_type == 'feature':
                        rect = container.rect
                        if rect['width'] > 400 and rect['height'] > 400:
                            left_panel = container
                            print(f"    ✅ Found LEFT PANEL by ID pattern!")
                            break
            except:
                pass
        
        # STRATEGY 5: Find via parent traversal
        if not left_panel:
            try:
                shared_passage = self.driver.find_element(By.CSS_SELECTOR, '.lrn_sharedpassage')
                if shared_passage:
                    parent_container = self.driver.execute_script(
                        "return arguments[0].parentElement.parentElement;", 
                        shared_passage
                    )
                    if parent_container and parent_container.is_displayed():
                        rect = parent_container.rect
                        if rect['width'] > 400 and rect['height'] > 400:
                            left_panel = parent_container
                            print(f"    ✅ Found LEFT PANEL via parent traversal!")
            except:
                pass
        
        if not left_panel:
            print(f"    ⚠️ No left panel found - checking for top image layout...")
            
            # FALLBACK: Look for image above the question
            try:
                # Strategy 1: Find the main content container (not the scrollable wrapper)
                # Look for elements that contain the actual content, not UI chrome
                content_containers = self.driver.find_elements(By.CSS_SELECTOR, 
                    '.lrn_stimulus_content, .lrn-stimulus-content, [class*="stimulus"]')
                
                for stimulus in content_containers:
                    if not stimulus.is_displayed():
                        continue
                    
                    # Get the parent that might be scrollable
                    parent = self.driver.execute_script("return arguments[0].parentElement;", stimulus)
                    parent_scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", parent)
                    parent_rect = parent.rect
                    
                    # Check if this stimulus contains content
                    has_image = len(stimulus.find_elements(By.TAG_NAME, 'img')) > 0
                    has_text = len(stimulus.text.strip()) > 50
                    
                    if not (has_image or has_text):
                        continue
                    
                    print(f"    ✅ Found stimulus content area")
                    print(f"       Parent dimensions:")
                    print(f"       - Visible height: {parent_rect['height']}px")
                    print(f"       - Scroll height: {parent_scroll_height}px")
                    
                    # Get actual content height (not including UI elements)
                    stimulus_rect = stimulus.rect
                    stimulus_height = self.driver.execute_script("return arguments[0].scrollHeight;", stimulus)
                    
                    print(f"       Content dimensions:")
                    print(f"       - Content height: {stimulus_height}px")
                    print(f"       - Visible: {stimulus_rect['height']}px")
                    
                    # Check if content is taller than visible area
                    if stimulus_height > stimulus_rect['height'] + 50 or parent_scroll_height > parent_rect['height'] + 50:
                        print(f"    📸 Content is scrollable - need to capture full content...")
                        
                        # Use the PARENT for scrolling but capture the STIMULUS content
                        # Scroll parent to top
                        self.driver.execute_script("arguments[0].scrollTop = 0;", parent)
                        time.sleep(0.5)
                        
                        # Get dimensions
                        viewport_height = parent_rect['height']
                        total_content_height = max(stimulus_height, parent_scroll_height)
                        
                        # Calculate sections needed
                        overlap = 100
                        scroll_amount = viewport_height - overlap
                        num_sections = max(1, int((total_content_height - viewport_height) / scroll_amount) + 1)
                        
                        print(f"       Will capture {num_sections + 1} sections")
                        
                        screenshot_sections = []
                        
                        for section_num in range(num_sections + 1):
                            # Calculate scroll position
                            if section_num == 0:
                                scroll_pos = 0
                            elif section_num == num_sections:
                                scroll_pos = max(0, total_content_height - viewport_height)
                            else:
                                scroll_pos = section_num * scroll_amount
                            
                            scroll_pos = min(scroll_pos, total_content_height - viewport_height)
                            scroll_pos = max(scroll_pos, 0)
                            
                            # Scroll parent
                            self.driver.execute_script(f"arguments[0].scrollTop = {scroll_pos};", parent)
                            time.sleep(0.4)
                            
                            # Capture the STIMULUS (content), not the parent (which includes UI)
                            screenshot_data = stimulus.screenshot_as_png
                            section_img = Image.open(io.BytesIO(screenshot_data))
                            screenshot_sections.append((scroll_pos, section_img))
                            
                            print(f"       Section {section_num + 1}: scroll={scroll_pos}px, captured {section_img.height}px")
                            
                            if scroll_pos >= total_content_height - viewport_height:
                                break
                        
                        # For stitching, we need to be smarter about overlaps
                        print(f"    🔗 Stitching {len(screenshot_sections)} sections...")
                        
                        # Use the maximum height we can get
                        if len(screenshot_sections) == 1:
                            # Only one section, use it directly
                            final_img = screenshot_sections[0][1]
                        else:
                            # Multiple sections - stitch them
                            total_width = screenshot_sections[0][1].width
                            
                            # Calculate actual total height from scroll positions
                            last_scroll_pos = screenshot_sections[-1][0]
                            last_img_height = screenshot_sections[-1][1].height
                            total_height = last_scroll_pos + last_img_height
                            
                            stitched = Image.new('RGB', (total_width, total_height), (255, 255, 255))
                            
                            # Paste sections at their scroll positions
                            for scroll_pos, section_img in screenshot_sections:
                                stitched.paste(section_img, (0, scroll_pos))
                            
                            final_img = stitched
                        
                        filename = f"Q{question_num}_stimulus_FULL.png"
                        filepath = os.path.join(images_folder, filename)
                        final_img.save(filepath, 'PNG', quality=95)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Full Stimulus Content'
                        })
                        
                        print(f"    ✅ Captured FULL stimulus!")
                        print(f"       Final dimensions: {final_img.width}x{final_img.height}px")
                        return screenshots
                    
                    else:
                        # Content fits in view - simple capture
                        print(f"    📸 Content fits in view - simple capture")
                        
                        # Scroll to make sure it's fully visible
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({behavior: 'instant', block: 'start'});", 
                            stimulus
                        )
                        time.sleep(0.5)
                        
                        screenshot_data = stimulus.screenshot_as_png
                        final_img = Image.open(io.BytesIO(screenshot_data))
                        
                        filename = f"Q{question_num}_stimulus.png"
                        filepath = os.path.join(images_folder, filename)
                        final_img.save(filepath, 'PNG', quality=95)
                        
                        screenshots.append({
                            'filename': filename,
                            'description': 'Stimulus Content'
                        })
                        
                        print(f"    ✅ Captured stimulus!")
                        return screenshots
                
                print(f"    ⚠️ No suitable stimulus content found")
                
            except Exception as e:
                print(f"    ❌ Stimulus capture failed: {e}")
                import traceback
                traceback.print_exc()
            
            return []
        
        # Get dimensions
        rect = left_panel.rect
        viewport_height = rect['height']
        scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", left_panel)
        
        print(f"    📏 Panel dimensions:")
        print(f"       - Visible height: {viewport_height}px")
        print(f"       - Total content height: {scroll_height}px")
        print(f"       - Width: {rect['width']}px")
        
        # If content fits in viewport, take single screenshot
        if scroll_height <= viewport_height + 50:
            print(f"    📸 Content fits in viewport - single screenshot")
            
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
            
            print(f"    ✅ Captured panel!")
            return screenshots
        
        # Content is scrollable - need to stitch multiple screenshots
        print(f"    📸 Content is scrollable - capturing in sections...")
        
        # Scroll to top
        self.driver.execute_script("arguments[0].scrollTop = 0;", left_panel)
        time.sleep(0.5)
        
        # Calculate how many sections we need
        overlap = 100  # Increased overlap for better matching
        scroll_amount = viewport_height - overlap
        num_sections = int((scroll_height - viewport_height) / scroll_amount) + 1
        
        if num_sections < 1:
            num_sections = 1
        
        print(f"       Will capture {num_sections} sections")
        
        # Take screenshots while scrolling
        screenshot_sections = []
        
        for section_num in range(num_sections + 1):
            # Calculate scroll position
            if section_num == 0:
                scroll_pos = 0
            elif section_num == num_sections:
                # Last section - scroll to bottom
                scroll_pos = scroll_height - viewport_height
            else:
                scroll_pos = section_num * scroll_amount
            
            # Ensure we don't scroll past the end
            scroll_pos = min(scroll_pos, scroll_height - viewport_height)
            scroll_pos = max(scroll_pos, 0)
            
            # Scroll to position
            self.driver.execute_script(f"arguments[0].scrollTop = {scroll_pos};", left_panel)
            time.sleep(0.4)
            
            # Take screenshot
            screenshot_data = left_panel.screenshot_as_png
            img = Image.open(io.BytesIO(screenshot_data))
            screenshot_sections.append((scroll_pos, img))
            
            print(f"       Section {section_num + 1}: scroll={scroll_pos}px")
            
            # If we've reached the bottom, stop
            if scroll_pos >= scroll_height - viewport_height:
                break
        
        # Stitch images together
        print(f"    🔗 Stitching {len(screenshot_sections)} sections...")
        
        # Calculate final image dimensions
        total_width = screenshot_sections[0][1].width
        total_height = scroll_height
        
        # Create blank canvas
        stitched = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        
        # Paste each section at its correct position
        for scroll_pos, section_img in screenshot_sections:
            # Paste the section at the correct Y position
            stitched.paste(section_img, (0, scroll_pos))
        
        # Save stitched image
        filename = f"Q{question_num}_passage_panel_FULL.png"
        filepath = os.path.join(images_folder, filename)
        stitched.save(filepath, 'PNG', quality=95)
        
        screenshots.append({
            'filename': filename,
            'description': 'Full Passage Panel (Stitched)'
        })
        
        print(f"    ✅ Captured FULL scrollable panel!")
        print(f"       Final dimensions: {total_width}x{total_height}px")
        
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
        print(f"   🔍 Extracting content...")
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
    """Save results in Quizizz CSV format with UNIQUE filename"""
    # Create unique filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(output_file)[0]
    unique_file = f"{base_name}_{timestamp}.csv"
    
    with open(unique_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # Quizizz CSV header
        writer.writerow(['Question', 'Question Type', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Option 5', 'Correct Answer', 'Image Link'])
        
        for result in self.ocr_results:
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
    
    print(f"\n💾 Saved Quizizz CSV: {unique_file}")
    return unique_file

def cleanup(self):
    """Close browser and cleanup"""
    try:
        keyboard.unhook_all()
    except:
        pass
    self.driver.quit()
```

def main():
print(”=” * 80)
print(“AP CLASSROOM EXTRACTOR - WITH IMAGES & QUIZIZZ EXPORT”)
print(”=” * 80)

```
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
    print("    5. Press ESC at any time to stop")
    print("=" * 80)
    input()
    
    print(f"\n▶  Starting...")
    print(f"    Questions: {MAX_CLICKS}")
    print(f"    Wait: {WAIT_TIME}s\n")
    
    # Run automation
    ocr.run_automation(MAX_CLICKS, WAIT_TIME, OUTPUT_FOLDER)
    
    if not ocr.ocr_results:
        print("❌ No results to save!")
        return
    
    # Upload screenshots
    print(f"\n📤 Uploading images to ImgBB...")
    total_uploaded = ocr.upload_all_screenshots()
    
    # Save Quizizz CSV
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
    
    print("\n🎮 QUIZIZZ IMPORT STEPS:")
    print("   1. Go to quizizz.com → Create → Quiz")
    print("   2. Click 'Import from Spreadsheet'")
    print("   3. Upload the CSV file")
    if total_uploaded > 0:
        print("   4. All images will automatically load from ImgBB URLs! 🎉")
    print("   5. Set correct answers")
    print("   6. Share your quiz!")
    
    print("=" * 80)
    
except KeyboardInterrupt:
    print("\n\n⚠️ Cancelled by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    ocr.cleanup()
    print("\n👋 Closed")
```

if **name** == “**main**”:
main()
