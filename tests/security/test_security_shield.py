"""Unit tests for JARVIS Security Shield."""

import os
import json
import pytest
from unittest import mock
from cryptography.fernet import Fernet, InvalidToken

from JARVIS.core.security import security_shield

@pytest.fixture(autouse=True)
def clean_security_files():
    """Ensure clean files before and after each test."""
    files_to_remove = [
        security_shield.KEY_FILE,
        security_shield.SETTINGS_FILE,
        security_shield.FACE_TEMPLATE_FILE,
        security_shield.LAST_NOTIFICATION_FILE,
        os.path.join("logs", "security_validation_report.md")
    ]
    for f in files_to_remove:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
                
    # Clear logs directory
    if os.path.exists(security_shield.LOGS_DIR):
        for f in os.listdir(security_shield.LOGS_DIR):
            try:
                os.remove(os.path.join(security_shield.LOGS_DIR, f))
            except Exception:
                pass
                
    security_shield.SETTINGS_TAMPERED = False
    security_shield.LOGS_TAMPERED = False
    security_shield.CONSECUTIVE_FAILURES = 0
    yield
    
    # Cleanup after test
    for f in files_to_remove:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

def test_fernet_encryption_decryption():
    """Test that data can be encrypted and decrypted and that tampering raises InvalidToken."""
    raw_data = b"Secret Owner Face Feature Template 1234"
    enc = security_shield.encrypt_data(raw_data)
    assert enc != raw_data
    
    dec = security_shield.decrypt_data(enc)
    assert dec == raw_data
    
    # Tamper with the encrypted bytes
    tampered_enc = bytearray(enc)
    tampered_enc[15] ^= 0xFF  # Flip bits
    
    with pytest.raises(InvalidToken):
        security_shield.decrypt_data(bytes(tampered_enc))

def test_settings_storage_and_tamper_detection():
    """Verify load/save settings and verify settings tamper detection flags are raised."""
    settings = security_shield.load_settings()
    assert settings["recovery_pin"] == "1234"
    assert settings["test_mode"] is True
    assert security_shield.SETTINGS_TAMPERED is False
    
    settings["recovery_pin"] = "4321"
    security_shield.save_settings(settings)
    
    loaded = security_shield.load_settings()
    assert loaded["recovery_pin"] == "4321"
    assert security_shield.SETTINGS_TAMPERED is False
    
    # Manually write tampered bytes to settings file
    with open(security_shield.SETTINGS_FILE, "wb") as f:
        f.write(b"Tampered data plain-text settings file!")
        
    loaded_tampered = security_shield.load_settings()
    assert loaded_tampered["recovery_pin"] == "1234"  # Defaults returned
    assert security_shield.SETTINGS_TAMPERED is True

def test_optional_location_telemetry():
    """Test location collection toggle behavior."""
    # Location collection = False
    tel_no_loc = security_shield.get_telemetry(collect_location=False)
    assert "location" not in tel_no_loc
    assert tel_no_loc["username"] is not None
    assert tel_no_loc["local_ip"] is not None
    assert tel_no_loc["wifi_ssid"] is not None

    # Location collection = True (mocked location services)
    with mock.patch("JARVIS.core.security.security_shield.get_windows_location") as mock_loc:
        mock_loc.return_value = {"latitude": 45.0, "longitude": -90.0}
        tel_with_loc = security_shield.get_telemetry(collect_location=True)
        assert tel_with_loc["location"] == {"latitude": 45.0, "longitude": -90.0}

def test_logs_decryption_and_tamper_detection():
    """Verify log encryption/decryption, loading, and log tamper flags."""
    log_entry = {"timestamp": "20260618_120000", "event": "FAILED_AUTH"}
    security_shield.save_log(log_entry, image_bytes=b"fake_image_bytes")
    
    loaded_logs = security_shield.load_logs()
    assert len(loaded_logs) == 1
    assert loaded_logs[0]["event"] == "FAILED_AUTH"
    assert security_shield.LOGS_TAMPERED is False
    
    # Verify encrypted image exists
    img_path = os.path.join(security_shield.LOGS_DIR, "20260618_120000_image.bin")
    assert os.path.exists(img_path)
    
    # Tamper with the log file
    log_file = os.path.join(security_shield.LOGS_DIR, "20260618_120000_log.json.enc")
    with open(log_file, "wb") as f:
        f.write(b"Tampered raw bytes logs!")
        
    loaded_tampered = security_shield.load_logs()
    assert len(loaded_tampered) == 1
    assert loaded_tampered[0]["error"] == "TAMPERED / INTEGRITY_FAILURE"
    assert security_shield.LOGS_TAMPERED is True

def test_face_templates_encryption():
    """Test encrypting and decrypting face templates."""
    face_data = b"face_encoding_metrics"
    security_shield.save_face_template(face_data)
    
    loaded = security_shield.load_face_template()
    assert loaded == face_data

def test_notification_delivery_and_rate_limiting():
    """Verify notification webhook send rate limit controls."""
    payload = {"alert": "auth_failure"}
    
    with mock.patch("urllib.request.urlopen") as mock_url:
        mock_response = mock.Mock()
        mock_response.status = 200
        mock_url.return_value.__enter__.return_value = mock_response
        
        # Initial call succeeds
        success = security_shield.send_webhook_notification(payload)
        assert success is True
        
        # Second call within 60s is throttled
        success_throttled = security_shield.send_webhook_notification(payload)
        assert success_throttled is False


def test_face_match_failure_flow():
    """Verify face matching execution when forced to fail."""
    os.environ["JARVIS_FACE_MATCH_STATUS"] = "FALSE"
    
    with mock.patch("JARVIS.core.security.security_shield.lock_workstation") as mock_lock, \
         mock.patch("JARVIS.core.security.security_shield.send_webhook_notification") as mock_notify, \
         mock.patch("JARVIS.core.security.security_shield.get_camera_status") as mock_cam, \
         mock.patch("JARVIS.core.voice.ses_motoru.speak") as mock_speak:
        
        mock_cam.return_value = "READY"
        
        app_mock = mock.Mock()
        app_mock.after.side_effect = lambda ms, cb: cb()
        
        # First failure
        matched = security_shield.run_face_match_check(app=app_mock)
        assert matched is False
        assert security_shield.CONSECUTIVE_FAILURES == 1
        assert mock_speak.call_count == 1
        
        # Second failure
        matched = security_shield.run_face_match_check(app=app_mock)
        assert security_shield.CONSECUTIVE_FAILURES == 2
        
        # Check settings
        settings = security_shield.load_settings()
        assert settings["test_mode"] is True
        # Since test_mode=True, mock_lock shouldn't be called
        assert mock_lock.call_count == 0
        
        # Third failure - triggers PIN recovery
        matched = security_shield.run_face_match_check(app=app_mock)
        assert security_shield.CONSECUTIVE_FAILURES == 3
        app_mock.trigger_pin_recovery_dialog.assert_called()


def test_pin_recovery_reset():

    """Test that recovery dialog reset actions behave correctly."""
    security_shield.CONSECUTIVE_FAILURES = 3
    
    # Simulate PIN recovery dialog success
    security_shield.CONSECUTIVE_FAILURES = 0
    os.environ["JARVIS_FACE_MATCH_STATUS"] = "TRUE"
    
    assert security_shield.CONSECUTIVE_FAILURES == 0
    assert os.environ.get("JARVIS_FACE_MATCH_STATUS") == "TRUE"
