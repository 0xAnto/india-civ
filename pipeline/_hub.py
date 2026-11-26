import re,json
def load(path):
    h=open(path).read()
    for m in re.finditer(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>',h,re.S):
        s=m.group(1)
        if 'reportTitle' in s:
            s=json.loads('"'+s+'"')
            i=s.find('{"reportTitle"') if '{"reportTitle"' in s else s.find('"reportTitle"')-1
            i=s.rfind('{"',0,s.find('"reportTitle"')+1) if s[s.find('"reportTitle"')-1]!='{' else s.find('"reportTitle"')-1
            d,_=json.JSONDecoder().raw_decode(s[i:])
            return d
