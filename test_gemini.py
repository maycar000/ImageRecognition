"""
Gemini API Diagnostic - Check available models and test API key
"""
import os
import requests
from dotenv import load_dotenv

# Load API key
load_dotenv()
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

print("="*70)
print("GEMINI API DIAGNOSTIC")
print("="*70)

if not GEMINI_API_KEY:
    print("❌ No API key found!")
    exit(1)

print(f"✅ API Key found: {GEMINI_API_KEY[:20]}...")

# Test 1: List available models
print("\n" + "="*70)
print("TEST 1: Listing Available Models")
print("="*70)

list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"

try:
    response = requests.get(list_url, timeout=10)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'models' in data:
            print(f"\n✅ Found {len(data['models'])} models:\n")
            for model in data['models']:
                name = model.get('name', 'Unknown')
                display_name = model.get('displayName', 'Unknown')
                supported = model.get('supportedGenerationMethods', [])
                print(f"  • {name}")
                print(f"    Display: {display_name}")
                print(f"    Methods: {', '.join(supported)}")
                print()
        else:
            print("⚠️  No models found in response")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Try different model names with a simple prompt
print("\n" + "="*70)
print("TEST 2: Testing Model Endpoints")
print("="*70)

test_models = [
    "gemini-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "models/gemini-pro",
    "models/gemini-1.5-pro",
    "models/gemini-1.5-flash",
]

test_prompt = "Answer with only the number 1"

for model_name in test_models:
    print(f"\nTesting: {model_name}")
    
    # Try v1beta
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": test_prompt
            }]
        }]
    }
    
    try:
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"  ✅ SUCCESS! Status: {response.status_code}")
            data = response.json()
            if 'candidates' in data:
                text = data['candidates'][0]['content']['parts'][0]['text']
                print(f"  Response: {text}")
        else:
            print(f"  ❌ Failed: {response.status_code}")
            error = response.json().get('error', {})
            print(f"  Error: {error.get('message', 'Unknown')[:80]}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print("\n💡 Next Steps:")
print("  1. Check which models returned ✅ SUCCESS")
print("  2. Use that model name in screenshot_automation.py")
print("  3. If none work, your API key may need activation at:")
print("     https://makersuite.google.com/app/apikey")
