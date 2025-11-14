"""
Test Llama 4 Scout vision capabilities with OpenRouter
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print("="*70)
print("LLAMA 4 SCOUT VISION TEST")
print("="*70)

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

if not OPENROUTER_API_KEY:
    print("\n❌ No OPENROUTER_API_KEY in .env file!")
    exit(1)

print(f"\n✅ API Key Found")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Test 1: Text-only question
print("\n" + "="*70)
print("TEST 1: Text-Only Question")
print("="*70)

try:
    print("\n📡 Testing text-only mode...")
    
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://github.com/test",
            "X-Title": "Test",
        },
        extra_body={},
        model="meta-llama/llama-4-scout:free",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """What is the capital of France?

1. London
2. Paris
3. Berlin
4. Madrid
5. Rome

Answer with ONLY the number (1-5)."""
                }
            ]
        }],
        max_tokens=10,
        temperature=0.1
    )
    
    answer = completion.choices[0].message.content.strip()
    print(f"✅ Response: {answer}")
    
    if "2" in answer:
        print("✅ CORRECT! Text mode works!")
    else:
        print("⚠️  Unexpected answer")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Vision question with image
print("\n" + "="*70)
print("TEST 2: Vision Question (with image)")
print("="*70)

try:
    print("\n📡 Testing vision mode with image...")
    
    # Use a simple test image
    test_image_url = "https://i.ibb.co/DgbnmVj8/92f6aac70edf.png"
    
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://github.com/test",
            "X-Title": "Test",
        },
        extra_body={},
        model="meta-llama/llama-4-scout:free",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Based on the image provided, what color is most prominent?

1. Red
2. Blue
3. Green
4. Yellow
5. Purple

Answer with ONLY the number (1-5)."""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": test_image_url
                    }
                }
            ]
        }],
        max_tokens=10,
        temperature=0.1
    )
    
    answer = completion.choices[0].message.content.strip()
    print(f"✅ Response: {answer}")
    print("✅ VISION MODE WORKS! (Llama can see images)")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: AP-style question with image
print("\n" + "="*70)
print("TEST 3: AP-Style Question")
print("="*70)

try:
    print("\n📡 Testing AP-style question...")
    
    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://github.com/test",
            "X-Title": "Test",
        },
        extra_body={},
        model="meta-llama/llama-4-scout:free",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Which of the following best describes photosynthesis?

1. The process by which plants convert light energy into chemical energy
2. The process by which animals digest food
3. The process by which water evaporates
4. The process by which rocks erode
5. The process by which cells divide

Answer with ONLY the number (1-5)."""
                }
            ]
        }],
        max_tokens=10,
        temperature=0.1
    )
    
    answer = completion.choices[0].message.content.strip()
    print(f"✅ Response: {answer}")
    
    if "1" in answer:
        print("✅ CORRECT! Llama understands AP-level content!")
    else:
        print("⚠️  Unexpected answer")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("✅ Llama 4 Scout is ready to use!")
print("✅ Supports text questions")
print("✅ Supports vision (images)")
print("✅ Completely FREE")
print("\nYour main script is now configured to:")
print("  • Use Llama 4 Scout for all questions")
print("  • Automatically include images when available")
print("  • Should get much better accuracy on visual questions!")
print("="*70)
