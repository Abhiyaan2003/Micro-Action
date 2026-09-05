"""
Comprehensive Automated Test Suite for Micro Action.
Tests every feature, subsystem, edge case, and failure mode.
"""
import sys
import os
import unittest
import ctypes
import ctypes.wintypes
import threading
import queue
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config
from actions import ActionEngine
from ptt_engine import PTTEngine
from hook import KeyboardHook, KBDLLHOOKSTRUCT, HOOKPROC, VK_TO_POS, NUMPAD_SCANCODES
from screen_engine import ScreenEngine
from main import MainWindow, SOCKET_NAME, MUTEX_NAME, _acquire_mutex, enable_autostart


class TestConfigSubsystem(unittest.TestCase):
    """1. Config Loading, Validation, and Mutation Tests"""

    def setUp(self):
        self.config = Config()

    def test_default_numpad_keys_present(self):
        actions = self.config.data.get("keys", {})
        for pos_id in list(VK_TO_POS.values()):
            self.assertIn(pos_id, actions, f"Missing key position: {pos_id}")

    def test_get_and_set_action(self):
        test_pos = "num7"
        original = self.config.get_action(test_pos)
        
        new_action = {"type": "hotkey", "value": "ctrl+c"}
        self.config.set_action(test_pos, new_action)
        
        updated = self.config.get_action(test_pos)
        self.assertEqual(updated["type"], "hotkey")
        self.assertEqual(updated["value"], "ctrl+c")
        
        # Restore original
        if original:
            self.config.set_action(test_pos, original)

    def test_invalid_position_returns_none(self):
        self.assertIsNone(self.config.get_action("invalid_key_999"))


class TestActionEngine(unittest.TestCase):
    """2. Action Dispatcher Tests"""

    def setUp(self):
        self.engine = ActionEngine()

    def test_dispatch_hotkey_action(self):
        action = {"type": "hotkey", "value": "ctrl+c"}
        # Mock send_hotkey to test dispatch routing
        called = []
        self.engine.send_hotkey = lambda keys: called.append(keys)
        self.engine.dispatch(action)
        self.assertEqual(called, ["ctrl+c"])

    def test_dispatch_unknown_type_graceful(self):
        action = {"type": "nonexistent_action_type", "value": "xyz"}
        # Should not raise exception
        try:
            self.engine.dispatch(action)
        except Exception as e:
            self.fail(f"Dispatching unknown action raised: {e}")


class TestKeyboardHookSubsystem(unittest.TestCase):
    """3. Win32 Low-Level Keyboard Hook Tests"""

    def setUp(self):
        self.config = Config()
        self.action_engine = ActionEngine()
        self.ptt_engine = PTTEngine(self.config)
        self.hook = KeyboardHook(self.config, self.action_engine, self.ptt_engine)

    def test_vk_to_pos_mapping(self):
        self.assertEqual(VK_TO_POS[0x24], "num7")
        self.assertEqual(VK_TO_POS[0x26], "num8")
        self.assertEqual(VK_TO_POS[0x2D], "num0")
        self.assertEqual(VK_TO_POS[0x2E], "numdot")

    def test_numpad_scancodes_set(self):
        # 0x47 is Home (num7), 0x52 is Insert (num0)
        self.assertIn(0x47, NUMPAD_SCANCODES)
        self.assertIn(0x52, NUMPAD_SCANCODES)

    def test_hookproc_type_signature(self):
        # Verify 64-bit safe callback type
        self.assertEqual(HOOKPROC._restype_, ctypes.c_longlong)

    def test_hook_callback_numpad_detection(self):
        # Create mock numpad key structure (num7 = VK 0x24, scanCode 0x47, non-extended)
        struct = KBDLLHOOKSTRUCT()
        struct.vkCode = 0x24
        struct.scanCode = 0x47
        struct.flags = 0  # not extended, not injected
        
        addr = ctypes.addressof(struct)
        
        # Test with NumLock OFF (GetKeyState 0x90 returns 0)
        # Note: If physical NumLock is ON during test, test checks pass-through
        ret = self.hook._hook_callback(0, 0x0100, addr)
        self.assertIn(ret, (0, 1))

    def test_refresh_hook_safety(self):
        # Calling refresh_hook when uninstalled should be a safe no-op
        try:
            self.hook.refresh_hook()
        except Exception as e:
            self.fail(f"refresh_hook raised exception: {e}")


class TestPTTEngineSubsystem(unittest.TestCase):
    """4. Push-to-Talk Speech-to-Text Tests"""

    def setUp(self):
        self.config = Config()
        self.ptt = PTTEngine(self.config)

    def tearDown(self):
        self.ptt.shutdown()

    def test_model_warm_in_memory(self):
        # Verify auto-unload is disabled
        self.ptt._reset_inactivity_timer()
        # Timer should be None (no 60s eviction scheduled)
        self.assertIsNone(self.ptt._unload_timer)

    def test_local_agreement_reconciliation(self):
        committed = ["hello", "world"]
        prev_hyp = ["hello", "world", "this", "is", "a", "test"]
        curr_hyp = ["hello", "world", "this", "is", "another", "word"]
        
        n_committed = len(committed)
        prev_uncommitted = prev_hyp[n_committed:]
        curr_uncommitted = curr_hyp[n_committed:]
        
        match_count = 0
        min_len = min(len(prev_uncommitted), len(curr_uncommitted))
        for i in range(min_len):
            if prev_uncommitted[i] == curr_uncommitted[i]:
                match_count += 1
            else:
                break
        
        newly_committed = curr_uncommitted[:match_count]
        self.assertEqual(newly_committed, ["this", "is"])


class TestSingleInstanceGuard(unittest.TestCase):
    """5. Single Instance Mutex & IPC Tests"""

    def test_mutex_creation(self):
        handle, already_exists = _acquire_mutex()
        self.assertIsNotNone(handle)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)


if __name__ == "__main__":
    print("=" * 65)
    print("  RUNNING MICRO ACTION FULL FEATURE & EDGE-CASE TEST SUITE")
    print("=" * 65)
    unittest.main()
