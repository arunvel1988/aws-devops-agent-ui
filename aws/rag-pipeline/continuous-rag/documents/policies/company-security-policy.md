# Company Security Policy

Production SSH access must use approved identity-based access.
Production instances must have SSM Agent installed and an IAM role with the required SSM permissions.
Secrets must not be stored in source code or Docker images.
Critical security changes require review before deployment.
