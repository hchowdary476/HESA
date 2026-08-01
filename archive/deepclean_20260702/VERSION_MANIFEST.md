# JARVIS Version Manifest

This document records the official production version manifest, build mappings, and package library dependencies.

---

## 1. Version Control Audits

### • Feature Name: Version Manifest Checker
- **File Location**: [installer/setup_wizard.py](file:///c:/Users/veera/OneDrive/Desktop/Open.Jarvis-main/installer/setup_wizard.py)
- **Purpose**: Validates version number checks and system path registries.
- **Working**: Yes
- **Backend Connected**: Yes
- **Frontend Connected**: Yes
- **Button Working**: Yes
- **Live Data**: Yes
- **Performance**: High (prerequisite check runs under 10ms)
- **Dependencies**: None
- **Issues Found**: None
- **Severity**: None
- **Recommended Fix**: None
- **Priority**: Low

---

## 2. Release metadata
- **Product Name**: JARVIS Enterprise AI Operating System
- **Stable Version**: **v3.0.0**
- **Library Compatibility**:
  - `psutil` >= 5.9.0
  - `numpy` >= 1.22.0
  - `requests` >= 2.27.0
  - `cryptography` >= 37.0.0
- **Database Mappings**: Uses memory-based federated layers, TF-IDF vector matrices, and property graphs.
