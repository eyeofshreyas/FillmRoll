import re
import os

with open('static/styles.css', encoding='utf-8') as f:
    text = f.read()

# Split the string using the distinctive box separator
# We'll split on something safe like '/* ════════'
# But re.split lets us capture the delimiter so we don't lose it if we want it,
# or we can just findall. Actually, a simple iterative split is easier.

parts = re.split(r'(/\*\s*═+((?:\n|.)*?)═+\s*\*/)', text)
# parts[0] is the text before the first header (the global CSS)
# parts[1] is the entire header match
# parts[2] is the group inside the header (e.g. '\n   TOKENS\n')
# parts[3] is the text after the first header, up to the second header...

blocks = []
blocks.append({'name': 'BASE', 'content': parts[0]})

for i in range(1, len(parts), 3):
    header_full = parts[i]
    name = parts[i+1].strip()
    content = parts[i+2]
    blocks.append({'name': name, 'content': header_full + content})

# Groupings
mapping = {
    'BASE': 'base.css',
    'TOKENS': 'base.css',
    'FADE-IN UTILITY': 'base.css',
    'SPINNER': 'base.css',

    'HEADER': 'layout.css',
    'FOOTER': 'layout.css',
    'RESPONSIVE': 'layout.css',
    'FOR YOU  nav badge': 'layout.css',
    'MOBILE BOTTOM NAV': 'layout.css',
    
    # We'll also catch plain text anomalies based on prefixes if encoding fails
}

def get_filename(name):
    upper = name.upper()
    if 'TOKEN' in upper or 'FADE' in upper or 'SPINNER' in upper or name == 'BASE':
        return 'base.css'
    if 'HEADER' in upper or 'FOOTER' in upper or 'RESPONSIVE' in upper or 'FOR YOU' in upper or 'MOBILE' in upper:
        return 'layout.css'
    if 'HERO' in upper or 'HOME' in upper or 'TRENDING' in upper or 'GENRE' in upper or 'MOOD' in upper:
        return 'home.css'
    if 'RESULTS' in upper:
        return 'cards.css'
    if 'MODAL' in upper or 'STAR' in upper:
        return 'modal.css'
    if 'AI CHAT' in upper:
        return 'ai.css'
    if 'REVIEW' in upper:
        return 'reviews.css'
    return 'misc.css'

os.makedirs('static/css', exist_ok=True)

file_contents = {}

for b in blocks:
    fn = get_filename(b['name'])
    file_contents.setdefault(fn, []).append(b['content'])

# matchmaker UI CSS was added dynamically by replace_file_content at the bottom, without a box header.
# Let's extract everything after the last block. Wait, the last block will just contain it.

for fn, contents in file_contents.items():
    with open(f'static/css/{fn}', 'w', encoding='utf-8') as f:
        f.write('\n'.join(contents))
        
print("CSS files created successfully:", list(file_contents.keys()))
