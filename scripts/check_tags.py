# Usage: python3 scripts/check_tags.py <html files...>  (HTML tag-balance check)
import sys
from html.parser import HTMLParser
V={'meta','link','br','img','input','hr','source','wbr'}
for f in sys.argv[1:]:
    st=[];bad=[]
    class P(HTMLParser):
        def handle_starttag(s,t,a):
            if t not in V: st.append(t)
        def handle_endtag(s,t):
            if t in V: return
            if st and st[-1]==t: st.pop()
            else: bad.append(t)
    P().feed(open(f).read()); print(f, "OK" if not bad and not st else (bad,st))
