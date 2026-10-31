import json
import re

with open("core/brain.py", "r", encoding="utf-8") as f:
    text = f.read()

names = re.findall(r'"name":\s*"([a-zA-Z0-9_]+)"', text)
print(f"Total tools: {len(names)}")
for n in names:
    print(" -", n)
