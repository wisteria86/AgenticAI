import speech_recognition as sr
import subprocess
import os
import tempfile
import asyncio
import edge_tts

def listen() -> str:
    """
    Listens to the microphone and transcribes the speech to text using local Whisper.
    """
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[Voice] Adjusting for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[Voice] Listening... Speak now!")
        
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            print("[Voice] Processing audio with Whisper...")
            
            # Using the local whisper model built into speech_recognition
            text = recognizer.recognize_whisper(audio, model="base", language="english")
            print(f"[Voice] You said: {text}")
            return text
        except sr.WaitTimeoutError:
            print("[Voice] No speech detected within timeout.")
            return ""
        except sr.UnknownValueError:
            print("[Voice] Whisper could not understand the audio.")
            return ""
        except Exception as e:
            print(f"[Voice] Error during speech recognition: {e}")
            return ""

async def _speak_async(text: str, voice: str = "en-US-AriaNeural"):
    """Async generator to create audio file using edge-tts"""
    communicate = edge_tts.Communicate(text, voice)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    
    await communicate.save(temp_file.name)
    return temp_file.name

def speak(text: str):
    """
    Converts text to speech using Microsoft Edge TTS and plays it.
    """
    print(f"[Agent Speaking]: {text}")
    try:
        mp3_file = asyncio.run(_speak_async(text))
        
        # On Windows, use PowerShell to play mp3 invisibly without popping up a GUI
        ps_script = f'''
        $player = New-Object -ComObject WMPlayer.OCX
        $player.URL = "{mp3_file}"
        $player.controls.play()
        Start-Sleep -Milliseconds 500
        while ($player.playState -eq 3) {{ Start-Sleep -Milliseconds 100 }}
        '''
        
        subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
        
        # Cleanup
        if os.path.exists(mp3_file):
            try:
                os.remove(mp3_file)
            except:
                pass
            
    except Exception as e:
        print(f"[Voice Error] Could not play TTS: {e}")
