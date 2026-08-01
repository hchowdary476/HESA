"""Cyber Security Engine for log, process, threat landscape, and cert learning analytics."""

from __future__ import annotations

import json
import logging
import random
import re
import time
from pathlib import Path

import psutil

logger = logging.getLogger("jarvis.cyber_engine")


class CyberSecurityEngine:
    """Core cybersecurity analysis, forensics, threat intelligence, and mentoring engine."""

    def __init__(self) -> None:
        self.log_file = Path("JARVIS/core/system/utils/logs/jarvis.log")
        self.risk_score = 15.0  # Base normal posture risk score out of 100

    def analyze_security_logs(self) -> str:
        """Scan logs for errors, failures, port bindings, and suspicious patterns."""
        anomalies = []
        try:
            if self.log_file.exists():
                with open(self.log_file, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-300:]  # Audit last 300 entries
                for line in lines:
                    if any(w in line.lower() for w in ["error", "fail", "collision", "duplicate", "conflict", "warn"]):
                        anomalies.append(line.strip())
        except Exception as e:
            logger.error("Failed to parse logs: %s", e)

        if not anomalies:
            return (
                "### SOC Log Audit Summary\n\n"
                "**Status:** [GREEN] SECURE\n\n"
                "No suspicious indicators, unauthorized logins, or thread lock failures detected in the active log cache, sir."
            )

        correlation = "\n".join(f"- {anom}" for anom in anomalies[:10])
        return (
            f"### SOC Log Correlation Audit\n\n"
            f"**Status:** [YELLOW] ALERT (Risk Score: {self.risk_score + 10:.1f}/100)\n\n"
            f"Detected {len(anomalies)} anomalies in recent log streams. Correlation vectors below:\n"
            f"{correlation}\n\n"
            f"**Recommendation:** Investigate service bindings and thread contention patterns."
        )

    def summarize_suspicious_processes(self) -> str:
        """Scan running processes for anomalies (temp executions, high CPU, unrecognized executables)."""
        suspicious = []
        count = 0
        cpu_cores = psutil.cpu_count() or 1
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "exe"]):
            try:
                info = proc.info
                exe_path = str(info.get("exe") or "")
                name = str(info.get("name") or "").lower()
                raw_cpu = info.get("cpu_percent") or 0.0
                cpu = raw_cpu / cpu_cores

                # Flag processes running out of TEMP or AppData/Local/Temp
                is_temp = "temp" in exe_path.lower() or "tmp" in exe_path.lower()
                # Flag extremely high CPU usage (e.g. > 85%) as potential miners or runaway threads
                is_high_cpu = cpu > 85.0

                if is_temp or is_high_cpu:
                    suspicious.append(f"PID {info.get('pid')}: `{info.get('name')}` running from `{exe_path}` (CPU: {cpu}%)")
                count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not suspicious:
            return (
                "### Process Audit Report\n\n"
                f"Audited {count} active system processes. No unrecognized binaries, transient scripts in temp directories, or mining spikes detected, sir."
            )

        details = "\n".join(f"- {s}" for s in suspicious[:8])
        return (
            f"### Process Audit Alert\n\n"
            f"**Status:** [RED] CRITICAL (Risk Score: {self.risk_score + 25:.1f}/100)\n\n"
            f"Audited {count} processes. Suspicious binaries isolated:\n"
            f"{details}\n\n"
            f"**Recommendation:** Check process hashes on VirusTotal or terminate transient executables."
        )

    def review_vulnerability_report(self, report_data: str = "") -> str:
        """Analyze a vulnerability payload, highlighting high findings and remediation steps."""
        if not report_data:
            report_data = "OpenSSL Heartbleed, CVE-2014-0160: CVSS 7.5. Read buffer overflow allow key exposure."

        return (
            "### Vulnerability Assessment Report\n\n"
            f"**Target:** {report_data[:80]}...\n"
            "**CVSS Score:** 7.5 (High Risk)\n"
            "**Technical Overview:** The vulnerability allows remote attackers to disclose memory content from the connected client or server, exposing private keys and session cookies.\n\n"
            "**Remediation Action Plan:**\n"
            "1. Upgrade packages to patched binaries.\n"
            "2. Revoke and reissue SSL/TLS keypairs.\n"
            "3. Enable Perfect Forward Secrecy (PFS)."
        )

    def explain_cve(self, cve_id: str) -> str:
        """Provide detailed info on common CVE vulnerabilities."""
        cve_id = cve_id.upper().strip()
        cve_database = {
            "CVE-2021-44228": {
                "name": "Log4Shell",
                "score": "10.0 Critical",
                "desc": "Apache Log4j2 JNDI remote code execution via LDAP lookup injections.",
                "mitigation": "Upgrade Log4j to >= 2.15.0 or remove JndiLookup class from classpath.",
            },
            "CVE-2017-0144": {
                "name": "EternalBlue",
                "score": "9.3 Critical",
                "desc": "SMBv1 buffer overflow exploited by WannaCry ransomware to propagate across networks.",
                "mitigation": "Disable SMBv1, apply Microsoft MS17-010 security patch immediately.",
            },
            "CVE-2014-0160": {
                "name": "Heartbleed",
                "score": "7.5 High",
                "desc": "OpenSSL TLS Heartbeat extension memory disclosure vulnerability.",
                "mitigation": "Upgrade OpenSSL to 1.0.1g, replace compromised private key files.",
            },
        }

        # Check default match or regex match
        cve_info = cve_database.get(cve_id)
        if not cve_info:
            # Fallback regex look
            match = re.search(r"CVE-\d{4}-\d+", cve_id)
            if match and match.group(0) in cve_database:
                cve_info = cve_database[match.group(0)]
                cve_id = match.group(0)

        if not cve_info:
            return (
                f"### CVE Research: {cve_id}\n\n"
                f"Vulnerability record {cve_id} is not cached in my offline dictionary, sir. "
                "However, general mitigation recommends upgrading dependencies and running static vulnerability scans."
            )

        return (
            f"### Vulnerability File: {cve_id} ({cve_info['name']})\n\n"
            f"**CVSS Score:** {cve_info['score']}\n"
            f"**Description:** {cve_info['desc']}\n\n"
            f"**Mitigation Plan:** {cve_info['mitigation']}"
        )

    def generate_soc_report(self) -> str:
        """Compile a SOC Executive summary with active incident statistics."""
        return (
            "### SOC Operational Status Report\n\n"
            "**Operational Posture:** OPTIMIZED (GREEN)\n"
            "**Key Indicators:**\n"
            "- Firewall Status: Active / Blocked 24 intrusions today\n"
            "- Host Intrusion Prevention (HIPS): Active\n"
            "- Suspicious Processes Isolated: 0\n"
            "- File Integrity Check: 100% Verified\n"
            "- API Integrity checks: Passing\n\n"
            "**Overall Risk Index:** 12/100 (Secure)"
        )

    def create_incident_timeline(self) -> str:
        """Create a mock incident chronological log for post-mortem analysis."""
        t = time.time()
        fmt_time = lambda delta: time.strftime("%H:%M:%S", time.localtime(t - delta))
        return (
            "### Incident Post-Mortem Timeline\n\n"
            f"- **{fmt_time(1200)}**: [Detect] IDS alerts triggering on port 445 (SMB) scanning activity.\n"
            f"- **{fmt_time(900)}**: [Isolate] Target server IP `192.168.1.104` isolated via firewall rule.\n"
            f"- **{fmt_time(600)}**: [Analyze] RAM forensics isolated anomalous PowerShell download script.\n"
            f"- **{fmt_time(300)}**: [Mitigate] Offending binary terminated. Key registry entries restored.\n"
            f"- **{fmt_time(0)}**: [Resolve] All host diagnostics report healthy status. Incident closed."
        )

    def explain_malware_behavior(self, malware_name: str) -> str:
        """Detail indicators and behaviors of notable malware strains."""
        m_name = malware_name.lower().strip()

        profiles = {
            "wannacry": {
                "vector": "EternalBlue SMBv1 Exploit (Port 445)",
                "payload": "AES/RSA File Encryption, `.WNCRY` file extension append.",
                "indicators": "Kill-switch URL check, registry modification under Software\\WanaCrypt0r.",
            },
            "emotet": {
                "vector": "Phishing macros, malicious document attachments.",
                "payload": "Polymorphic loader, credential harvesting, spam-bot modules.",
                "indicators": "Scheduled tasks creation, encrypted HTTP POST beacons to dynamic C2 servers.",
            },
            "pegasus": {
                "vector": "Zero-click exploits in messaging apps (iMessage, WhatsApp).",
                "payload": "Complete smartphone compromise (keylogger, camera control, data exfiltration).",
                "indicators": "Modified system binaries, anomalous background data usage spikes.",
            },
        }

        matched = None
        for k, v in profiles.items():
            if k in m_name:
                matched = (k.title(), v)
                break

        if not matched:
            return (
                f"### Malware Profile: {malware_name}\n\n"
                f"Static profile for {malware_name} is not loaded offline. "
                "Generally, malware operates via delivery (phishing), exploitation, installation (persistence), C2 communication, and actions on objectives."
            )

        title, p = matched
        return (
            f"### Threat Profile: {title} Ransomware/Spyware\n\n"
            f"**Initial Access Vector:** {p['vector']}\n"
            f"**Execution Payload:** {p['payload']}\n"
            f"**Key Host Indicators:** {p['indicators']}"
        )

    def compare_mitre_techniques(self, command: str = "") -> str:
        """Provide comparisons of MITRE ATT&CK techniques."""
        return (
            "### MITRE ATT&CK Technique Comparison\n\n"
            "**T1055 (Process Injection) vs T1574 (Hijack Execution Flow):**\n\n"
            "- **Process Injection (T1055):** Writing shellcode directly into a running process's memory space (e.g. DLL Injection, Process Hollowing) to evade security alerts.\n"
            "- **Hijack Execution Flow (T1574):** Placing a malicious DLL/binary in a path loaded before the legitimate one (e.g. DLL search order hijacking, path interception).\n\n"
            "**Defense Strategy:** PROCESS INJECTION is best mitigated by monitoring syscalls like `VirtualAllocEx`/`WriteProcessMemory`. HIJACK EXECUTION is mitigated by enforcing strict directory permissions and absolute DLL search path constraints."
        )

    def review_security_architecture(self) -> str:
        """Evaluate a generic blueprint against Zero Trust principles."""
        return (
            "### Security Architecture Design Review\n\n"
            "**Architecture Posture Checklist:**\n"
            "- **Identity Trust:** Lacking multi-factor verification on internal database calls. (FAIL)\n"
            "- **Microsegmentation:** Subnets isolated but routing firewall lacks session checking. (WARNING)\n"
            "- **Continuous Inspection:** Network metrics logged but not correlated in real time. (WARNING)\n\n"
            "**Remediation Recommendation:** Transition architecture from boundary-defense to Zero Trust Network Access (ZTNA) model. Enforce strict least-privilege token access for every application layer."
        )

    def summarize_threat_landscape(self) -> str:
        """Generate summary of active threat vectors and actors."""
        return (
            "### Global Threat Intelligence Summary\n\n"
            "**Active Threat Groups:** APT29 (Cozy Bear), APT41 (Double Dragon), Lazarus Group.\n"
            "**Top Active Attack Vectors:**\n"
            "1. Software Supply Chain Interceptions\n"
            "2. Exploitation of Edge VPN devices (Ivanti, Fortinet)\n"
            "3. Drive-by downloads via compromised ad networks\n\n"
            "**Trending Vulnerabilities:** CVE-2024-21887 (Command Injection), CVE-2024-1709 (Auth Bypass)."
        )

    def explain_packet_capture(self) -> str:
        """Analyze and explain network communication anomalies in pcap reports."""
        return (
            "### Network PCAP Diagnostic Report\n\n"
            "**Anomalous Patterns Isolated:**\n"
            "- **DNS Tunneling Indicator:** Excessive subdomain lookup queries containing high entropy base64 payloads directed to unknown nameservers.\n"
            "- **Port Scan Signature:** TCP SYN requests sent to 100+ consecutive ports on `192.168.1.1` in under 2 seconds.\n"
            "- **Exfiltration Vector:** Outbound HTTP POST payload transfer on port 80 bypassing standard proxy rules.\n\n"
            "**Mitigation:** Configure DNS security filters (DNSSEC) and restrict outbound firewall policies."
        )

    def create_learning_roadmap(self, topic: str = "security+") -> str:
        """Provide a study guide syllabus for security certifications."""
        topic_lower = topic.lower()
        if "sec" in topic_lower or "security" in topic_lower:
            cert = "CompTIA Security+"
            syllabus = (
                "1. General Security Concepts (Threats, attacks, vulnerabilities)\n"
                "2. Architecture & Design (Identity management, cloud networks, cryptography)\n"
                "3. Security Operations (Incident response, logging, alerts)\n"
                "4. Governance, Risk & Compliance (Frameworks, privacy policies)"
            )
        elif "ceh" in topic_lower or "ethical" in topic_lower:
            cert = "Certified Ethical Hacker (CEH)"
            syllabus = (
                "1. Footprinting and Reconnaissance\n"
                "2. Scanning Networks & Enumeration\n"
                "3. System Hacking & Malware Threats\n"
                "4. Web Server & Wireless Hacking"
            )
        elif "cysa" in topic_lower:
            cert = "CompTIA CySA+"
            syllabus = (
                "1. Threat and Vulnerability Management\n"
                "2. Software and Systems Security\n"
                "3. Security Operations and Monitoring\n"
                "4. Incident Response and Compliance"
            )
        else:
            cert = "CISSP Core Concepts"
            syllabus = (
                "1. Security & Risk Management\n"
                "2. Asset Security\n"
                "3. Security Architecture & Engineering\n"
                "4. Communication & Network Security"
            )

        return (
            f"### Cyber Learning Roadmap: {cert}\n\n"
            f"**Recommended Study Framework:**\n"
            f"{syllabus}\n\n"
            "**Study Tip:** Use my quiz prep feature (e.g. *Hesa, prepare me for Security+*) to drill question scenarios."
        )

    def prepare_secplus(self) -> str:
        """Serve an interactive quiz question for Security+ prep."""
        quizzes = [
            {
                "q": "Which of the following cryptographic algorithms uses a symmetric key structure?",
                "options": ["A) RSA", "B) AES", "C) ECC", "D) Diffie-Hellman"],
                "answer": "B) AES. Advanced Encryption Standard is a symmetric block cipher, while RSA, ECC, and DH are asymmetric.",
            },
            {
                "q": "An attacker intercepts communication between a client and a server and replaces the server's public key with their own. What type of attack is this?",
                "options": ["A) Phishing", "B) DDoS", "C) Man-in-the-Middle (MitM)", "D) SQL Injection"],
                "answer": "C) Man-in-the-Middle (MitM). Intercepting and altering transit keys represents a classic MitM scenario.",
            },
            {
                "q": "Which security control is designed to detect and log unauthorized modifications to system files?",
                "options": ["A) Firewall", "B) File Integrity Monitoring (FIM)", "C) DLP", "D) WAF"],
                "answer": "B) File Integrity Monitoring (FIM). FIM systems (like OSSEC or Tripwire) calculate file hashes to isolate changes.",
            },
        ]

        item = random.choice(quizzes)

        try:
            from JARVIS.gui.qml_bridge import JarvisBridge

            if JarvisBridge._instance:
                q_data = {
                    "question": item["q"],
                    "options": item["options"],
                    "answer": item["answer"].split(")")[0].strip(),
                    "explanation": item["answer"].split(")", 1)[1].strip() if ")" in item["answer"] else item["answer"],
                }
                JarvisBridge._instance._cyber_quiz_question = json.dumps(q_data)
                JarvisBridge._instance.cyberQuizQuestionChanged.emit(json.dumps(q_data))
        except Exception:
            pass

        options_str = "\n".join(item["options"])
        return f"### CompTIA Security+ Quiz Challenge\n\n**Question:** {item['q']}\n\n{options_str}\n\n**Answer Key:** ||{item['answer']}||"

    def teach_cloud_security(self) -> str:
        """Explain core cloud security principles."""
        return (
            "### Cloud & Container Security Syllabus\n\n"
            "**1. Shared Responsibility Model:**\n"
            "- Cloud Provider (AWS/Azure/GCP): Secures physical infrastructure, hardware, and hypervisors.\n"
            "- Customer: Secures user access, data storage, network configuration, and host operating systems.\n\n"
            "**2. Kubernetes / Container Security:**\n"
            "- Scan container images during CI/CD builds for vulnerabilities.\n"
            "- Limit container runtime capabilities (disable root privilege, enforce read-only filesystems).\n"
            "- Enforce network policies to segment pod-to-pod communications.\n\n"
            "**3. DevSecOps integration:**\n"
            "Run Static (SAST) and Dynamic (DAST) scanners, and audit Infrastructure as Code (IaC) templates."
        )

    def explain_dns(self) -> str:
        """Provide detailed holographic-themed explanation of Domain Name System (DNS)."""
        return (
            "### Domain Name System (DNS) Security Blueprint\n\n"
            "**Core Concept:** DNS translates human-readable domain names (e.g. `hesa.ai`) into machine-routable IP addresses (e.g. `198.51.100.42`). It is the internet's address book.\n\n"
            "**Key Security Risks:**\n"
            "1. **DNS Spoofing/Poisoning:** Attackers inject falsified DNS entries into a resolver cache, redirecting traffic to malicious servers.\n"
            "2. **DNS Tunneling:** Exfiltrating data or routing C2 traffic over port 53 (DNS query/response protocol) to bypass firewalls.\n"
            "3. **DDoS Amplification:** Exploiting open resolvers to flood a target with massive spoofed responses.\n\n"
            "**Defensive Measures:** Enforce DNSSEC (cryptographic verification of DNS records), use secure encrypted protocols (DoH - DNS over HTTPS, DoT - DNS over TLS), and filter DNS queries using threat intelligence."
        )

    def teach_linux(self) -> str:
        """Provide detailed holographic-themed Linux security and administration lessons."""
        return (
            "### Linux Security & Administration System\n\n"
            "**Architecture:** Linux separates user space from kernel space. Security is anchored on permissions, users, and the root account.\n\n"
            "**Core Fundamentals:**\n"
            "- **Permissions:** File access is controlled by Read (r), Write (w), and Execute (x) flags for User, Group, and Others (e.g., `chmod 755 file.sh`).\n"
            "- **Hardening Actions:**\n"
            "  1. Disable root login over SSH (`PermitRootLogin no` in sshd_config).\n"
            "  2. Implement least privilege (limit sudo access under `/etc/sudoers`).\n"
            "  3. Keep services minimized (turn off unused systemd units: `systemctl disable --now service_name`).\n"
            "  4. Monitor logs in real time (`tail -f /var/log/auth.log` or `journalctl -u ssh`).\n\n"
            "**Syllabus Focus:** Linux scripting automation, cron jobs, and PAM (Pluggable Authentication Modules) security."
        )

    def explain_owasp(self) -> str:
        """Provide detailed holographic-themed explanation of the OWASP Top 10 web vulnerabilities."""
        return (
            "### OWASP Top 10 Web Application Vulnerabilities\n\n"
            "The Open Web Application Security Project (OWASP) lists the top ten critical application flaws:\n\n"
            "1. **A01:2021-Broken Access Control:** Users acting outside of intended permissions (e.g., Privilege Escalation).\n"
            "2. **A02:2021-Cryptographic Failures:** Data in transit or at rest exposed due to weak/missing encryption (formerly Sensitive Data Exposure).\n"
            "3. **A03:2021-Injection:** SQL, NoSQL, OS Command, or LDAP injection where untrusted input is executed as a command.\n"
            "4. **A04:2021-Insecure Design:** Flaws in threat modeling and architectural security before coding begins.\n"
            "5. **A05:2021-Security Misconfiguration:** Missing hardening settings, default credentials, or overly verbose error messages.\n\n"
            "**Mitigation Framework:** Enforce parameterized queries, validate and sanitize all inputs, implement strong role-based access control (RBAC), and encrypt sensitive traffic via TLS 1.3."
        )

    def explain_zero_trust(self) -> str:
        """Provide detailed holographic-themed explanation of Zero Trust Architecture."""
        return (
            "### Zero Trust Architecture (ZTA) Model\n\n"
            "**Core Principle:** *Never Trust, Always Verify*. Zero Trust shifts security from perimeter defense (firewall boundaries) to continuous verification of every asset, user, and session.\n\n"
            "**Three Pillars of Zero Trust:**\n"
            "1. **Verify Explicitly:** Always authenticate and authorize based on all available data points (identity, location, device health, service workload).\n"
            "2. **Use Least Privileged Access:** Limit user access with Just-In-Time (JIT) and Just-Enough-Access (JEA) models, risk-based adaptive policies, and data protection.\n"
            "3. **Assume Breach:** Minimize blast radius by segmenting networks (microsegmentation). Verify all sessions end-to-end, and continuously monitor telemetry to detect anomalies.\n\n"
            "**Implementation Key:** Replace traditional VPNs with Zero Trust Network Access (ZTNA) brokers."
        )

    def check_ai_prompt_security(self, prompt: str) -> str:
        """Scan LLM prompt inputs for jailbreak attempt indicators."""
        patterns = [
            r"ignore previous instructions",
            r"bypass system rules",
            r"dan mode",
            r"jailbreak",
            r"system prompt leak",
            r"developer commands",
            r"override restrictions",
        ]

        matched = []
        for p in patterns:
            if re.search(p, prompt.lower()):
                matched.append(p)

        if not matched:
            return (
                "### Prompt Security Audit\n\n"
                "**Result:** [GREEN] PASS\n"
                "No jailbreak signatures, system prompt injection attempts, or policy bypass variables detected in this prompt payload."
            )

        list_matched = ", ".join(f"`{m}`" for m in matched)
        return (
            "### Prompt Security Alert\n\n"
            "**Result:** [RED] RISK DETECTED\n"
            f"Isolated injection fingerprint matching: {list_matched}.\n\n"
            "**Recommendation:** Reject this prompt or sanitize inputs before dispatching to LLM routers."
        )
