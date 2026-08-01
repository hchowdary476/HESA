import sys
import os
import logging
import sounddevice as sd

logger = logging.getLogger("jarvis.pyaudio")

_real_pyaudio = None

# Try importing native pyaudio by bypassing our own directory in sys.path
our_path = os.path.abspath(__file__)
our_dir = os.path.dirname(our_path)
other_paths = [p for p in sys.path if os.path.abspath(p) != our_dir]

original_path = sys.path
try:
    sys.path = other_paths
    import importlib.util
    # Find spec for pyaudio
    spec = importlib.util.find_spec("pyaudio")
    if spec and spec.origin and os.path.abspath(spec.origin) != our_path:
        _real_pyaudio = importlib.import_module("pyaudio")
except Exception:
    pass
finally:
    sys.path = original_path

if _real_pyaudio is not None:
    logger.info("Native PyAudio backend active.")
    # Expose all variables from the real pyaudio module
    globals().update({k: v for k, v in _real_pyaudio.__dict__.items() if not k.startswith('__')})
else:
    logger.info("PyAudio compatibility wrapper active (using sounddevice backend).")

    # Define PyAudio format constants
    paInt8 = 1
    paInt16 = 2
    paInt24 = 3
    paInt32 = 4
    paFloat32 = 5

    def get_sample_size(format):
        if format == paInt8:
            return 1
        elif format == paInt16:
            return 2
        elif format == paInt24:
            return 3
        elif format == paInt32:
            return 4
        elif format == paFloat32:
            return 4
        return 2

    class Stream:
        def __init__(self, device_index, channels, rate, format, frames_per_buffer):
            self.device_index = device_index
            self.channels = channels
            self.rate = rate
            if format == paInt8:
                self.dtype = 'int8'
            elif format == paInt16:
                self.dtype = 'int16'
            elif format == paInt32:
                self.dtype = 'int32'
            elif format == paFloat32:
                self.dtype = 'float32'
            else:
                self.dtype = 'int16'
                
            self.stream = sd.RawInputStream(
                device=device_index,
                channels=channels,
                samplerate=rate,
                dtype=self.dtype,
                blocksize=frames_per_buffer
            )
            self.stream.start()

        def read(self, num_frames, exception_on_overflow=False):
            if self.stream is None:
                return b""
            data, overflowed = self.stream.read(num_frames)
            return bytes(data)

        def is_stopped(self):
            if self.stream is None:
                return True
            try:
                return self.stream.stopped
            except Exception:
                return True

        def close(self):
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

        def stop_stream(self):
            if self.stream:
                try:
                    self.stream.stop()
                except Exception:
                    pass

        def start_stream(self):
            if self.stream:
                try:
                    self.stream.start()
                except Exception:
                    pass

    class PyAudio:
        def __init__(self):
            pass

        def get_device_count(self):
            try:
                return len(sd.query_devices())
            except Exception:
                return 0

        def get_device_info_by_index(self, index):
            try:
                dev = sd.query_devices(index)
                return {
                    'index': index,
                    'name': dev.get('name'),
                    'maxInputChannels': dev.get('max_input_channels', 0),
                    'maxOutputChannels': dev.get('max_output_channels', 0),
                    'defaultSampleRate': dev.get('default_samplerate', 16000),
                }
            except Exception:
                return {}

        def get_default_input_device_info(self):
            try:
                default_idx = sd.default.device[0]
            except Exception:
                default_idx = -1
            if default_idx is None or default_idx < 0:
                try:
                    for idx, dev in enumerate(sd.query_devices()):
                        if dev.get('max_input_channels', 0) > 0:
                            default_idx = idx
                            break
                except Exception:
                    pass
            if default_idx is not None and default_idx >= 0:
                return self.get_device_info_by_index(default_idx)
            raise IOError("No default input device available")

        def open(self, *args, **kwargs):
            rate = kwargs.get('rate', 16000)
            channels = kwargs.get('channels', 1)
            format = kwargs.get('format', paInt16)
            input_device_index = kwargs.get('input_device_index', None)
            frames_per_buffer = kwargs.get('frames_per_buffer', 1024)
            return Stream(input_device_index, channels, rate, format, frames_per_buffer)

        def terminate(self):
            pass
