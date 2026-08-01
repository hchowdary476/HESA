import speech_recognition as sr
import traceback

def main():
    r = sr.Recognizer()
    # 1 second of silence
    audio = sr.AudioData(b'\x00' * 32000, 16000, 2)
    print("Sending mock audio to recognize_google...")
    try:
        r.recognize_google(audio)
    except Exception as e:
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
