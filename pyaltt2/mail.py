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
                 password=None):
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

    def send(self, sender, rcpt, body):
        """
        Send email

        Args:
            sender: E-Mail sender
            rcpt: E-Mail recipient
            body: E-Mail body (string)
        """
        sm = self.sendfunc(self.host, self.port)
        sm.ehlo()
        if self.tls:
            sm.starttls()
        if self.login is not None:
            sm.login(self.login, self.password)
        sm.sendmail(sender, rcpt, body)
        sm.close()
