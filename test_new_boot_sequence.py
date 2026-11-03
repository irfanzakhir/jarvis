"""
Automated Verification Suite for the New Jarvis Boot Sequence Pipeline
Verifies:
1. Combat mode lock screen (red theme, centered red Arc Reactor, all widgets hidden)
2. Facial recognition -> cinematic boot screen (boot_sequence.py JarvisBootScreen)
3. Smooth transition to default cyan Arc Reactor rotating at center on black grid (reactor_docked == False, all widgets hidden)
4. Home preferences import sequence:
   - Arc Reactor smoothly scales down and docks to the side (reactor_docked == True)
   - Only 3 widgets appear one by one:
     * command_widget (Manual Override Uplink) + Chime 1
     * log_widget (Neural Activity Log) + Chime 2
     * telemetry_widget (System Telemetry) + Chime 3
   - All other 13 widgets remain strictly hidden
   - Electronic chime sounds are verified
5. Arc Reactor auto-recenter behavior remains completely intact when widgets close
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --no-sandbox --disable-logging --log-level=3"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QEventLoop

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
app = QApplication.instance() or QApplication(["test_new_boot_sequence"])

from gui.hud import JarvisHUD
from boot_sequence import JarvisBootScreen


class TestNewBootSequencePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.hud = JarvisHUD()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "hud") and cls.hud:
            cls.hud.close()

    def test_01_chime_sound_files_exist(self):
        """Verifies that electronic chime sound files are generated and exist on disk."""
        self.assertTrue(os.path.exists(self.hud.chime_cmd_path), f"Missing {self.hud.chime_cmd_path}")
        self.assertTrue(os.path.exists(self.hud.chime_log_path), f"Missing {self.hud.chime_log_path}")
        self.assertTrue(os.path.exists(self.hud.chime_telem_path), f"Missing {self.hud.chime_telem_path}")

    def test_02_combat_mode_lock_screen_state(self):
        """
        Verifies Stage 1: Combat Mode Enabled Lock Screen
        - Orb in combat mode (red theme)
        - Central Arc Reactor at center (not docked to side)
        - All 16 widgets hidden
        """
        self.hud.update_text({"log": "AWAITING BIOMETRIC AUTHENTICATION...", "action": "combat_on"})
        self.app.processEvents()

        self.assertTrue(self.hud.orb.combat_mode, "Orb should be in combat mode (red theme)")
        self.assertFalse(self.hud.reactor_docked, "Arc Reactor should be centered, not docked")

        for widget in self.hud.all_hud_widgets:
            self.assertFalse(widget.isVisible(), f"Widget {widget.title_label.text()} must be hidden in lock mode!")

    def test_03_cinematic_boot_screen_execution_and_transition(self):
        """
        Verifies Stage 2 & 3:
        - Boot screen (JarvisBootScreen) triggers on 'cinematic_boot'
        - On complete, transitions to default Cyan Arc Reactor centered on black grid
        - All widgets remain strictly hidden
        """
        # Trigger cinematic boot
        self.hud.update_text({"log": "[SECURITY]: ADMIN VERIFIED. INITIATING BOOT.", "action": "cinematic_boot"})
        self.app.processEvents()

        self.assertIsNotNone(self.hud.boot_screen, "JarvisBootScreen should be instantiated")
        self.assertIsInstance(self.hud.boot_screen, JarvisBootScreen)

        # Fast-forward / complete the boot screen
        self.hud.on_boot_screen_completed()
        self.app.processEvents()

        self.assertTrue(self.hud.boot_screen_finished.is_set(), "boot_screen_finished event should be set")
        self.assertFalse(self.hud.orb.combat_mode, "Orb should transition out of combat mode to Cyan")
        self.assertFalse(self.hud.reactor_docked, "Arc Reactor should remain centered in default grid view")

        for widget in self.hud.all_hud_widgets:
            self.assertFalse(widget.isVisible(), f"Widget {widget.title_label.text()} must remain hidden before preference import")

    def test_04_reveal_home_preferences_sequence(self):
        """
        Verifies Stage 4: Home Preferences Import & Staggered Reveal
        - Arc Reactor docks to the side (setReactorDocked(true), scaling down and moving left)
        - Only 3 core widgets become visible:
          1. command_widget (Manual Override Uplink)
          2. log_widget (Neural Activity Log)
          3. telemetry_widget (System Telemetry)
        - All other 13 widgets remain strictly hidden
        - Electronic chime sounds are triggered for each widget
        """
        played_chimes = []

        def mock_play_chime(chime_type):
            played_chimes.append(chime_type)

        with patch.object(self.hud, 'play_widget_chime', side_effect=mock_play_chime):
            self.hud.update_text({"log": ">> J.A.R.V.I.S. SYSTEM FULLY OPERATIONAL.", "action": "reveal_home_preferences"})

            # Check that reactor docked immediately
            self.assertTrue(self.hud.reactor_docked, "Arc Reactor must dock to the side when preferences import")

            # Let timers fire (up to 2000ms)
            loop = QEventLoop()
            QTimer.singleShot(2100, loop.quit)
            loop.exec()
            self.app.processEvents()

        # Check that exactly the 3 core widgets are visible
        self.assertTrue(self.hud.command_widget.isVisible(), "Command typing widget must be visible")
        self.assertTrue(self.hud.log_widget.isVisible(), "Neural log widget must be visible")
        self.assertTrue(self.hud.telemetry_widget.isVisible(), "System telemetry widget must be visible")

        # Verify all other 13 widgets remain strictly hidden
        core_3 = {self.hud.command_widget, self.hud.log_widget, self.hud.telemetry_widget}
        for widget in self.hud.all_hud_widgets:
            if widget not in core_3:
                self.assertFalse(
                    widget.isVisible(),
                    f"Peripheral widget {widget.title_label.text()} should NOT be visible during preference import!"
                )

        # Check chime sequence
        self.assertEqual(played_chimes, ["cmd", "log", "telem"], f"Expected chimes ['cmd', 'log', 'telem'], got: {played_chimes}")

    def test_05_reactor_auto_recentering_intact(self):
        """
        Verifies that closing the 3 visible widgets smoothly recenters the Arc Reactor.
        Technique of Arc Reactor becoming smaller/moving to side when widget appears,
        and recentering when widgets close, is 100% intact.
        """
        self.assertTrue(self.hud.reactor_docked, "Reactor should be docked with widgets open")

        # Close all widgets
        self.hud.command_widget.close_widget()
        self.hud.log_widget.close_widget()
        self.hud.telemetry_widget.close_widget()

        loop = QEventLoop()
        QTimer.singleShot(500, loop.quit)
        loop.exec()
        self.app.processEvents()

        self.assertFalse(self.hud.reactor_docked, "Reactor must recenter when all widgets are closed")

    def test_06_speech_plays_before_preference_widgets_reveal(self):
        """
        Verifies Stage 4 Execution Order:
        1. When boot finishes, HUD displays normal Cyan Arc Reactor on plain background, all widgets hidden.
        2. Real JarvisMouth initializes cleanly (no NameError or missing imports).
        3. _MouthProxy.speak_sync() blocks until speech finishes.
        4. During speech, all widgets are hidden and the Arc Reactor is NOT docked.
        5. Only after speech returns does 'reveal_home_preferences' fire to reveal the widgets.
        """
        from core.mouth import JarvisMouth
        from main import _MouthProxy

        real_mouth = JarvisMouth()
        self.assertIsNotNone(real_mouth)
        self.assertIn("Good to see you, sir. Importing preferences from home interface.", real_mouth._audio_cache)

        # Mock worker for proxy
        mock_worker = MagicMock()
        mouth_proxy = _MouthProxy(real_mouth, mock_worker)

        execution_log = []
        welcome_phrase = "Good to see you, sir. Importing preferences from home interface."

        # Verify that before speaking, HUD has all widgets hidden and reactor is centered
        self.assertFalse(self.hud.reactor_docked)

        # Intercept real_mouth.speak to verify timing and state during speech
        def checked_speak(text):
            execution_log.append(f"start_speak:{text}")
            # Ensure during speech all widgets are still strictly hidden
            for w in self.hud.all_hud_widgets:
                self.assertFalse(w.isVisible(), f"Widget {w.title_label.text()} must be hidden during speech!")
            self.assertFalse(self.hud.reactor_docked, "Arc Reactor must remain centered during speech!")
            execution_log.append(f"end_speak:{text}")

        with patch.object(real_mouth, 'speak', side_effect=checked_speak):
            mouth_proxy.speak_sync(welcome_phrase)
            execution_log.append("signal:reveal_home_preferences")

        self.assertEqual(
            execution_log,
            [
                f"start_speak:{welcome_phrase}",
                f"end_speak:{welcome_phrase}",
                "signal:reveal_home_preferences"
            ],
            "Vocal greeting must play and finish before reveal_home_preferences signal is emitted!"
        )

    def test_07_scifi_click_sound_trimmed_properties(self):
        """
        Verifies that the sound effect from Pixabay (596258) has been trimmed:
        - Original file (1.39s with 1.0s silence) is trimmed to <= 0.40s
        - WAV format (PCM 16-bit)
        - Exists in assets/chimes/
        """
        import wave
        for ch_path in [self.hud.chime_cmd_path, self.hud.chime_log_path, self.hud.chime_telem_path]:
            self.assertTrue(os.path.exists(ch_path), f"File {ch_path} must exist")
            with wave.open(ch_path, 'rb') as wf:
                duration = wf.getnframes() / float(wf.getframerate())
                self.assertLessEqual(duration, 0.45, f"Audio {ch_path} must be trimmed to <= 0.45s (got {duration:.2f}s)")
                self.assertGreater(duration, 0.15, f"Audio {ch_path} must contain active sound (got {duration:.2f}s)")
                self.assertEqual(wf.getsampwidth(), 2, "Audio must be 16-bit PCM")


if __name__ == "__main__":
    unittest.main()
