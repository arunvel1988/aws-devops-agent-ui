# High CPU Runbook

When an EC2 instance has sustained CPU above 80 percent:

1. Identify the top CPU-consuming process.
2. Check whether the process belongs to the approved application.
3. Review recent deployment and application logs.
4. If the process is confirmed runaway and approved for termination, stop or restart it using the approved operational procedure.
5. Record the action and evidence in the incident ticket.
