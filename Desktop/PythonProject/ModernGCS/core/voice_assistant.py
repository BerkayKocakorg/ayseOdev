import threading
import queue

# Graceful fallback: if pyttsx3 is not installed, voice will be silent
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    print("[WARN] pyttsx3 not installed. Voice assistant disabled. Install with: pip install pyttsx3")


class VoiceAssistant:
    """
    Thread-safe text-to-speech voice assistant.
    
    V5.0 Improvements:
    - Graceful fallback if pyttsx3 is not installed
    - Priority queue: urgent alerts jump ahead of normal messages
    - Configurable enable/disable
    - New alert categories for safety system
    """
    # Priority levels (lower number = higher priority)
    PRIORITY_CRITICAL = 0   # Emergency: battery critical, signal lost
    PRIORITY_WARNING = 1    # Warning: geofence, altitude limit
    PRIORITY_INFO = 2       # Info: mode change, armed/disarmed
    
    def __init__(self):
        self.message_queue = queue.PriorityQueue()
        self.running = True
        self.enabled = True
        self._msg_counter = 0  # For stable sorting in PriorityQueue
        self._lock = threading.Lock()
        
        if _TTS_AVAILABLE:
            self.thread = threading.Thread(target=self._tts_loop, daemon=True)
            self.thread.start()
        else:
            self.thread = None

    def _tts_loop(self):
        try:
            # Initialize pyttsx3 within the thread that will run it
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)  # Speed of speech
            
            while self.running:
                try:
                    # Block until a message is available
                    priority, counter, msg = self.message_queue.get(timeout=0.5)
                    if self.enabled:
                        engine.say(msg)
                        engine.runAndWait()
                    self.message_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"TTS Error: {e}")
        except Exception as e:
            print(f"[WARN] TTS engine init failed: {e}")

    def say(self, message, priority=PRIORITY_INFO):
        """Add a message to the TTS queue to be spoken."""
        if not _TTS_AVAILABLE or not self.enabled:
            return
        with self._lock:
            self._msg_counter += 1
            self.message_queue.put((priority, self._msg_counter, message))

    def say_critical(self, message):
        """Speak an urgent/critical message (jumps queue)."""
        self.say(message, priority=self.PRIORITY_CRITICAL)
    
    def say_warning(self, message):
        """Speak a warning message."""
        self.say(message, priority=self.PRIORITY_WARNING)

    def set_enabled(self, enabled):
        """Enable or disable voice output."""
        self.enabled = enabled

    def stop(self):
        self.running = False
