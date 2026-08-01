import unittest
import time
from JARVIS.gui.ui_avatar import JarvisAvatar

class MockCanvas:
    def __init__(self):
        self.items = {}
        self.next_id = 1
        
    def create_oval(self, *args, **kwargs):
        item_id = self.next_id
        self.next_id += 1
        self.items[item_id] = {"type": "oval", "coords": args, "opts": kwargs}
        return item_id
        
    def create_polygon(self, *args, **kwargs):
        item_id = self.next_id
        self.next_id += 1
        self.items[item_id] = {"type": "polygon", "coords": args, "opts": kwargs}
        return item_id
        
    def create_line(self, *args, **kwargs):
        item_id = self.next_id
        self.next_id += 1
        self.items[item_id] = {"type": "line", "coords": args, "opts": kwargs}
        return item_id
        
    def create_arc(self, *args, **kwargs):
        item_id = self.next_id
        self.next_id += 1
        self.items[item_id] = {"type": "arc", "coords": args, "opts": kwargs}
        return item_id
        
    def coords(self, item_id, *args):
        if item_id in self.items:
            self.items[item_id]["coords"] = args
            
    def itemconfig(self, item_id, **kwargs):
        if item_id in self.items:
            self.items[item_id]["opts"].update(kwargs)
            
    def delete(self, item_id):
        if item_id == "all":
            self.items.clear()
        elif item_id in self.items:
            del self.items[item_id]
            
    def winfo_toplevel(self):
        return self

    def winfo_width(self):
        return 600
        
    def winfo_height(self):
        return 600
        
    def winfo_exists(self):
        return True
        
    def after(self, ms, func, *args):
        pass


class TestJarvisAvatar(unittest.TestCase):
    def setUp(self):
        self.canvas = MockCanvas()
        self.avatar = JarvisAvatar(self.canvas)

    def tearDown(self):
        self.avatar.stop()

    def test_initial_state_is_standby(self):
        self.assertEqual(self.avatar.state, "STANDBY")
        self.assertEqual(self.avatar.breathing_rate, 1.5)
        self.assertTrue(self.avatar.is_alive)

    def test_state_transitions(self):
        self.avatar.set_state("LISTENING")
        self.assertEqual(self.avatar.state, "LISTENING")
        
        self.avatar.set_state("PROCESSING")
        self.assertEqual(self.avatar.state, "PROCESSING")
        self.assertEqual(self.avatar.breathing_rate, 3.5)
        
        self.avatar.set_state("EXECUTING")
        self.assertEqual(self.avatar.state, "EXECUTING")
        self.assertEqual(self.avatar.breathing_rate, 4.0)

    def test_phoneme_mouth_mapping(self):
        # Vowels
        w, h = self.avatar._get_phoneme_mouth_shape('a')
        self.assertEqual((w, h), (35.0, 25.0))
        
        w, h = self.avatar._get_phoneme_mouth_shape('o')
        self.assertEqual((w, h), (26.0, 26.0))
        
        w, h = self.avatar._get_phoneme_mouth_shape('m')
        self.assertEqual((w, h), (28.0, 0.5))
        
        w, h = self.avatar._get_phoneme_mouth_shape('f')
        self.assertEqual((w, h), (30.0, 3.5))
        
        # Punctuation/rest
        w, h = self.avatar._get_phoneme_mouth_shape(' ')
        self.assertEqual((w, h), (30.0, 1.0))
        
        # Consonant fallback
        w, h = self.avatar._get_phoneme_mouth_shape('x')
        self.assertEqual((w, h), (34.0, 8.0))

    def test_speaking_updates_text_and_state(self):
        self.avatar.set_speaking_text("Hello Jarvis")
        self.assertEqual(self.avatar.speaking_text, "Hello Jarvis")
        self.assertEqual(self.avatar.state, "SPEAKING")
        self.assertGreater(self.avatar.speech_start_time, 0)

    def test_blinking_state_transitions(self):
        self.assertEqual(self.avatar.blink_state, "open")
        self.assertEqual(self.avatar.eyelids_scale, 1.0)
        
        # Force blink
        self.avatar.blink_timer = 0.0
        self.avatar._update_blinking(0.01)
        self.assertEqual(self.avatar.blink_state, "closing")
        
        # Progress closing
        self.avatar._update_blinking(0.06)
        self.assertAlmostEqual(self.avatar.eyelids_scale, 0.5, places=2)
        
        # Close completely
        self.avatar._update_blinking(0.06)
        self.assertEqual(self.avatar.blink_state, "closed")
        self.assertEqual(self.avatar.eyelids_scale, 0.0)

    def test_tick_execution_updates_coordinates(self):
        # Run tick to make sure no exceptions are raised
        initial_phase1 = self.avatar.ring_phase_1
        time.sleep(0.01)
        self.avatar.tick()
        # Verify that animation state advances
        self.assertNotEqual(self.avatar.ring_phase_1, initial_phase1)
        
    def test_stop_cancels_ticks(self):
        self.avatar.stop()
        self.assertFalse(self.avatar.is_alive)


if __name__ == "__main__":
    unittest.main()
