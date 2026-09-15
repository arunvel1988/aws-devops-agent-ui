---
name: ec2-high-cpu-investigation
description: Investigate high CPU utilization on Amazon EC2 instances, identify the root cause, and recommend safe remediation steps using AWS monitoring and available investigation tools.
---

# EC2 High CPU Investigation Skill

## Purpose

This skill provides a standardized procedure for investigating
high CPU utilization on Amazon EC2 instances.

Use this skill when:

- EC2 CPU utilization is abnormally high
- A CloudWatch CPU alarm is triggered
- A user reports that an EC2 server is slow
- An application running on EC2 is experiencing performance problems

---

## Investigation Objectives

The investigation must determine:

1. Which EC2 instance is affected
2. How high CPU utilization is
3. When the CPU problem started
4. Whether the problem is temporary or sustained
5. Which process is consuming CPU
6. Whether the process belongs to an application or system service
7. Whether a recent deployment or configuration change caused the problem
8. The most likely root cause
9. The recommended remediation
10. The risk associated with the remediation

---

## Investigation Procedure

### Step 1: Identify the EC2 Instance

Collect:

- Instance ID
- Instance name
- Instance type
- Availability Zone
- Instance state
- Instance health status

Do not assume the affected instance if multiple instances exist.

---

### Step 2: Investigate CloudWatch Metrics

Check the EC2 CPUUtilization metric.

Determine:

- Current CPU utilization
- Maximum CPU utilization
- Average CPU utilization
- Time when the CPU spike started
- Duration of the spike
- Whether the CPU usage is continuously high
- Whether the CPU usage is periodic

Use the available CloudWatch integration or tools.

---

### Step 3: Classify the Incident

Classify CPU utilization using the following guidance:

- Below 60%: normally not a CPU incident
- 60–80%: monitor and investigate if performance is affected
- 80–90%: investigate
- Above 90%: treat as high-priority investigation
- Above 95% for a sustained period: treat as critical performance degradation

These thresholds are guidelines and should not replace organization-specific monitoring policies.

---

### Step 4: Investigate Running Processes

If operating-system-level investigation is available, identify the processes consuming CPU.

Collect:

- Process name
- PID
- CPU percentage
- Memory percentage
- Parent process
- User running the process
- Command line, when available

Identify the top CPU-consuming processes.

If an MCP investigation tool is available, use it for
operating-system-level process investigation.

---

### Step 5: Determine the Process Type

Determine whether the process is:

- Application process
- Docker/container process
- System process
- Database process
- Web server
- Background job
- Monitoring process
- Unknown process

Do not assume that the process causing high CPU is malicious or faulty without evidence.

---

### Step 6: Investigate Recent Changes

Check for recent:

- Application deployments
- Configuration changes
- Package updates
- Infrastructure changes
- Scheduled jobs
- Traffic increases
- Container changes

If the CPU spike started immediately after a deployment,
investigate the deployment as a potential contributing factor.

---

### Step 7: Investigate Application Logs

If the CPU-consuming process belongs to an application:

Check available application logs for:

- Repeated errors
- Request spikes
- Infinite loops
- Failed retries
- Exception storms
- Long-running operations
- Unexpected background jobs

Correlate the log timestamps with the CPU spike.

---

## Root Cause Analysis

Determine the most likely root cause.

Possible classifications:

### Application Issue

The application is consuming excessive CPU because of
application behavior or code.

### Traffic Increase

CPU increased because request volume increased.

### Runaway Process

A process is consuming abnormal CPU resources.

### Deployment Issue

CPU increased after a new application version was deployed.

### Scheduled Job

A batch job or scheduled process caused the CPU spike.

### Container Issue

A container is consuming excessive CPU.

### Infrastructure Capacity

The EC2 instance may not have sufficient CPU capacity
for the workload.

### Security Concern

Unexpected processes or behavior may indicate suspicious activity.

Do not classify an incident as a security incident without evidence.

### Unknown

If sufficient evidence is not available, explicitly state:

"Root cause could not be conclusively determined."

Do not invent a root cause.

---

## Decision Rules

### Rule 1

If CPU is high and one process is consuming most of the CPU:

Investigate that process first.

### Rule 2

If CPU increased immediately after a deployment:

Investigate the deployment and application behavior.

### Rule 3

If CPU increased together with request volume:

Investigate traffic and application capacity.

### Rule 4

If CPU is high but no process clearly explains the usage:

Investigate system-level CPU behavior and continue gathering evidence.

### Rule 5

If an unknown process consumes significant CPU:

Flag it for further investigation.

Do not automatically terminate it.

---

## MCP Tool Usage

If an MCP server provides an investigation tool:

Use the investigation tool when operating-system-level
information is required.

For example:

1. Identify the affected EC2 instance.
2. Confirm the CPU spike using CloudWatch.
3. Use the MCP investigation tool.
4. Identify the top CPU-consuming process.
5. Compare process information with application evidence.
6. Use the combined evidence to determine the root cause.

Do not call tools unnecessarily.

---

## Remediation

Based on the investigation, recommend an appropriate action.

Possible recommendations include:

- Restart the affected application
- Restart a specific service
- Stop a runaway process
- Roll back a deployment
- Increase EC2 capacity
- Scale the workload
- Investigate application code
- Investigate unexpected traffic
- Investigate suspicious activity

The recommendation must be supported by evidence.

---

## Safety Rules

Do not automatically:

- Terminate an EC2 instance
- Delete an EC2 instance
- Kill a process
- Modify security groups
- Modify IAM permissions
- Delete application data
- Roll back a production deployment

Before any potentially disruptive remediation:

1. Explain the proposed action.
2. Explain why it is required.
3. Explain the expected impact.
4. Explain the risk.
5. Obtain explicit authorization before execution.

Investigation and remediation are separate phases.

---

## Expected Investigation Output

Return the investigation using this structure:

### Incident Summary

Briefly describe the problem.

### Affected Resource

- Instance ID:
- Instance Name:
- Instance Type:
- Region:
- Instance State:

### CPU Analysis

- Current CPU:
- Maximum CPU:
- Average CPU:
- Spike Started:
- Duration:
- Pattern:

### Process Analysis

- Top Process:
- PID:
- CPU Usage:
- Memory Usage:
- Process Owner:

### Evidence

List the important evidence discovered during investigation.

### Timeline

Describe the important events in chronological order.

### Root Cause

State the most likely root cause.

Clearly distinguish between:

- Confirmed
- Highly likely
- Possible
- Unknown

### Impact

Describe the potential customer/application/infrastructure impact.

### Recommended Remediation

Provide the recommended action and explain why.

### Risk

Describe the risk associated with the remediation.

### Confidence

Provide a confidence level and explain what evidence supports it.

---

## Success Criteria

The investigation is successful when:

- The affected EC2 instance is identified.
- CPU behavior is analyzed.
- The CPU spike timeframe is identified.
- The main CPU-consuming process is identified when possible.
- Relevant evidence is collected.
- Recent changes are considered.
- A root cause is identified or explicitly marked unknown.
- A remediation recommendation is provided.
- Risks are clearly explained.
- No destructive action is performed without authorization.
