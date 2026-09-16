# Nginx Incident Investigation

## Purpose

Investigate Nginx incidents on the EC2 server and determine the likely root cause of HTTP errors, service failures, or abnormal traffic.

This skill defines the approved investigation procedure and the log files that may be inspected.

---

## Log Access Policy

### ONLY inspect these log files

```text
/var/log/nginx/access.log
/var/log/nginx/error.log
```

### DO NOT inspect these files

```text
/var/log/nginx/*.log.1
/var/log/nginx/*.gz
/var/log/syslog
/var/log/auth.log
```

Do not expand the investigation to other log files unless explicitly instructed by the user.

---

## Investigation Procedure

### Step 1 — Check Nginx service status

Run:

```bash
sudo systemctl status nginx --no-pager
```

Determine whether Nginx is:

* running
* stopped
* failed
* restarting

Do not restart Nginx yet.

---

### Step 2 — Validate Nginx configuration

Run:

```bash
sudo nginx -t
```

Check for:

* syntax errors
* invalid directives
* missing configuration files
* invalid upstream configuration
* permission-related errors

Record the exact error if the configuration test fails.

---

### Step 3 — Check whether Nginx is listening

Run:

```bash
sudo ss -lntp | grep ':80'
```

Also check HTTPS if relevant:

```bash
sudo ss -lntp | grep ':443'
```

Determine whether Nginx is actually listening on the expected port.

---

### Step 4 — Inspect Nginx error log

ONLY read:

```text
/var/log/nginx/error.log
```

Use:

```bash
sudo tail -100 /var/log/nginx/error.log
```

Look specifically for:

* `connect() failed`
* `connection refused`
* `upstream timed out`
* `no live upstreams`
* `502 Bad Gateway`
* `503 Service Unavailable`
* `504 Gateway Timeout`
* permission errors
* configuration errors
* worker/process failures

Correlate error timestamps with the reported incident time.

---

### Step 5 — Inspect Nginx access log

ONLY read:

```text
/var/log/nginx/access.log
```

Use:

```bash
sudo tail -100 /var/log/nginx/access.log
```

Look for:

* HTTP 400
* HTTP 401
* HTTP 403
* HTTP 404
* HTTP 499
* HTTP 500
* HTTP 502
* HTTP 503
* HTTP 504

Identify:

* affected endpoint
* request method
* response status
* frequency of failures
* approximate incident start time

---

## HTTP Status Investigation

Use the following interpretation as an initial guide.

### 4xx

Investigate possible client/request problems.

Examples:

```text
400 → Bad Request
401 → Unauthorized
403 → Forbidden
404 → Not Found
```

Do not automatically classify every 4xx response as an Nginx failure.

---

### 5xx

Investigate possible server or upstream problems.

Examples:

```text
500 → Internal Server Error
502 → Bad Gateway
503 → Service Unavailable
504 → Gateway Timeout
```

For 502/503/504 responses, pay particular attention to the Nginx error log.

---

## Upstream Investigation

If the error log contains messages such as:

```text
connect() failed
connection refused
upstream timed out
no live upstreams
```

determine whether Nginx is unable to communicate with its upstream application.

Check the Nginx configuration to identify the configured upstream.

Do not modify the configuration during investigation.

---

## Incident Correlation

Correlate evidence from:

```text
access.log
     +
error.log
     +
Nginx service status
     +
Nginx configuration test
     +
listening ports
```

Build a timeline where possible.

Example:

```text
10:31:02  First HTTP 502
10:31:03  Upstream connection refused
10:31:05  Multiple checkout requests fail
10:31:10  Nginx remains running
```

Use timestamps and log evidence rather than assumptions.

---

## Root Cause Classification

Classify the incident where possible as one of:

```text
NGINX_SERVICE_FAILURE
NGINX_CONFIGURATION_ERROR
UPSTREAM_UNAVAILABLE
UPSTREAM_TIMEOUT
HTTP_CLIENT_ERROR
HTTP_SERVER_ERROR
ABNORMAL_TRAFFIC
UNKNOWN
```

If evidence is insufficient, report:

```text
Root cause could not be conclusively determined.
```

Do not invent a root cause.

---

## Safety Rules

During investigation:

### DO NOT

```text
restart nginx
stop nginx
kill processes
delete logs
truncate logs
modify nginx configuration
modify application files
modify firewall rules
modify security groups
```

unless explicitly instructed by the user.

The investigation phase must be read-only.

---

## Remediation

After identifying the likely root cause:

1. Explain the evidence.
2. Explain the proposed remediation.
3. Identify the commands that would be executed.
4. Ask for approval before performing a potentially disruptive action.

Example:

```text
Finding:
Nginx is running, but the configured upstream is refusing
connections.

Proposed remediation:
Verify that the upstream application service is running.

Potential command:
sudo systemctl status ecommerce
```

Do not execute disruptive remediation automatically.

---

## Required Investigation Output

Return the final investigation in this format:

```text
NGINX INCIDENT REPORT

Incident:
<short description>

Nginx Status:
<running/stopped/failed>

Configuration:
<valid/invalid>

Listening Ports:
<details>

HTTP Errors:
<status codes and frequency>

Affected Endpoints:
<endpoints>

Error Log Evidence:
<important findings>

Access Log Evidence:
<important findings>

Timeline:
<important timestamps>

Root Cause:
<most likely cause>

Confidence:
<high/medium/low>

Impact:
<observed impact>

Recommended Remediation:
<recommended action>

Commands Executed:
<commands actually executed>

Files Inspected:
ONLY:
- /var/log/nginx/access.log
- /var/log/nginx/error.log
```

---

## Strict Log Boundary

The following rule has highest priority for log inspection:

```text
ONLY inspect:
/var/log/nginx/access.log
/var/log/nginx/error.log

NEVER inspect:
/var/log/nginx/*.log.1
/var/log/nginx/*.gz
/var/log/syslog
/var/log/auth.log
```

If information required to determine the root cause is unavailable from the allowed sources, explicitly state that additional information is required rather than reading a prohibited file.
