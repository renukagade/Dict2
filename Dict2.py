import streamlit as st
import requests
import speech_recognition as sr
import pyttsx3
from googletrans import Translator
from streamlit_webrtc import webrtc_streamer, WebRtcMode, ClientSettings
import av
import time


BASE_URL = 'https://api.dictionaryapi.dev/api/v2/entries/en/'
if "webrtc_initialized" not in st.session_state:
    st.session_state["webrtc_initialized"] = False
    st.session_state["transcription"] = ""
    st.session_state["start_time"] = 0
    st.session_state["capture_duration"] = 10000  # Duration in seconds

# Function to process audio frames
def audio_processor_factory():
    recognizer = sr.Recognizer()

    def process_audio(frame: av.AudioFrame):
        current_time = time.time()
        if current_time - st.session_state["start_time"] > st.session_state["capture_duration"]:
            st.session_state["webrtc_initialized"] = False
            webrtc_ctx.stop()
            return

        audio = frame.to_ndarray()
        audio = audio.mean(axis=1)  # Convert stereo to mono
        sample_rate = frame.sample_rate

        # Convert numpy array to AudioData
        audio_data = sr.AudioData(audio.tobytes(), sample_rate, frame.format.bits_per_sample // 8)

        try:
            text = recognizer.recognize_google(audio_data)
            st.session_state["transcription"] = text
        except sr.UnknownValueError:
            st.session_state["transcription"] = "Could not understand audio"
        except sr.RequestError as e:
            st.session_state["transcription"] = f"Could not request results from Google Speech Recognition service; {e}"

    return process_audio
def get_word_data(word):
    url = f"{BASE_URL}{word}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]
        else:
            return None
    else:
        return None

def get_word_meaning(data):
    if 'meanings' in data:
        definitions = data['meanings'][0]['definitions']
        if definitions:
            return definitions[0]['definition']
    return "No definition found."

def get_part_of_speech(data):
    if 'meanings' in data:
        return data['meanings'][0]['partOfSpeech']
    return "Unknown"

def get_example_sentences(data):
    examples = []
    if 'meanings' in data:
        definitions = data['meanings'][0]['definitions']
        if definitions:
            for definition in definitions:
                if 'example' in definition:
                    examples.append(definition['example'])
    return examples

def get_synonyms_antonyms(data):
    synonyms = []
    antonyms = []
    if 'meanings' in data:
        definitions = data['meanings'][0]['definitions']
        if definitions:
            for definition in definitions:
                if 'synonyms' in definition:
                    synonyms.extend(definition['synonyms'])
                if 'antonyms' in definition:
                    antonyms.extend(definition['antonyms'])
    return synonyms, antonyms

def translate_text(text, dest_lang):
    translator = Translator()
    translation = translator.translate(text, dest=dest_lang)
    return translation.text

def recognize_speech(audio_data):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_data) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            st.write("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            st.write(f"Could not request results from Google Speech Recognition service; {e}")
        return ""

def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

class AudioProcessor:
    def __init__(self):
        self.frames = []

    def recv(self, frame):
        audio_frame = av.AudioFrame.from_ndarray(frame.to_ndarray(), format="s16")
        self.frames.append(audio_frame)
        return audio_frame

# Streamlit UI
st.title("Enhanced Multilingual Dictionary Bot")
st.write("Enter a word or use voice input to get its meaning.")

word = st.text_input("Enter a word:")

# Streamlit interface
if st.button("Use Voice Input") and not st.session_state["webrtc_initialized"]:
    st.session_state["webrtc_initialized"] = True
    st.session_state["start_time"] = time.time()  # Start time for capture
    st.write("hello");
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDRECV,
        client_settings=ClientSettings(
            #rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": False, "audio": True},
        ),
        audio_processor_factory=audio_processor_factory,
    )

# Display the transcription if available
if st.session_state["webrtc_initialized"]:
    st.write("Listening...")
    if st.session_state["transcription"]:
        st.write("You said: ", st.session_state["transcription"])
        
if word:
    word_data = get_word_data(word)
    if word_data:
        meaning = get_word_meaning(word_data)
        part_of_speech = get_part_of_speech(word_data)
        examples = get_example_sentences(word_data)
        synonyms, antonyms = get_synonyms_antonyms(word)

        st.write(f"Word: {word}")
        st.write(f"Part of Speech: {part_of_speech}")
        st.write(f"Meaning: {meaning}")

        if examples:
            st.write("Examples:")
            for example in examples:
                st.write(f"- {example}")

        if synonyms:
            st.write("Synonyms:")
            st.write(", ".join(synonyms))

        if antonyms:
            st.write("Antonyms:")
            st.write(", ".join(antonyms))

        dest_lang = st.selectbox("Translate to language:", ["es", "fr", "de", "zh-cn", "hi"])
        translated_meaning = translate_text(meaning, dest_lang)
        st.write(f"Translated Meaning: {translated_meaning}")
        
        if st.button("Speak Meaning"):
            speak_text(meaning)

        if st.button("Speak Translated Meaning"):
            speak_text(translated_meaning)

    else:
        st.write("No data found for the given word.")
