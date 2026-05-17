"""AWS Lambda: turn an inbound reply email into a POST to /messages/.

Triggered by an SES receipt-rule Lambda action. The raw MIME message has
already been stored to S3 by an S3 action on the same rule.
"""
import email
import json
import logging
import os
import urllib.error
import urllib.request
from email.utils import parseaddr

import html2text
from email_reply_parser import EmailReplyParser

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Must match the SES receipt rule's S3 action ObjectKeyPrefix in template.yaml.
S3_KEY_PREFIX = 'inbound/'


def _decode_part(part):
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    charset = part.get_content_charset() or 'utf-8'
    return payload.decode(charset, errors='replace')


def _get_body(msg, content_type):
    """Return the first non-attachment part of content_type, decoded to str."""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() != content_type:
            continue
        disposition = str(part.get('Content-Disposition', '')).lower()
        if 'attachment' in disposition:
            continue
        text = _decode_part(part)
        if text is not None:
            return text
    return None


def _html_to_text(html):
    """Render HTML to text, with quoted blocks as '>'-prefixed lines."""
    converter = html2text.HTML2Text()
    converter.body_width = 0  # don't hard-wrap lines
    return converter.handle(html)


def extract_sender_and_text(raw_bytes):
    """Parse raw MIME; return (sender_email, stripped_reply_text).

    Quoted history and signature are removed with email-reply-parser.
    """
    msg = email.message_from_bytes(raw_bytes)
    sender = parseaddr(msg.get('From', ''))[1].lower()

    plain = _get_body(msg, 'text/plain')
    if not plain or not plain.strip():
        html = _get_body(msg, 'text/html')
        if html:
            plain = _html_to_text(html)

    if not plain:
        return sender, ''
    reply = EmailReplyParser.parse_reply(plain)
    return sender, reply.strip()


def handler(event, context):
    import boto3

    record = event['Records'][0]['ses']
    message_id = record['mail']['messageId']
    receipt = record['receipt']

    if (receipt.get('spamVerdict', {}).get('status') == 'FAIL' or
            receipt.get('virusVerdict', {}).get('status') == 'FAIL'):
        logger.warning('Dropping %s: failed spam/virus scan', message_id)
        return {'status': 'dropped'}

    bucket = os.environ['INBOUND_BUCKET']
    endpoint = os.environ['MESSAGES_ENDPOINT']
    secret = os.environ['SHARED_SECRET']

    key = S3_KEY_PREFIX + message_id
    raw = boto3.client('s3').get_object(Bucket=bucket, Key=key)['Body'].read()

    sender, text = extract_sender_and_text(raw)
    if not sender or not text:
        logger.warning('Message %s skipped: sender=%r text_len=%d',
                        message_id, sender, len(text))
        return {'status': 'skipped'}

    body = json.dumps({'sender': sender, 'stripped-text': text}).encode('utf-8')
    request = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={'Content-Type': 'application/json',
                 'X-Inbound-Secret': secret})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            logger.info('POST %s -> %s', endpoint, response.status)
            return {'status': 'posted', 'code': response.status}
    except urllib.error.HTTPError as exc:
        logger.error('POST %s failed: HTTP %s', endpoint, exc.code)
        raise
    except urllib.error.URLError as exc:
        logger.error('POST %s failed: %s', endpoint, exc.reason)
        raise
