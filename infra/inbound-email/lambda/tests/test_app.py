import os
import unittest

from app import extract_sender_and_text

FIXTURE = os.path.join(os.path.dirname(__file__), 'sample-reply.eml')


class ExtractTests(unittest.TestCase):
    def test_extracts_sender_and_strips_quotes_and_signature(self):
        with open(FIXTURE, 'rb') as handle:
            raw = handle.read()

        sender, text = extract_sender_and_text(raw)

        self.assertEqual(sender, 'writer@example.com')
        self.assertIn('I learned how SES inbound works.', text)
        # quoted history removed
        self.assertNotIn('wrote:', text)
        self.assertNotIn('What did you learn today?', text)
        # signature removed
        self.assertNotIn('Sent from a journaling app', text)

    def test_handles_html_only_reply(self):
        raw = (
            b'From: Jane Writer <writer@example.com>\r\n'
            b'To: The Daily Inquirer <the@dailyinquirer.me>\r\n'
            b'Subject: Re: What did you learn today?\r\n'
            b'Content-Type: text/html; charset="UTF-8"\r\n'
            b'\r\n'
            b'<div dir="ltr">I learned how SES inbound works.</div>\r\n'
            b'<blockquote class="gmail_quote">'
            b'<div>On Sun, May 17, 2026 The Daily Inquirer wrote:</div>'
            b'<div>What did you learn today?</div>'
            b'</blockquote>\r\n'
        )

        sender, text = extract_sender_and_text(raw)

        self.assertEqual(sender, 'writer@example.com')
        self.assertIn('I learned how SES inbound works.', text)
        self.assertNotIn('What did you learn today?', text)
