import json
from app.main import app
spec = app.openapi()
with open(r'D:\AI\project-aura\IAM_OPENAPI.json', 'w', encoding='utf-8', newline='\n') as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
web_paths = [p for p in spec['paths'] if '/web/' in p]
ai_paths = [p for p in spec['paths'] if '/ai-communication/' in p]
print('Web routes:', len(web_paths), 'AI communication routes:', len(ai_paths), 'Total:', len(spec['paths']), 'paths,', len(spec['components']['schemas']), 'schemas')
