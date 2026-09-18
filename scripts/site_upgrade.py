from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'data-matrix-audit-upgrade="v1"'

NAV = '''<header class="site-upgrade-bar" {marker}><div class="mu-inner"><a class="mu-brand" href="{root}"><span class="mu-dot"></span>MATRIX AUDIT</a><nav class="mu-links"><a href="{root}">Question</a><a href="{root}dar.html">DAR</a><a href="{root}verification.html">Verification</a><a href="{root}case-studies.html">Evidence</a><a href="{root}break-it.html">Break It</a><a href="{root}review.html">Private Review</a><a class="mu-cta" href="{root}break-it.html">TEST THE BOUNDARY →</a></nav></div></header><div class="site-upgrade-status"><strong>A11 STATUS:</strong> independent runtime/interface audit pending · the project does not claim a PASS before independent evidence</div>'''

PANEL = '''<section class="site-upgrade-shell" aria-label="Independent adversarial review"><div class="site-upgrade-panel"><div class="kicker">Independent verification</div><h2>Do not trust the boundary. Try to break it.</h2><p>Matrix Audit is seeking independent security researchers to test the declared boundary against alternate execution paths. The audit is intentionally falsifiable: a reproducible bypass is a finding, not a failure of the research process.</p><div class="mu-actions"><a class="mu-button primary" href="{root}break-it.html">Open the A11 challenge →</a><a class="mu-button" href="{root}verification.html">See verification posture →</a><a class="mu-button" href="https://github.com/liranbarshrim-ui/human-stop-boundary/issues/12">GitHub challenge →</a></div><div class="mu-evidence-grid"><article><b>V1–V3</b><strong>Identity · IPC · processes</strong><span>Try alternate identities, transports, helpers and child-process paths.</span></article><article><b>V4–V6</b><strong>Interfaces · recovery · TOCTOU</strong><span>Look for direct adapters, recovery bypasses, descriptor substitution and races.</span></article><article><b>V7–V8</b><strong>Side channels · rollback</strong><span>Test network/plugin routes and attempts to restore state before a fresh protected commit.</span></article></div></div></section>'''

FOOTER = '''<footer class="site-upgrade-footer"><div class="mu-inner"><span>Matrix Audit · Decision Accountability Review · Liran Bar-Shrim · 2026</span><span><a href="{root}about.html">About</a> · <a href="{root}faq.html">FAQ</a> · <a href="{root}goodfaith.html">Good Faith</a> · <a href="https://github.com/liranbarshrim-ui/human-stop-boundary">Repository</a></span></div></footer>'''


def root_for(path: Path) -> str:
    depth = len(path.relative_to(ROOT).parts) - 1
    return '../' * depth


def upgrade(path: Path) -> bool:
    if path.name in {'break-it.html', 'verification.html'}:
        return False
    text = path.read_text(encoding='utf-8')
    if MARKER in text or '<html' not in text.lower():
        return False
    root = root_for(path)
    nav = NAV.format(marker=MARKER, root=root)
    panel = PANEL.format(root=root)
    footer = FOOTER.format(root=root)
    if '</head>' not in text.lower() or '<body' not in text.lower():
        return False
    head_close = text.lower().find('</head>')
    text = text[:head_close] + '<link rel="stylesheet" href="' + root + 'site-upgrade.css">\n' + text[head_close:]
    body_open = text.lower().find('>', text.lower().find('<body')) + 1
    text = text[:body_open] + nav + text[body_open:]
    body_close = text.lower().rfind('</body>')
    text = text[:body_close] + panel + footer + text[body_close:]
    path.write_text(text, encoding='utf-8')
    return True


changed = []
for path in sorted(ROOT.rglob('*.html')):
    if '.git' in path.parts:
        continue
    if upgrade(path):
        changed.append(str(path.relative_to(ROOT)))

print(f'Upgraded {len(changed)} HTML pages')
for item in changed:
    print(item)
