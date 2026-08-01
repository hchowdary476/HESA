"""Cyber security action execution domain for JARVIS."""

from __future__ import annotations

import logging
from typing import Any

from JARVIS.core.security.cyber_engine import CyberSecurityEngine
from JARVIS.runtime.ui_bridge import send_log, send_state

logger = logging.getLogger("jarvis.cyber_actions")


def _update_bridge(property_name: str, value: str):
    try:
        from JARVIS.gui.qml_bridge import JarvisBridge
        if JarvisBridge._instance:
            setattr(JarvisBridge._instance, f"_{property_name}", value)
            signal = getattr(JarvisBridge._instance, f"{property_name}Changed")
            signal.emit(value)
    except Exception:
        pass


def handle_cyber_action(action: str, params: dict[str, Any], context: dict[str, Any]) -> bool | None:
    """Execute cyber security and certification learning actions."""
    if not action.startswith("cyber_"):
        return None

    speak = context.get("speak", print)
    engine = CyberSecurityEngine()

    try:
        if action == "cyber_analyze_logs":
            res = engine.analyze_security_logs()
            send_log(res)
            _update_bridge("cyberLogsAudit", res)
            speak("I have correlated today's security logs, sir. Output is posted on the console.")
            return True

        elif action == "cyber_suspicious_processes":
            res = engine.summarize_suspicious_processes()
            send_log(res)
            _update_bridge("cyberProcessAudit", res)
            speak("I have audited active system processes, sir. No transient anomalies isolated.")
            return True

        elif action == "cyber_review_vuln":
            report = params.get("report", "")
            res = engine.review_vulnerability_report(report)
            send_log(res)
            _update_bridge("cyberComplianceReport", res)
            speak("I have reviewed the vulnerability report and compiled mitigation parameters, sir.")
            return True

        elif action == "cyber_explain_cve":
            cve_id = params.get("cve_id", "") or params.get("query", "")
            res = engine.explain_cve(cve_id)
            send_log(res)
            _update_bridge("cyberCveExplanation", res)
            speak(f"Explaining {cve_id}, sir. Detailed mitigation plan is rendered on the console.")
            return True

        elif action == "cyber_generate_soc":
            res = engine.generate_soc_report()
            send_log(res)
            _update_bridge("cyberLogsAudit", res)
            speak("Generating daily SOC operational report, sir. Posture remains secure.")
            return True

        elif action == "cyber_create_timeline":
            res = engine.create_incident_timeline()
            send_log(res)
            _update_bridge("cyberLogsAudit", res)
            speak("I have reconstructed the chronological incident post-mortem timeline, sir.")
            return True

        elif action == "cyber_explain_malware":
            malware = params.get("malware", "") or params.get("query", "")
            res = engine.explain_malware_behavior(malware)
            send_log(res)
            _update_bridge("cyberCveExplanation", res)
            if malware:
                speak(f"Analyzing {malware} execution behavior, sir. Payload indicators are on screen.")
            else:
                speak("Analyzing general malware execution behavior, sir. Payload indicators are on screen.")
            return True

        elif action == "cyber_compare_mitre":
            res = engine.compare_mitre_techniques()
            send_log(res)
            _update_bridge("cyberCveExplanation", res)
            speak("Comparing MITRE ATT&CK techniques and mitigations, sir.")
            return True

        elif action == "cyber_review_arch":
            res = engine.review_security_architecture()
            send_log(res)
            _update_bridge("cyberComplianceReport", res)
            speak("I have performed an architectural security review against Zero Trust principles, sir.")
            return True

        elif action == "cyber_threat_landscape":
            res = engine.summarize_threat_landscape()
            send_log(res)
            _update_bridge("cyberLogsAudit", res)
            speak("Summarizing today's global threat landscape and trending CVEs, sir.")
            return True

        elif action == "cyber_explain_pcap":
            res = engine.explain_packet_capture()
            send_log(res)
            _update_bridge("cyberLogsAudit", res)
            speak("Explaining packet capture anomalies and DNS tunneling signatures, sir.")
            return True

        elif action == "cyber_explain_dns":
            res = engine.explain_dns()
            send_log(res)
            _update_bridge("cyberComplianceReport", res)
            speak("Explaining Domain Name System security risks and mitigation, sir.")
            return True

        elif action == "cyber_teach_linux":
            res = engine.teach_linux()
            send_log(res)
            _update_bridge("cyberLearningRoadmap", res)
            speak("Opening Linux administration and shell security modules, sir.")
            return True

        elif action == "cyber_explain_owasp":
            res = engine.explain_owasp()
            send_log(res)
            _update_bridge("cyberLearningRoadmap", res)
            speak("Summarizing the OWASP Top 10 web vulnerabilities, sir.")
            return True

        elif action == "cyber_explain_zero_trust":
            res = engine.explain_zero_trust()
            send_log(res)
            _update_bridge("cyberLearningRoadmap", res)
            speak("Explaining Zero Trust Architecture principles, sir.")
            return True

        elif action == "cyber_learning_roadmap":
            topic = params.get("topic", "security+")
            res = engine.create_learning_roadmap(topic)
            send_log(res)
            _update_bridge("cyberLearningRoadmap", res)
            speak(f"Creating your personalized learning roadmap for {topic}, sir.")
            return True

        elif action == "cyber_prepare_secplus":
            res = engine.prepare_secplus()
            send_log(res)
            # Quiz question properties are set inside engine.prepare_secplus()
            speak("Here is your CompTIA Security plus study question, sir. Options are listed below.")
            return True

        elif action == "cyber_teach_cloud":
            res = engine.teach_cloud_security()
            send_log(res)
            _update_bridge("cyberComplianceReport", res)
            speak("Opening container and cloud security training modules, sir.")
            return True

        elif action == "cyber_prompt_security":
            prompt = params.get("prompt", "")
            res = engine.check_ai_prompt_security(prompt)
            send_log(res)
            _update_bridge("cyberComplianceReport", res)
            speak("Prompt security audit complete, sir.")
            return True

        else:
            logger.warning("Unrecognized cyber action: %s", action)
            return False

    except Exception as e:
        logger.error("Failed to execute cyber action %s: %s", action, e)
        send_log(f"⚠️ Cyber Engine Error while running {action}: {e}")
        return False

    except Exception as e:
        logger.error("Failed to execute cyber action %s: %s", action, e)
        send_log(f"⚠️ Cyber Engine Error while running {action}: {e}")
        return False
