# Inbound Email (reply-to-prompt) via AWS SES

**Date:** 2026-05-17
**Status:** Approved design

## Goal

Restore the reply-to-prompt feature: when a subscriber replies to the daily
writing-prompt email, the server turns the reply into a journal `Entry`.

The daily email is sent `From: The Daily Inquirer <the@dailyinquirer.me>`, so
replies arrive at `the@dailyinquirer.me`. The handler still exists
(`POST /messages/` → `on_incoming_message` in `core/views.py`) and expects
`sender` + `stripped-text`. It was originally fed by a Mailgun inbound Route;
the app has since migrated to AWS SES for outbound mail, and inbound was never
re-implemented. This design re-implements inbound on SES.

## Decisions

| Topic | Decision |
|-------|----------|
| Provisioning | AWS SAM template committed to the repo (`infra/inbound-email/`) |
| Reply parsing | `talon` (Mailgun's library) — reproduces the original `stripped-text` |
| Lambda packaging | Container-image Lambda (talon + lxml/scikit-learn exceed the zip limit) |
| SES action pattern | S3 action + Lambda action in one receipt rule |
| Region | `us-east-1` (SES domain identity already verified there) |
| Endpoint security | Shared-secret header check on `/messages/` |

## Key facts

- AWS account `954015041804`; AWS CLI profile `dest`; SES region `us-east-1`.
- `dailyinquirer.me` is a verified SES domain identity (DKIM verified).
- Route 53 hosted zone for the domain: `Z0253142WNQ4MF525XQJ`.
- App deployed on Fly.io as `dailyinquirer`, live at https://dailyinquirer.me.
- The SES sandbox affects sending only, not receiving — inbound can be set up now.

## Architecture & data flow

```
User replies to daily email
   ↓ (MX record)
SES inbound-smtp.us-east-1
   → receipt rule "deliver-the" (recipient the@dailyinquirer.me, scan enabled)
       ├─ action 1: S3 action     → writes raw MIME to s3://…/inbound/<messageId>
       └─ action 2: Lambda action → invokes inbound-email Lambda
            ↓
   Lambda (container image, Python 3.12 + talon)
   • drop if spamVerdict/virusVerdict == FAIL
   • GET the S3 object, parse MIME (stdlib email)
   • extract sender from the From: header, body from text/plain (or html)
   • talon: strip quoted history + signature  → stripped-text
   • POST https://dailyinquirer.me/messages/  {sender, stripped-text}
       header  X-Inbound-Secret: <shared secret>
            ↓
   Django on_incoming_message
   • verify X-Inbound-Secret (hmac.compare_digest) → 403 if bad/missing
   • look up User by sender, today's Prompt → create Entry
```

## Components

### 1. DNS — MX record

`AWS::Route53::RecordSet` in the SAM template, in zone `Z0253142WNQ4MF525XQJ`:

```
dailyinquirer.me  MX  10 inbound-smtp.us-east-1.amazonaws.com
```

Adding an MX record does not conflict with the existing Fly A/AAAA records or
the SES DKIM CNAMEs in the zone.

### 2. S3 bucket

Bucket `dailyinquirer-inbound-email`:

- Stores raw inbound MIME under the `inbound/` prefix.
- Lifecycle rule: expire objects after 30 days.
- Bucket policy grants `Service: ses.amazonaws.com` `s3:PutObject`, scoped with
  an `aws:SourceAccount` = `954015041804` condition.
- Public access fully blocked.

### 3. SES receipt rule set + rule

- Receipt rule set `dailyinquirer-inbound`.
- Rule `deliver-the`: recipient condition `the@dailyinquirer.me`,
  `ScanEnabled: true`, actions `[S3 action, Lambda action]` in that order.
- The S3 action writes to the bucket with object-key prefix `inbound/`.
- The Lambda action invokes the Lambda; its event carries `mail.messageId`
  (the S3 object key, minus prefix) and `receipt` with the scan verdicts.

**Activation:** CloudFormation cannot mark a receipt rule set *active* — the
active rule set is account-global state. Activation is a one-time, idempotent
post-deploy step, documented in the implementation plan:

```
aws --profile dest --region us-east-1 ses set-active-receipt-rule-set \
    --rule-set-name dailyinquirer-inbound
```

Before creating the rule set, check whether an active rule set already exists
(`aws ses describe-active-receipt-rule-set`); if one does, add the
`deliver-the` rule to it instead of creating and activating a new set.

### 4. Lambda — `dailyinquirer-inbound-email`

Container-image Lambda, Python 3.12 base, 1024 MB memory, 30 s timeout.

Behavior:

1. Receive the SES Lambda-action event; read `messageId` and the
   `spamVerdict` / `virusVerdict` from `receipt`.
2. If either verdict is `FAIL`, log and return without creating an entry.
3. `GET` the raw message from `s3://dailyinquirer-inbound-email/inbound/<messageId>`.
4. Parse the MIME with the stdlib `email` package.
5. Extract the sender address from the `From:` header (address portion only).
6. Extract the body: prefer the `text/plain` part; fall back to `text/html`.
7. Strip quoted history and signature with talon
   (`talon.quotations.extract_from` for plain or html, then
   `talon.signature.extract` after `talon.init()`).
8. `POST` JSON `{"sender": …, "stripped-text": …}` to
   `https://dailyinquirer.me/messages/` with header
   `X-Inbound-Secret: <shared secret>`. Uses stdlib `urllib.request` — no
   `requests` dependency.
9. Log the response status. Non-2xx and exceptions are logged to CloudWatch;
   SES async-invoke retries twice. No DLQ in v1.

`talon.init()` (loads the bundled ML signature models) runs once at module
import / cold start.

### 5. IAM

- Lambda execution role: `s3:GetObject` on
  `arn:aws:s3:::dailyinquirer-inbound-email/inbound/*`, plus the standard
  CloudWatch Logs permissions.
- `AWS::Lambda::Permission` allowing `Principal: ses.amazonaws.com` to invoke
  the Lambda, with `SourceAccount` = `954015041804`.

### 6. Django changes

`core/views.py` — `on_incoming_message`:

- **First step:** read the `X-Inbound-Secret` request header and compare it to
  `settings.INBOUND_SHARED_SECRET` using `hmac.compare_digest`. Missing,
  empty, or mismatched → return `HttpResponseForbidden` (`403`). If
  `INBOUND_SHARED_SECRET` is unset, treat all requests as unauthorized.
- Replace the always-`OK` response with meaningful status codes:
  - `201` — entry created.
  - `200` — request understood but no entry created (unknown sender, no prompt
    for today, or an entry already exists), with a short reason in the body.
  - `400` — missing/invalid `sender` or `stripped-text`.
  - `403` — bad/missing secret.
- Keep `@csrf_exempt` (the caller is the Lambda, not a browser).

`dailyinquirer/settings/base.py`:

- `INBOUND_SHARED_SECRET = os.environ.get('INBOUND_SHARED_SECRET')`.

Tests (`core/tests.py`) — written test-first; the endpoint currently has none:

- POST without the secret header → `403`, no `Entry` created.
- POST with a wrong secret → `403`, no `Entry` created.
- POST with the correct secret, known sender, prompt for today → `201`, one
  `Entry` created with the posted text.
- POST with the correct secret but unknown sender → `200`, no `Entry`.
- POST with the correct secret, known sender, prompt exists, entry already
  exists → `200`, no second `Entry`.

### 7. Repository layout

```
infra/inbound-email/
  template.yaml          # SAM/CloudFormation: bucket, rule set + rule, Lambda,
                         # IAM, Lambda permission, MX RecordSet
  lambda/
    Dockerfile           # python:3.12 Lambda base image + talon
    app.py               # handler described in component 4
    requirements.txt     # talon
    tests/
      test_app.py        # local unit test of parse + strip (no AWS)
      sample-reply.eml   # fixture: a Gmail reply to a daily prompt
```

The SAM template parameters: `SharedSecret` (`NoEcho: true`), `HostedZoneId`
(default `Z0253142WNQ4MF525XQJ`).

## Secret management

Generate a 32-byte URL-safe token. Set it in two places with the same value:

- Fly secret: `flyctl secrets set INBOUND_SHARED_SECRET=<token>`.
- SAM parameter `SharedSecret` (`NoEcho: true`) → Lambda environment variable.

A future hardening could move the Lambda's copy to Secrets Manager; out of
scope for v1.

## Error handling

| Situation | Behavior |
|-----------|----------|
| spam/virus verdict `FAIL` | Lambda logs and drops; no entry, no retry |
| Unknown sender / no prompt today / entry already exists | Django `200` + reason; Lambda logs |
| Missing/bad `X-Inbound-Secret` | Django `403`; Lambda logs an error |
| Missing `sender` / `stripped-text` | Django `400`; Lambda logs an error |
| Lambda exception | CloudWatch Logs; SES async-invoke retries twice |

## Testing end-to-end

After deploying the SAM stack and the Django changes:

1. Ensure a `Prompt` exists with `mail_day` = today, and that the sending
   email address belongs to a confirmed `User`.
2. Send a reply (or a plain email) to `the@dailyinquirer.me` from that address.
3. Confirm in CloudWatch Logs that the Lambda parsed the message and POSTed,
   and on Fly (`Entry.objects.filter(...)`) that an `Entry` was created with
   the expected text.

## Alternatives considered

- **SNS receipt action** instead of S3 + Lambda — rejected: SNS caps the
  message at 150 KB, which fails on emails with attachments.
- **S3-only action + S3 `ObjectCreated` trigger** — viable, but the SES Lambda
  action hands us structured spam/virus verdicts directly without re-parsing
  SES headers; the S3 + Lambda pattern is cleaner.
- **Plain-zip Lambda** — rejected: talon's dependency tree (lxml,
  scikit-learn, numpy) exceeds the 250 MB unzipped limit; container image is
  required.

## Out of scope

- Bounce / complaint handling for `the@` or `beep-boop@`.
- Catch-all receiving for other addresses at the domain.
- A dead-letter queue for the Lambda.
- Migrating the Lambda's secret copy to Secrets Manager.
- Changing the `dev.py` settings (still Mailgun) — inbound is prod-only.
