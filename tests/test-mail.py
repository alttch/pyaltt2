#!/usr/bin/env python3

from pathlib import Path
import sys

sys.path.insert(0, Path().absolute().parent.as_posix())

from pyaltt2.mail import SMTP
from email.mime.text import MIMEText

smtp = SMTP(host='10.90.1.8', port=25)
sender = 'bot@lab.altt.ch'
rcpt = 'div@altertech.com'

# letter = MIMEText('this is a test')
# letter['Subject'] = 'test'
# letter['From'] = sender
# letter['To'] = rcpt

# smtp.send(sender, rcpt, letter.as_string())

text = "this is a test message\nhow do you do?"
html = """
<html><body><b>this is a test message</b><br />how do you do?</body></html>
"""

smtp.sendmail(sender, rcpt, subject='test', text=text, html=html)
