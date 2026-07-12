import subprocess
import psutil
import docker
import json
import os
from typing import Dict, List

from mcp.server.fastmcp import FastMCP

###############################################################################
# MCP SERVER
###############################################################################

mcp = FastMCP("EC2 Operations MCP")

docker_client = docker.from_env()

###############################################################################
# HELPERS
###############################################################################

def run_command(command: str) -> str:
    """
    Execute shell command and return output.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.stdout:
            return result.stdout.strip()

        return result.stderr.strip()

    except Exception as e:
        return str(e)


def get_cpu():
    return round(psutil.cpu_percent(interval=1), 2)


def get_memory():

    mem = psutil.virtual_memory()

    return {
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
        "percent": mem.percent,
    }


def get_disk():

    disk = psutil.disk_usage("/")

    return {
        "total_gb": round(disk.total / (1024 ** 3), 2),
        "used_gb": round(disk.used / (1024 ** 3), 2),
        "free_gb": round(disk.free / (1024 ** 3), 2),
        "percent": disk.percent,
    }


def get_load():

    try:
        load = os.getloadavg()

        return {
            "1min": round(load[0], 2),
            "5min": round(load[1], 2),
            "15min": round(load[2], 2),
        }

    except:

        return {
            "1min": 0,
            "5min": 0,
            "15min": 0,
        }


def get_uptime():

    return run_command("uptime -p")


def get_failed_services():

    return run_command("systemctl --failed --no-pager")


def top_cpu_processes():

    return run_command(
        "ps -eo pid,user,comm,%cpu --sort=-%cpu | head -10"
    )


def top_memory_processes():

    return run_command(
        "ps -eo pid,user,comm,%mem --sort=-%mem | head -10"
    )


###############################################################################
# DOCKER
###############################################################################

def docker_summary():

    output = []

    try:

        containers = docker_client.containers.list(all=True)

        for container in containers:

            item = {
                "name": container.name,
                "status": container.status,
                "image": str(container.image.tags),
            }

            try:

                stats = container.stats(stream=False)

                cpu = stats["cpu_stats"]["cpu_usage"]["total_usage"]

                mem = stats["memory_stats"]["usage"]

                item["cpu_raw"] = cpu

                item["memory_mb"] = round(mem / 1024 / 1024, 2)

            except Exception:

                item["cpu_raw"] = 0

                item["memory_mb"] = 0

            output.append(item)

    except Exception as e:

        output.append(
            {
                "error": str(e)
            }
        )

    return output


###############################################################################
# TOOL 1
###############################################################################

@mcp.tool(
    name="investigate_server",
    description="Investigate why the EC2 server is slow or unhealthy."
)
def investigate_server() -> dict:

    cpu = get_cpu()

    memory = get_memory()

    disk = get_disk()

    load = get_load()

    uptime = get_uptime()

    failed_services = get_failed_services()

    cpu_processes = top_cpu_processes()

    memory_processes = top_memory_processes()

    docker_info = docker_summary()

    findings = []

    recommendations = []

    health_score = 100

    ###########################################################################
    # CPU
    ###########################################################################

    if cpu > 90:

        findings.append(
            f"Critical CPU usage detected ({cpu}%)."
        )

        recommendations.append(
            "Investigate high CPU processes."
        )

        health_score -= 25

    elif cpu > 75:

        findings.append(
            f"High CPU usage detected ({cpu}%)."
        )

        recommendations.append(
            "Monitor CPU usage."
        )

        health_score -= 10

    ###########################################################################
    # MEMORY
    ###########################################################################

    if memory["percent"] > 90:

        findings.append(
            f"Critical memory usage ({memory['percent']}%)."
        )

        recommendations.append(
            "Check for memory leaks."
        )

        health_score -= 20

    elif memory["percent"] > 75:

        findings.append(
            f"High memory usage ({memory['percent']}%)."
        )

        health_score -= 10

    ###########################################################################
    # DISK
    ###########################################################################

    if disk["percent"] > 90:

        findings.append(
            f"Disk almost full ({disk['percent']}%)."
        )

        recommendations.append(
            "Clean logs and Docker images."
        )

        health_score -= 20

    elif disk["percent"] > 75:

        findings.append(
            f"Disk usage is high ({disk['percent']}%)."
        )

        health_score -= 10

    ###########################################################################
    # FAILED SERVICES
    ###########################################################################

    if "0 loaded units listed" not in failed_services.lower():

        findings.append(
            "One or more Linux services have failed."
        )

        recommendations.append(
            "Review failed systemd services."
        )

        health_score -= 10

    ###########################################################################
    # DOCKER
    ###########################################################################

    running = 0

    stopped = 0

    for c in docker_info:

        if "status" not in c:
            continue

        if c["status"] == "running":

            running += 1

        else:

            stopped += 1

    if stopped > 0:

        findings.append(
            f"{stopped} stopped Docker container(s) found."
        )

        recommendations.append(
            "Inspect stopped containers."
        )

        health_score -= 5

    ###########################################################################
    # DEFAULT
    ###########################################################################

    if len(findings) == 0:

        findings.append(
            "No critical issues detected."
        )

        recommendations.append(
            "Continue monitoring."
        )

    ###########################################################################
    # RETURN
    ###########################################################################

    return {

        "status": "success",

        "health_score": max(health_score, 0),

        "summary": {

            "cpu_percent": cpu,

            "memory": memory,

            "disk": disk,

            "load_average": load,

            "uptime": uptime,

            "running_containers": running,

            "stopped_containers": stopped

        },

        "findings": findings,

        "recommendations": recommendations,

        "failed_services": failed_services,

        "top_cpu_processes": cpu_processes,

        "top_memory_processes": memory_processes,

        "docker": docker_info

    }

###############################################################################
# TOOL 2 - SECURITY AUDIT
###############################################################################

def ssh_root_login():

    return run_command(
        "grep '^PermitRootLogin' /etc/ssh/sshd_config 2>/dev/null || echo 'Not Found'"
    )


def ssh_password_auth():

    return run_command(
        "grep '^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null || echo 'Not Found'"
    )


def firewall_status():

    return run_command(
        "ufw status 2>/dev/null || firewall-cmd --state 2>/dev/null || echo 'Firewall Not Installed'"
    )


def open_ports():

    return run_command(
        "ss -tulnp"
    )


def docker_security():

    findings = []

    try:

        containers = docker_client.containers.list(all=True)

        for c in containers:

            try:

                inspect = docker_client.api.inspect_container(c.id)

                cfg = inspect["Config"]

                host = inspect["HostConfig"]

                if cfg.get("User", "") == "":
                    findings.append(
                        f"{c.name}: running as root"
                    )

                if host.get("Privileged"):

                    findings.append(
                        f"{c.name}: privileged container"
                    )

                image = cfg.get("Image", "")

                if image.endswith(":latest"):

                    findings.append(
                        f"{c.name}: using latest tag"
                    )

            except Exception as e:

                findings.append(str(e))

    except Exception as e:

        findings.append(str(e))

    return findings


@mcp.tool(
    name="security_audit",
    description="Perform a Linux and Docker security audit."
)
def security_audit():

    score = 100

    findings = []

    recommendations = []

    #######################################################################
    # SSH
    #######################################################################

    root_login = ssh_root_login()

    if "yes" in root_login.lower():

        score -= 25

        findings.append(
            "SSH Root Login is ENABLED."
        )

        recommendations.append(
            "Disable PermitRootLogin."
        )

    password = ssh_password_auth()

    if "yes" in password.lower():

        score -= 20

        findings.append(
            "SSH Password Authentication is ENABLED."
        )

        recommendations.append(
            "Use SSH keys only."
        )

    #######################################################################
    # FIREWALL
    #######################################################################

    firewall = firewall_status()

    if "inactive" in firewall.lower():

        score -= 15

        findings.append(
            "Firewall is disabled."
        )

        recommendations.append(
            "Enable UFW."
        )

    #######################################################################
    # DOCKER
    #######################################################################

    docker_findings = docker_security()

    if docker_findings:

        score -= min(len(docker_findings) * 5, 25)

        findings.extend(docker_findings)

        recommendations.append(
            "Review Docker security configuration."
        )

    #######################################################################
    # DISK
    #######################################################################

    disk = get_disk()

    if disk["percent"] > 90:

        score -= 10

        findings.append(
            f"Disk usage is high ({disk['percent']}%)."
        )

        recommendations.append(
            "Free disk space."
        )

    #######################################################################
    # OPEN PORTS
    #######################################################################

    ports = open_ports()

    #######################################################################
    # DEFAULT
    #######################################################################

    if not findings:

        findings.append(
            "No major security issues detected."
        )

    if not recommendations:

        recommendations.append(
            "System follows basic security practices."
        )

    #######################################################################
    # RETURN
    #######################################################################

    return {

        "status": "success",

        "security_score": max(score, 0),

        "findings": findings,

        "recommendations": recommendations,

        "ssh_root_login": root_login,

        "ssh_password_authentication": password,

        "firewall": firewall,

        "disk_usage": disk,

        "open_ports": ports

    }


###############################################################################
# MAIN
###############################################################################

if __name__ == "__main__":

    print("=" * 60)
    print("Starting EC2 Operations MCP Server")
    print("Transport : Streamable HTTP")
    print("Host      : 0.0.0.0")
    print("Port      : 8080")
    print("Endpoint  : http://0.0.0.0:8080/mcp")
    print("=" * 60)

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8080,
        path="/mcp",
    )
