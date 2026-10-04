# Usage: python3 scripts/add_hub_link.py <slug> "<EN link text>" "<JA link text>"  (adds a KanColle hub cluster link, EN+JA)
import sys
S='style="color:var(--accent);font-weight:700;text-decoration:none;"'
slug,en,ja=sys.argv[1:4]
for f,pre,txt in [("games/kancolle/index.html","/games/kancolle/",en),("ja/games/kancolle/index.html","/ja/games/kancolle/",ja)]:
    s=open(f).read()
    lines=[l for l in s.split("\n") if 'class="cluster-link"' in l]
    anchor=lines[-1]+"\n"
    if f'{pre}{slug}/' in s: continue
    s=s.replace(anchor,anchor+f'      <p class="cluster-link" style="margin-top:8px;"><a href="{pre}{slug}/" {S}>{txt}</a></p>\n',1)
    open(f,"w").write(s)
