"""
Quick Gemini API Test - 30 seconds
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

print("🧪 QUICK GEMINI API TEST")
print("=" * 50)

if not GEMINI_API_KEY:
    print("❌ No API key found in .env file!")
    exit(1)

print(f"✅ API Key: {GEMINI_API_KEY[:20]}...")

# Test the API
print("\n📡 Testing gemini-2.5-flash...")

api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

payload = {
    "contents": [{
        "parts": [{
            "text": "What is 2+2? Answer with only the number."
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
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        answer = data['candidates'][0]['content']['parts'][0]['text']
        print(f"\n✅ SUCCESS! API is working!")
        print(f"Response: {answer}")
        print("\n🎉 Your API key is valid and ready to use!")
    elif response.status_code == 429:
        print("\n⚠️  Rate limited - but API key works!")
        print("Wait a minute and try again.")
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")

print("=" * 50)
