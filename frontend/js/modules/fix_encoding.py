# Fix double-encoded UTF-8 (UTF-8 interpreted as Latin-1 and re-encoded as UTF-8)
import codecs

with open('checkout.js', 'rb') as f:
    raw = f.read()

# The file was UTF-8 but got corrupted by being read as Latin-1 and written as UTF-8
# We need to reverse this: decode as UTF-8, encode as Latin-1, decode as UTF-8
try:
    # First decode from whatever encoding it is now
    text = raw.decode('utf-8')
    
    # Check if it's double-encoded
    if 'Р' in text and 'С' in text:  # Signs of double-encoding
        print("Detected double-encoded UTF-8, fixing...")
        # The text was UTF-8 bytes interpreted as CP1252/Latin1, then encoded to UTF-8
        # Reverse: decode UTF-8 -> encode to Latin-1 -> decode UTF-8
        fixed = text.encode('cp1252').decode('utf-8')
        
        with open('checkout.js', 'w', encoding='utf-8', newline='\n') as f:
            f.write(fixed)
        print("Fixed! File rewritten with correct encoding.")
        print(f"First 200 chars: {fixed[:200]}")
    else:
        print("File doesn't appear to be double-encoded")
        print(f"First 200 chars: {text[:200]}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

