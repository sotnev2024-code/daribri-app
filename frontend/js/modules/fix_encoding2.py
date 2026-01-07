# Try multiple decode/encode combinations
import codecs

with open('checkout.js', 'rb') as f:
    raw = f.read()

# Remove BOM if present
if raw.startswith(codecs.BOM_UTF16_LE):
    raw = raw[2:]
    print("Removed UTF-16 LE BOM")
elif raw.startswith(codecs.BOM_UTF16_BE):
    raw = raw[2:]
    print("Removed UTF-16 BE BOM")
elif raw.startswith(codecs.BOM_UTF8):
    raw = raw[3:]
    print("Removed UTF-8 BOM")

# Try UTF-16 LE (PowerShell default)
try:
    text = raw.decode('utf-16-le')
    if 'function' in text and ('checkout' in text.lower() or 'Checkout' in text):
        print("SUCCESS: Decoded as UTF-16-LE")
        # Write back as UTF-8
        with open('checkout.js', 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print(f"Written back as UTF-8. First 300 chars:\n{text[:300]}")
        exit(0)
except Exception as e:
    print(f"UTF-16-LE failed: {e}")

# Try other encodings
for enc in ['utf-16', 'utf-8', 'cp1251', 'latin-1']:
    try:
        text = raw.decode(enc)
        if 'function' in text:
            print(f"Decoded with {enc}. First 300 chars:\n{text[:300]}")
    except Exception as e:
        print(f"{enc}: {e}")

