# Inbound Email (reply-to-prompt) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the reply-to-prompt feature — a subscriber's reply to the daily email becomes a journal `Entry` — using AWS SES for inbound mail.

**Architecture:** SES receives mail at `the@dailyinquirer.me` via an MX record; a receipt rule stores the raw MIME to S3 and invokes a plain-zip Lambda. The Lambda parses the message, strips quoted history/signature with email-reply-parser, and POSTs `sender` + `stripped-text` to the existing `POST /messages/` endpoint, which is hardened with a shared-secret header check.

**Tech Stack:** Django 5.2, AWS SES receiving, S3, Lambda (plain zip, Python 3.12), AWS SAM, email-reply-parser, html2text, Route 53, Fly.io.

**Design doc:** `docs/superpowers/specs/2026-05-17-inbound-email-design.md`

**Key facts:** AWS account `954015041804`, CLI profile `dest`, region `us-east-1`. Route 53 zone `Z0253142WNQ4MF525XQJ`. Fly app `dailyinquirer`. The Django test settings module is `dailyinquirer.settings.local` (the `manage.py` default).

---

## Task 1: Secure `POST /messages/` with a shared secret

Adds a `X-Inbound-Secret` header check to `on_incoming_message` and replaces its always-`OK` response with meaningful status codes. The endpoint currently has no tests; this task adds them first.

**Files:**
- Modify: `dailyinquirer/settings/base.py`
- Modify: `core/views.py`
- Modify: `core/tests.py`

- [ ] **Step 1: Add the setting**

In `dailyinquirer/settings/base.py`, add after the `DEFAULT_FROM_EMAIL` line:

```python
# Shared secret the inbound-email Lambda must present in the
# X-Inbound-Secret header on POST /messages/. Unset locally.
INBOUND_SHARED_SECRET = os.environ.get('INBOUND_SHARED_SECRET')
```

- [ ] **Step 2: Write the failing tests**

In `core/tests.py`, change the first import line from:

```python
from django.test import TestCase
```

to:

```python
import json

from django.test import TestCase, override_settings
from django.utils import timezone
```

and add to the existing import block:

```python
from core.models import Entry, Prompt
```

Then append this class to the end of the file:

```python
@override_settings(INBOUND_SHARED_SECRET='test-secret')
class IncomingMessageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='writer@example.com', password='mostdope1')
        self.user.timezone = 'UTC'
        self.user.confirmed_email = True
        self.user.save()
        self.prompt = Prompt.objects.create(
            question='What did you learn today?',
            mail_day=timezone.now())
        self.url = reverse('messages')

    def post(self, payload, secret='test-secret'):
        headers = {}
        if secret is not None:
            headers['HTTP_X_INBOUND_SECRET'] = secret
        return self.client.post(
            self.url, data=json.dumps(payload),
            content_type='application/json', **headers)

    def test_rejects_missing_secret(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'hi'},
            secret=None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Entry.objects.count(), 0)

    def test_rejects_wrong_secret(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'hi'},
            secret='wrong-secret')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Entry.objects.count(), 0)

    def test_creates_entry_for_known_sender(self):
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'My entry.'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Entry.objects.count(), 1)
        entry = Entry.objects.get()
        self.assertEqual(entry.content, 'My entry.')
        self.assertEqual(entry.author, self.user)
        self.assertEqual(entry.prompt, self.prompt)

    def test_unknown_sender_creates_no_entry(self):
        response = self.post(
            {'sender': 'stranger@example.com', 'stripped-text': 'hi'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Entry.objects.count(), 0)

    def test_missing_fields_returns_400(self):
        response = self.post({'sender': 'writer@example.com'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Entry.objects.count(), 0)

    def test_duplicate_entry_not_created_twice(self):
        Entry.objects.create(
            content='first', author=self.user,
            prompt=self.prompt, pub_date=timezone.now())
        response = self.post(
            {'sender': 'writer@example.com', 'stripped-text': 'second'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Entry.objects.count(), 1)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python manage.py test core.tests.IncomingMessageTests -v 2`
Expected: FAIL — the current endpoint always returns `200`, so `test_rejects_missing_secret`, `test_rejects_wrong_secret`, `test_creates_entry_for_known_sender`, and `test_missing_fields_returns_400` fail on the status-code assertions.

- [ ] **Step 4: Rewrite the view**

In `core/views.py`, change the import line:

```python
from django.http import HttpResponse
```

to:

```python
from django.http import (HttpResponse, HttpResponseBadRequest,
                          HttpResponseForbidden, HttpResponseNotAllowed)
from django.conf import settings as django_settings
import hmac
```

This replaces the single `from django.http import HttpResponse` line with three lines. `json`, `pytz`, and `timezone` are already imported in `core/views.py`, so no other import changes are needed.

Then replace the entire `on_incoming_message` function with:

```python
@csrf_exempt
def on_incoming_message(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    expected = django_settings.INBOUND_SHARED_SECRET or ''
    provided = request.headers.get('X-Inbound-Secret', '')
    if not expected or not hmac.compare_digest(provided, expected):
        return HttpResponseForbidden('invalid secret')

    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        data = request.POST

    sender = data.get('sender')
    stripped_text = data.get('stripped-text')
    if not sender or not stripped_text:
        return HttpResponseBadRequest('missing sender or stripped-text')

    try:
        user = User.objects.get(email=sender)
    except User.DoesNotExist:
        return HttpResponse('ignored: unknown sender', status=200)

    local_time = user.local_time()
    if local_time is None:
        return HttpResponse('ignored: user has no valid timezone', status=200)

    todays_prompt = Prompt.objects.filter(
        mail_day__day=local_time.day,
        mail_day__month=local_time.month,
        mail_day__year=local_time.year,
    ).first()
    if todays_prompt is None:
        return HttpResponse('ignored: no prompt for today', status=200)

    already_exists = Entry.objects.filter(
        pub_date__day=local_time.day,
        pub_date__month=local_time.month,
        pub_date__year=local_time.year,
        author=user,
    ).exists()
    if already_exists:
        return HttpResponse('ignored: entry already exists', status=200)

    Entry.objects.create(
        content=stripped_text,
        author=user,
        prompt=todays_prompt,
        pub_date=timezone.now(),
    )
    return HttpResponse('created', status=201)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python manage.py test core.tests -v 2`
Expected: PASS — all `IncomingMessageTests` plus the existing `EmailConfirmationTests`.

- [ ] **Step 6: Commit**

```bash
git add dailyinquirer/settings/base.py core/views.py core/tests.py
git commit -m "$(cat <<'EOF'
Require a shared-secret header on the inbound message endpoint

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Inbound-email Lambda handler

Builds the Lambda that parses raw MIME and POSTs to `/messages/`. The parse-and-strip logic (`extract_sender_and_text`) is pure and unit-tested locally; the `handler` wires in S3 and the HTTP POST.

**Files:**
- Create: `infra/inbound-email/lambda/requirements.txt`
- Create: `infra/inbound-email/lambda/app.py`
- Create: `infra/inbound-email/lambda/tests/__init__.py`
- Create: `infra/inbound-email/lambda/tests/test_app.py`
- Create: `infra/inbound-email/lambda/tests/sample-reply.eml`

- [ ] **Step 1: Create the requirements file**

`infra/inbound-email/lambda/requirements.txt`:

```
email-reply-parser
html2text
```

(`boto3` is preinstalled in the Lambda runtime and is imported lazily inside `handler`, so it is not listed — this keeps the local test venv small.)

- [ ] **Step 2: Create the test fixture**

`infra/inbound-email/lambda/tests/sample-reply.eml` — a Gmail-style reply to a daily prompt:

```
From: Jane Writer <writer@example.com>
To: The Daily Inquirer <the@dailyinquirer.me>
Subject: Re: What did you learn today?
Date: Sun, 17 May 2026 12:00:00 -0400
Content-Type: text/plain; charset="UTF-8"

I learned how SES inbound works.

On Sun, May 17, 2026 at 9:00 AM The Daily Inquirer <the@dailyinquirer.me> wrote:

> What did you learn today?
```

- [ ] **Step 3: Create the test package marker**

`infra/inbound-email/lambda/tests/__init__.py` — empty file.

- [ ] **Step 4: Write the failing test**

`infra/inbound-email/lambda/tests/test_app.py`:

```python
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
```

- [ ] **Step 5: Create a venv, install dependencies, run the test to verify it fails**

```bash
cd infra/inbound-email/lambda
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app'` (`app.py` does not exist yet).

- [ ] **Step 6: Write the handler**

`infra/inbound-email/lambda/app.py`:

```python
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
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
cd infra/inbound-email/lambda
.venv/bin/python -m unittest discover -s tests -t . -v
```

Expected: PASS — `test_extracts_sender_and_strips_quotes_and_signature` and `test_handles_html_only_reply`.

- [ ] **Step 8: Commit**

```bash
git add infra/inbound-email/lambda
git commit -m "$(cat <<'EOF'
Add inbound-email Lambda handler that parses replies and posts entries

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: SAM template for the inbound pipeline

Defines all AWS resources: S3 bucket, SES receipt rule set + rule, the Lambda, IAM, and the Route 53 MX record.

**Files:**
- Create: `infra/inbound-email/template.yaml`
- Modify: `.gitignore`

- [ ] **Step 1: Write the template**

`infra/inbound-email/template.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Inbound email (reply-to-prompt) processing for dailyinquirer.me

Parameters:
  SharedSecret:
    Type: String
    NoEcho: true
    Description: Secret sent in X-Inbound-Secret; must match Fly INBOUND_SHARED_SECRET.
  HostedZoneId:
    Type: String
    Default: Z0253142WNQ4MF525XQJ
    Description: Route 53 hosted zone for dailyinquirer.me.
  RuleSetName:
    Type: String
    Default: dailyinquirer-inbound
    Description: Name of the SES receipt rule set.

Resources:

  InboundBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: dailyinquirer-inbound-email
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      LifecycleConfiguration:
        Rules:
          - Id: expire-inbound
            Status: Enabled
            Prefix: inbound/
            ExpirationInDays: 30

  InboundBucketPolicy:
    Type: AWS::S3::BucketPolicy
    Properties:
      Bucket: !Ref InboundBucket
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Sid: AllowSESPut
            Effect: Allow
            Principal:
              Service: ses.amazonaws.com
            Action: s3:PutObject
            Resource: !Sub '${InboundBucket.Arn}/inbound/*'
            Condition:
              StringEquals:
                aws:SourceAccount: !Ref AWS::AccountId

  InboundFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: dailyinquirer-inbound-email
      Runtime: python3.12
      Handler: app.handler
      CodeUri: ./lambda
      Architectures: [arm64]
      MemorySize: 256
      Timeout: 30
      Environment:
        Variables:
          INBOUND_BUCKET: !Ref InboundBucket
          MESSAGES_ENDPOINT: https://dailyinquirer.me/messages/
          SHARED_SECRET: !Ref SharedSecret
      Policies:
        - Statement:
            - Effect: Allow
              Action: s3:GetObject
              Resource: !Sub '${InboundBucket.Arn}/inbound/*'

  InboundFunctionSesPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref InboundFunction
      Action: lambda:InvokeFunction
      Principal: ses.amazonaws.com
      SourceAccount: !Ref AWS::AccountId

  InboundRuleSet:
    Type: AWS::SES::ReceiptRuleSet
    Properties:
      RuleSetName: !Ref RuleSetName

  InboundRule:
    Type: AWS::SES::ReceiptRule
    DependsOn:
      - InboundBucketPolicy
      - InboundFunctionSesPermission
    Properties:
      RuleSetName: !Ref InboundRuleSet
      Rule:
        Name: deliver-the
        Enabled: true
        ScanEnabled: true
        TlsPolicy: Optional
        Recipients:
          - the@dailyinquirer.me
        Actions:
          - S3Action:
              BucketName: !Ref InboundBucket
              ObjectKeyPrefix: inbound/
          - LambdaAction:
              FunctionArn: !GetAtt InboundFunction.Arn
              InvocationType: Event

  InboundMxRecord:
    Type: AWS::Route53::RecordSet
    Properties:
      HostedZoneId: !Ref HostedZoneId
      Name: dailyinquirer.me.
      Type: MX
      TTL: '300'
      ResourceRecords:
        - 10 inbound-smtp.us-east-1.amazonaws.com.

Outputs:
  FunctionName:
    Value: !Ref InboundFunction
  BucketName:
    Value: !Ref InboundBucket
  RuleSetName:
    Value: !Ref InboundRuleSet
```

- [ ] **Step 2: Ignore the SAM build directory**

Append to `.gitignore`:

```
# AWS SAM build artifacts
infra/inbound-email/.aws-sam/
```

- [ ] **Step 3: Install the SAM CLI and validate the template**

```bash
brew install aws-sam-cli
cd infra/inbound-email
sam validate --lint --region us-east-1 --profile dest
```

Expected: `template.yaml is a valid SAM Template`.

- [ ] **Step 4: Commit**

```bash
git add infra/inbound-email/template.yaml .gitignore
git commit -m "$(cat <<'EOF'
Add SAM template for SES inbound email pipeline

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Generate the shared secret and deploy the Django change

Generates the shared secret, stores it as a Fly secret, and deploys the hardened endpoint to production.

**Files:** none (deployment task).

- [ ] **Step 1: Generate the shared secret**

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Record the output — it is used here and again in Task 5. Refer to it below as `<SECRET>`.

- [ ] **Step 2: Set the Fly secret**

```bash
flyctl secrets set INBOUND_SHARED_SECRET="<SECRET>" -a dailyinquirer
```

Expected: Fly reports the secret was set and the app is updated.

- [ ] **Step 3: Deploy the Django change**

From the repo root, with the Task 1 commit present in the working tree:

```bash
flyctl deploy -a dailyinquirer
```

Expected: build succeeds, release deploys, machine becomes healthy.

- [ ] **Step 4: Verify the endpoint rejects unauthenticated requests**

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://dailyinquirer.me/messages/
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  -H 'X-Inbound-Secret: wrong' https://dailyinquirer.me/messages/
```

Expected: `403` for both.

---

## Task 5: Deploy the SAM stack and activate the SES rule set

Builds and deploys the AWS resources, then makes the receipt rule set active.

**Files:** none (deployment task). Run all commands from `infra/inbound-email/`.

- [ ] **Step 1: Check for an existing active receipt rule set**

```bash
aws ses describe-active-receipt-rule-set --region us-east-1 --profile dest
```

Expected: an error or empty result meaning no rule set is active. If a rule set IS already active, do not create a competing one — instead add the `deliver-the` rule to that set and skip Step 4. Pause and use superpowers:systematic-debugging to decide.

- [ ] **Step 2: Build the Lambda zip**

```bash
cd infra/inbound-email
sam build --use-container
```

Expected: `Build Succeeded`. `--use-container` ensures the Python 3.12 zip builds correctly regardless of local Python version.

- [ ] **Step 3: Deploy the stack**

```bash
sam deploy \
  --stack-name dailyinquirer-inbound-email \
  --region us-east-1 --profile dest \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides SharedSecret="<SECRET>" \
  --no-confirm-changeset
```

Use the same `<SECRET>` value generated in Task 4 Step 1.
Expected: `Successfully created/updated stack`. The Outputs list `FunctionName`, `BucketName`, `RuleSetName`.

Note: if the MX `RecordSet` fails because one already exists, inspect the existing record (`aws route53 list-resource-record-sets --hosted-zone-id Z0253142WNQ4MF525XQJ --profile dest`); if it already points at `inbound-smtp.us-east-1.amazonaws.com`, remove the `InboundMxRecord` resource from the template and redeploy.

- [ ] **Step 4: Activate the receipt rule set**

```bash
aws ses set-active-receipt-rule-set \
  --rule-set-name dailyinquirer-inbound \
  --region us-east-1 --profile dest
```

Expected: no output (success). Confirm:

```bash
aws ses describe-active-receipt-rule-set --region us-east-1 --profile dest
```

Expected: the active rule set is `dailyinquirer-inbound` with rule `deliver-the`.

- [ ] **Step 5: Verify the MX record resolves**

```bash
dig +short MX dailyinquirer.me
```

Expected: `10 inbound-smtp.us-east-1.amazonaws.com.` (may take up to a minute).

---

## Task 6: End-to-end verification

Confirms a real reply produces an `Entry`. Production data is changed here — these are real writes.

**Files:** none (verification task).

- [ ] **Step 1: Ensure a prompt exists for today and the test sender is a confirmed user**

Pick the email address you will send the test from (e.g. `big.mack.with.pies@gmail.com`). On the production app:

```bash
flyctl ssh console -a dailyinquirer -C "python manage.py shell -c \"
from django.utils import timezone
from core.models import Prompt
from authentication.models import User
Prompt.objects.get_or_create(
    question='E2E inbound test prompt',
    defaults={'mail_day': timezone.now()})
u, created = User.objects.get_or_create(
    email='big.mack.with.pies@gmail.com',
    defaults={'timezone': 'US/Eastern'})
u.confirmed_email = True
if not u.timezone:
    u.timezone = 'US/Eastern'
u.save()
print('prompt + user ready; user created:', created)
\""
```

Expected: prints `prompt + user ready; ...`. If a prompt for today already exists, `get_or_create` leaves it untouched.

- [ ] **Step 2: Send a test email**

(Manual — you do this.) From the confirmed user's mailbox, send a plain email — or reply to today's daily prompt email — **to `the@dailyinquirer.me`**, with a recognizable body line such as `E2E test entry body`.

- [ ] **Step 3: Check the Lambda ran**

After ~1 minute:

```bash
aws logs tail /aws/lambda/dailyinquirer-inbound-email \
  --since 10m --region us-east-1 --profile dest
```

Expected: a log line `POST https://dailyinquirer.me/messages/ -> 201`.

- [ ] **Step 4: Confirm the entry was created**

```bash
flyctl ssh console -a dailyinquirer -C "python manage.py shell -c \"
from django.utils import timezone
from core.models import Entry
now = timezone.now()
for e in Entry.objects.filter(
        pub_date__year=now.year, pub_date__month=now.month,
        pub_date__day=now.day).order_by('-pub_date')[:5]:
    print(e.author.email, '|', repr(e.content[:80]))
\""
```

Expected: an entry for the test sender containing `E2E test entry body`.

- [ ] **Step 5 (fallback diagnostic, only if Step 3/4 fail): direct Lambda invoke**

If no log line appeared, the SES receive path may be the problem rather than the Lambda. Isolate the Lambda by invoking it against a manually uploaded message:

```bash
cd infra/inbound-email
# Upload the fixture under a known key (edit the From: line in the .eml
# first so it matches a confirmed user's address).
aws s3 cp lambda/tests/sample-reply.eml \
  s3://dailyinquirer-inbound-email/inbound/diag-test-id \
  --region us-east-1 --profile dest
printf '%s' '{"Records":[{"ses":{"mail":{"messageId":"diag-test-id"},"receipt":{"spamVerdict":{"status":"PASS"},"virusVerdict":{"status":"PASS"}}}}}' > /tmp/ses-event.json
aws lambda invoke --function-name dailyinquirer-inbound-email \
  --payload fileb:///tmp/ses-event.json \
  --region us-east-1 --profile dest /tmp/lambda-out.json
cat /tmp/lambda-out.json
```

Expected: `{"status": "posted", "code": 201}` (or `200` if an entry already exists). A `posted` result means the Lambda → Django path works and the problem is the SES receive configuration (MX, active rule set, or recipient match) — debug that with superpowers:systematic-debugging.

---

## Notes for the implementer

- Tasks 1–3 are local code changes with commits. Tasks 4–6 deploy to and verify against production AWS and Fly — there is no rollback step; treat them as real changes.
- The branch is `reply-email`. Opening a PR / merging to `master` is a separate step after Task 6 — see superpowers:finishing-a-development-branch.
- The shared secret must be identical in the Fly secret (Task 4) and the SAM `SharedSecret` parameter (Task 5).
