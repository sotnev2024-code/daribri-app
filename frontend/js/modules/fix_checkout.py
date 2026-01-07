import codecs
import os

# Read the corrupted file
with open('checkout.js', 'rb') as f:
    content = f.read()

# Try to decode with different encodings
for enc in ['utf-16-le', 'utf-16', 'utf-8-sig', 'utf-8', 'cp1251', 'latin-1']:
    try:
        text = content.decode(enc)
        print(f'Trying {enc}: first 100 chars = {repr(text[:100])}')
        if 'function' in text and 'checkout' in text.lower():
            print(f'SUCCESS with encoding: {enc}')
            # Write back with UTF-8
            with open('checkout_fixed.js', 'w', encoding='utf-8') as f:
                f.write(text)
            print('Fixed file written to checkout_fixed.js')
            break
    except Exception as e:
        print(f'{enc} failed: {e}')

