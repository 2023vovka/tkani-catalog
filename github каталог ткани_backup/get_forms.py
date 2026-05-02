import urllib.request
from bs4 import BeautifulSoup
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://www.litena.lt/en/', headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req, context=ctx).read().decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    for form in soup.find_all('form'):
        print(f"Action: {form.get('action')}, Inputs: {[i.get('name') for i in form.find_all('input')]}")
except Exception as e:
    print(e)
