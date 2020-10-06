from pyaltt2.network import parse_host_port
import smtplib


class SMTP:
    """
    SMTP sender
    """

    def __init__(self,
                 host='localhost',
                 port=25,
                 tls=False,
                 ssl=False,
                 login=None,
                 password=None,
                 debug=False):
        """
        Args:
            host: SMTP host
            port: SMTP port
            tls: use TLS (default: False)
            ssl: use SSL (default: False)
            login: SMTP login
            password: SMTP password
        """
        self.host = host
        self.port = port
        self.tls = tls
        self.ssl = ssl
        self.login = login
        self.password = password
        self.sendfunc = smtplib.SMTP_SSL if ssl else smtplib.SMTP
        self.debug = debug

    def send(self, sender, rcpt, body):
        """
        Send raw email

        Args:
            sender: E-Mail sender
            rcpt: E-Mail recipient
            body: E-Mail body (string)
        """
        sm = self.sendfunc(self.host, self.port)
        if self.debug:
            sm.set_debuglevel(9)
        sm.ehlo()
        if self.tls:
            sm.starttls()
        if self.login is not None:
            sm.login(self.login, self.password)
        sm.sendmail(sender, rcpt, body)
        sm.close()

    def sendmail(self, sender, rcpt, subject='', text='', html=None):
        """
        Send text/html email

        Args:
            sender: E-Mail sender
            rcpt: E-Mail recipient
            subject: E-Mail subject
            text: message text in plain
            html: message text in HTML
        """
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        if html:
            m = MIMEMultipart('alternative')
            part_text = MIMEText(text, 'plain')
            part_html = MIMEText(html, 'html')
            m.attach(part_text)
            m.attach(part_html)
        else:
            m = MIMEText(text)
        m['Subject'] = subject
        m['From'] = sender
        m['To'] = rcpt[0] if isinstance(rcpt, list) and len(rcpt) > 1 else rcpt
        self.send(sender, rcpt, m.as_string())
