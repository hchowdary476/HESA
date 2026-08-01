import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from JARVIS.core.system.utils.gui_lifecycle_logger import log_close_reason, log_lifecycle


class SystemTrayManager(QSystemTrayIcon):
    """
    JARVIS system tray icon with full service-state awareness.

    State model per service:
        HEALTHY         → green dot (silent)
        RESTARTING      → yellow dot + balloon "⟳ Restarting <name>"
        RECOVERING      → yellow dot + balloon "↻ Recovering <name>"
        RECOVERED       → green dot  + balloon "✓ <name> Recovered"
        FAILED          → red dot    + balloon "✗ <name> Failed (max retries exceeded)"

    JARVIS NEVER exits due to a backend service failure; only the explicit
    "Exit JARVIS" menu item triggers app shutdown.
    """

    # Signals (PySide6)
    sig_open_dashboard = Signal()
    sig_voice_toggle = Signal(bool)
    sig_restart_jarvis = Signal()
    sig_reload_plugins = Signal()
    sig_show_diagnostics = Signal()
    sig_exit_completely = Signal()
    # Internal signal to safely update tray from non-Qt threads
    sig_service_state_changed = Signal(str, str)  # (service_name, status)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent

        # Load initial voice enabled state from ConfigManager
        self.voice_enabled = True
        try:
            from JARVIS.config.manager import ConfigManager

            config_mgr = ConfigManager()
            config_mgr.load()
            self.voice_enabled = config_mgr.get("voice.voice_enabled", True)
        except Exception:
            pass

        self.service_health = {}  # {name: status_string}

        self._setup_tray_icon()
        self._create_context_menu()
        self._setup_health_monitor()

        # Connect internal signal (thread-safe cross-thread update)
        self.sig_service_state_changed.connect(self._on_service_state_changed)
        log_lifecycle("TRAY_INITIALIZED", "SystemTrayManager initialized")

    # ── Setup ────────────────────────────────────────────────────────────────

    def _setup_tray_icon(self):
        self.setIcon(self._get_colored_icon("green"))
        self.setToolTip("HESA — AI Assistant (All systems nominal)")
        self.activated.connect(self._on_tray_activated)

    def _get_colored_icon(self, status):
        """Draw a status dot on the HESA icon."""
        pixmap = None
        base_paths = ["jarvis.ico", "assets/jarvis_face.png"]
        for path in base_paths:
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    break

        if pixmap is None or pixmap.isNull():
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(0, 191, 255))
            painter.drawEllipse(4, 4, 24, 24)
            painter.end()

        pixmap_copy = pixmap.copy()
        painter = QPainter(pixmap_copy)
        painter.setRenderHint(QPainter.Antialiasing)

        color_map = {
            "red": QColor(239, 68, 68),
            "yellow": QColor(245, 158, 11),
            "orange": QColor(249, 115, 22),
            "green": QColor(16, 185, 129),
        }
        color = color_map.get(status, QColor(16, 185, 129))

        dot_size = max(8, pixmap_copy.width() // 4)
        x = pixmap_copy.width() - dot_size - 1
        y = pixmap_copy.height() - dot_size - 1
        painter.setBrush(color)
        painter.setPen(QColor(18, 18, 18, 200))
        painter.drawEllipse(x, y, dot_size, dot_size)
        painter.end()

        return QIcon(pixmap_copy)

    def _create_context_menu(self):
        menu = QMenu()

        open_action = QAction("Open Dashboard", menu)
        open_action.triggered.connect(self.sig_open_dashboard.emit)
        menu.addAction(open_action)
        menu.addSeparator()

        self.voice_action = QAction("Voice: ON" if self.voice_enabled else "Voice: OFF", menu)
        self.voice_action.setCheckable(True)
        self.voice_action.setChecked(self.voice_enabled)
        self.voice_action.toggled.connect(self._on_voice_toggle)
        menu.addAction(self.voice_action)
        menu.addSeparator()

        restart_action = QAction("Restart HESA", menu)
        restart_action.triggered.connect(self.sig_restart_jarvis.emit)
        menu.addAction(restart_action)

        reload_action = QAction("Reload Plugins", menu)
        reload_action.triggered.connect(self.sig_reload_plugins.emit)
        menu.addAction(reload_action)
        menu.addSeparator()

        diag_action = QAction("Diagnostics & Status", menu)
        diag_action.triggered.connect(self.sig_show_diagnostics.emit)
        menu.addAction(diag_action)
        menu.addSeparator()

        exit_action = QAction("Exit HESA", menu)
        exit_action.triggered.connect(self._on_exit_clicked)
        menu.addAction(exit_action)

        self.setContextMenu(menu)

    def _setup_health_monitor(self):
        """Periodic tray refresh (icon colour)."""
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._update_tray_appearance)
        self.health_timer.start(5000)

    # ── Public API ──────────────────────────────────────────────────────────

    def update_service_status(self, service_name, status):
        """
        Thread-safe update called from ServiceHealthMonitor's notify_callback.
        Emits sig_service_state_changed so Qt processes it on the main thread.
        """
        self.sig_service_state_changed.emit(service_name, status)

    def show_notification(self, title, message, duration=5000):
        """Show a system tray balloon notification."""
        self.showMessage(title, message, QSystemTrayIcon.Information, duration)

    # ── Internal slots ───────────────────────────────────────────────────────

    def _on_service_state_changed(self, service_name, status):
        """Called on the Qt main thread; updates dict + icon + shows balloon."""
        prev = self.service_health.get(service_name)
        self.service_health[service_name] = status
        self._update_tray_appearance()

        # Only show balloon on meaningful transitions (not on every HEALTHY poll)
        if status == "RESTARTING" and prev != "RESTARTING":
            self.showMessage(
                "HESA — Service Restarting", f"⟳ {service_name.replace('_', ' ').title()} is restarting…", QSystemTrayIcon.Warning, 4000
            )
        elif status == "RECOVERING" and prev != "RECOVERING":
            self.showMessage(
                "HESA — Recovering", f"↻ {service_name.replace('_', ' ').title()} recovery in progress…", QSystemTrayIcon.Warning, 4000
            )
        elif status == "RECOVERED":
            self.showMessage(
                "HESA — Service Recovered", f"✓ {service_name.replace('_', ' ').title()} is back online.", QSystemTrayIcon.Information, 4000
            )
        elif status == "FAILED":
            self.showMessage(
                "HESA — Service Failed",
                f"✗ {service_name.replace('_', ' ').title()} failed permanently (max retries exceeded). HESA continues running.",
                QSystemTrayIcon.Critical,
                8000,
            )

    def _update_tray_appearance(self):
        """Recompute icon colour from the current health dict."""
        statuses = set(self.service_health.values())

        critical_failed = any(
            self.service_health.get(svc) in ("PERMANENTLY_FAILED", "FAILED", "DOWN")
            for svc in ["memory_engine", "knowledge_graph", "ai_router"]
        )
        any_restarting = any(s in ("RESTARTING", "RECOVERING") for s in statuses)
        any_failed = any(s in ("PERMANENTLY_FAILED", "FAILED") for s in statuses)

        if critical_failed:
            self.setIcon(self._get_colored_icon("red"))
            self.setToolTip("HESA — Critical service failed")
        elif any_failed:
            self.setIcon(self._get_colored_icon("orange"))
            self.setToolTip("HESA — One or more services failed")
        elif any_restarting:
            self.setIcon(self._get_colored_icon("yellow"))
            self.setToolTip("HESA — Service recovering…")
        else:
            self.setIcon(self._get_colored_icon("green"))
            self.setToolTip("HESA — All systems nominal")

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            log_lifecycle("TRAY_ACTIVATED", f"System tray icon activated (reason={reason})")
            self.sig_open_dashboard.emit()

    def _on_voice_toggle(self, checked):
        self.voice_enabled = checked
        self.voice_action.setText("Voice: ON" if checked else "Voice: OFF")
        self.sig_voice_toggle.emit(checked)

    def _on_exit_clicked(self):
        """
        Explicit user exit only — NEVER called automatically on service crashes.
        Asks user to choose Exit or Minimize.
        """
        log_lifecycle("TRAY_EXIT_CLICKED", "Tray context menu 'Exit HESA' option triggered")
        reply = QMessageBox.question(
            None,
            "Exit HESA",
            "Exit completely or minimize to tray?\n\n• Exit: Close all background services\n• Minimize: Keep running in system tray",
            QMessageBox.StandardButton.Close | QMessageBox.StandardButton.Minimize | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Minimize,
        )
        if reply == QMessageBox.StandardButton.Close:
            log_close_reason("tray_explicit_exit", "User explicitly chose Close/Exit from tray prompt")
            self.sig_exit_completely.emit()
        elif reply == QMessageBox.StandardButton.Minimize:
            log_lifecycle("tray_explicit_minimize", "User explicitly chose Minimize from tray prompt")
            if self.parent_widget:
                self.parent_widget.hide()
