import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = [
    r"D:\VAIC2026-hehehe\data\crawl\sbv\items\4201ee74e543b086.json",
    r"D:\VAIC2026-hehehe\data\crawl\sbv\items\495e06eefe45e6dc.json",
    r"D:\VAIC2026-hehehe\data\crawl\sbv\items\81a7ec11eb462ee4.json"
]

for fpath in files:
    with open(fpath, encoding='utf-8') as f:
        doc = json.load(f)
    
    print(f"\n{'='*80}")
    print(f"DOC: {doc['doc_number']}")
    doc_title = doc['title'][:100]
    print(f"Title: {doc_title}")
    print(f"Type: {doc['doc_type']}")
    
    text = doc.get('full_text', '')
    dieu_count = len(re.findall(r'Dieu\s+\d+', text, re.UNICODE))
    print(f"Structure - Dieu: {dieu_count} items")
    print(f"Text length: {len(text)}")
    
    # Check for numbers
    nums = re.findall(r'\d+(?:\.\d+)?(?:%)?', text[:3000])
    print(f"Numbers in first 3000 chars: {len(nums)}")
    print(f"Sample: {text[:400]}")
