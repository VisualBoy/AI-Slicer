import google.genai as genai # Changed to google.genai
from google.genai import types # Changed to google.genai
import os
import pyaudio
import asyncio # Added asyncio
import typing # Added typing

# Configure the Gemini client
# Ensure API key is configured in the environment.
# Example: genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# The user will need to ensure the API key is set in their .env file or environment.
# We assume genai.configure() will be called elsewhere or API key is globally set.

# As per LiveAPI example, using a client with http_options for v1beta
try:
    client = genai.Client(http_options={"api_version": "v1beta"})
except Exception as e:
    print(f"Error initializing GenAI Client: {e}. Ensure GEMINI_API_KEY is set.")
    # Potentially raise the error or handle it as per application's needs
    # For now, printing and allowing it to proceed, but session creation will likely fail.
    client = None

MODEL_NAME = "models/gemini-1.5-flash-latest" # Or "gemini-1.5-pro-latest" or other suitable model

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO", "TEXT"],  # Expect both audio and text responses
    media_resolution="MEDIA_RESOLUTION_MEDIUM", # Or as needed
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr") # Or other preferred voice
        )
    ),
    # Example of context window compression (optional, include if needed)
    # context_window_compression_config=types.ContextWindowCompressionConfig(
    #     enabled=True,
    #     max_tokens_for_compression=2048 # Adjust as needed
    # )
)

# PyAudio constants (from example, adjust if necessary)
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000  # For microphone input
RECEIVE_SAMPLE_RATE = 24000 # For Gemini's audio output (typically 24kHz for Gemini TTS)
CHUNK_SIZE = 1024 # Common chunk size

# Placeholder for API key configuration note
# print("Note: Ensure GEMINI_API_KEY is set in your environment variables for live_client.py to function correctly.")

async def listen_send_audio(session: typing.Any, audio_interface: pyaudio.PyAudio, stop_event: asyncio.Event): # Changed types.LiveSession to typing.Any
    """Opens microphone, reads audio, and sends it to the Gemini LiveSession."""
    print("Starting to listen and send audio...")
    input_stream = None
    try:
        input_stream = audio_interface.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        print("Microphone stream opened.")
        while not stop_event.is_set():
            try:
                data = input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                # print(f"Read {len(data)} bytes from microphone.") # Debug print
                # session.send_request(audio=data) # Old method
                session.send_realtime_input(audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}")) # New method
            except IOError as e:
                print(f"Error reading from microphone: {e}")
                # Potentially add a small delay or break if errors are persistent
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Error sending audio request: {e}")
                break
        print("Stop event received, closing microphone stream.")
    except Exception as e:
        print(f"Error in listen_send_audio: {e}")
    finally:
        if input_stream:
            input_stream.stop_stream()
            input_stream.close()
            print("Microphone stream closed.")
    print("Listen and send audio finished.")

async def receive_audio_stream(session: typing.Any, audio_queue: asyncio.Queue, text_handler_fn: callable, stop_event: asyncio.Event): # Changed types.LiveSession to typing.Any
    """Receives audio and text responses from the Gemini LiveSession."""
    print("Starting to receive audio/text stream...")
    try:
        async for response_part in session.receive(): # Changed from session.responses()
            if stop_event.is_set():
                print("Stop event received during response iteration.")
                break
            if response_part.audio:
                # print(f"Received audio chunk, putting in queue.") # Debug print
                await audio_queue.put(response_part.audio)
            if response_part.text:
                text_handler_fn(response_part.text)
            # Add handling for other response types if necessary, e.g., errors, session status
            if response_part.error:
                print(f"Received error from session: {response_part.error}")
                stop_event.set() # Stop processing on error
                break
            if response_part.session_status:
                 print(f"Session status update: {response_part.session_status}")
                 if response_part.session_status.session_closed or \
                    response_part.session_status.session_done or \
                    response_part.session_status.session_error:
                    print("Session ended by server.")
                    stop_event.set()
                    break

    except Exception as e:
        print(f"Error in receive_audio_stream: {e}")
        stop_event.set() # Ensure other tasks stop if this one errors out
    finally:
        print("Receive audio stream finished.")
        if not stop_event.is_set(): # If loop exited without stop_event, set it
            stop_event.set()


async def play_audio_stream(audio_interface: pyaudio.PyAudio, audio_queue: asyncio.Queue, stop_event: asyncio.Event):
    """Plays audio from the queue using PyAudio."""
    print("Starting to play audio stream...")
    output_stream = None
    try:
        output_stream = audio_interface.open(
            format=FORMAT, # Assuming output format is same as input for simplicity, adjust if needed
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE, # Use Gemini's typical output rate
            output=True
        )
        print("Audio output stream opened.")
        while not stop_event.is_set() or not audio_queue.empty(): # Continue if stop_event is set but queue has items
            try:
                # Wait for audio data with a timeout to allow checking stop_event
                audio_data = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                output_stream.write(audio_data)
                # print(f"Played audio chunk of size {len(audio_data)}.") # Debug print
                audio_queue.task_done()
            except asyncio.TimeoutError:
                # This is normal, just means no audio in queue currently
                if stop_event.is_set() and audio_queue.empty(): # If stop is set and queue is empty, break
                    break
                continue
            except Exception as e:
                print(f"Error playing audio: {e}")
                # Potentially break or handle differently based on error type
                await asyncio.sleep(0.1)
        print("Stop event received or queue empty, closing audio output stream.")
    except Exception as e:
        print(f"Error in play_audio_stream: {e}")
    finally:
        if output_stream:
            output_stream.stop_stream()
            output_stream.close()
            print("Audio output stream closed.")
    print("Play audio stream finished.")

def default_text_handler(text: str):
    """Default handler for printing received text."""
    print(f"Received text: {text}")

async def main_test():
    """Basic test for the new audio functions."""
    print("Running main_test for audio functions...")
    p_audio = pyaudio.PyAudio()
    audio_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    # These functions would normally be started with a real session object.
    # Here, we're just checking if they can be called and run for a short duration.
    # We'll mock the session for the purpose of this test.

    class MockLiveSession:
        async def receive(self): # Changed from responses to receive
            # Simulate receiving a few messages then stopping
            for i in range(3):
                if stop_event.is_set(): break
                print(f"MockSession: Yielding mock response {i}")
                await asyncio.sleep(0.2)
                # yield types.LiveResponse(audio=b'\x00\x00' * CHUNK_SIZE, text=f"Mock text {i}") # This needs actual LiveResponse structure
                # For simplicity, let's assume types.LiveResponse can be constructed like this or similar
                # Actual LiveResponse might be more complex or require specific factory methods
                # This part is tricky to mock without the exact LiveResponse structure details from SDK
                # Let's focus on the flow and assume response_part.audio and .text exist
                class MockResponsePart:
                    def __init__(self, audio, text, error=None, session_status=None):
                        self.audio = audio
                        self.text = text
                        self.error = error
                        self.session_status = session_status

                if i == 0: yield MockResponsePart(audio=b'\x00\x01' * (CHUNK_SIZE // 2), text=None) # Send some audio
                if i == 1: yield MockResponsePart(audio=None, text=f"Hello from mock session {i}") # Send some text
                if i == 2:
                    # Simulate session ending
                    class MockSessionStatus:
                        def __init__(self, session_closed=False, session_done=False, session_error=None):
                            self.session_closed = session_closed
                            self.session_done = session_done
                            self.session_error = session_error
                    yield MockResponsePart(audio=None, text=None, session_status=MockSessionStatus(session_done=True))


            print("MockSession: Response loop finished.")

        def send_realtime_input(self, audio): # Changed from send_request
            # print(f"MockSession: Received audio data of length {len(audio.data)}") # audio is now a types.Blob
            pass # No-op for mock

        def close(self):
            print("MockSession: close() called")


    mock_session = MockLiveSession()

    print("Creating tasks...")
    # Create tasks for listening, receiving, and playing
    # listen_task = asyncio.create_task(listen_send_audio(mock_session, p_audio, stop_event)) # Needs microphone
    receive_task = asyncio.create_task(receive_audio_stream(mock_session, audio_queue, default_text_handler, stop_event))
    play_task = asyncio.create_task(play_audio_stream(p_audio, audio_queue, stop_event))

    # Let them run for a short period
    await asyncio.sleep(2)
    print("\nSetting stop event in main_test...\n")
    if not stop_event.is_set(): # Check if not already set by e.g. receive_audio_stream
        stop_event.set()

    # Wait for tasks to complete
    print("Waiting for tasks to complete...")
    # await asyncio.gather(listen_task, receive_task, play_task, return_exceptions=True)
    # Not running listen_task as it requires a microphone and could block CI/testing.
    # Also, gather might wait indefinitely if tasks don't respect stop_event quickly enough or get stuck.
    # A timeout on gather or individual awaits might be needed in a real app.

    # Instead of gather, let's await them individually with a timeout to be safe
    try:
        await asyncio.wait_for(receive_task, timeout=5.0)
    except asyncio.TimeoutError:
        print("Receive task timed out.")
    try:
        await asyncio.wait_for(play_task, timeout=5.0) # play_task depends on audio_queue
    except asyncio.TimeoutError:
        print("Play task timed out.")
    # try:
    #     await asyncio.wait_for(listen_task, timeout=5.0)
    # except asyncio.TimeoutError:
    #     print("Listen task timed out.")


    print("Cleaning up PyAudio in main_test.")
    p_audio.terminate()
    print("main_test finished.")


if __name__ == '__main__':
    # Basic test to ensure the file is created and constants are accessible
    print("live_client.py created and constants defined.")
    if client:
        print(f"GenAI Client initialized: {client}")
    else:
        print("GenAI Client failed to initialize. Check API key and configurations.")
    print(f"Model Name: {MODEL_NAME}")
    print(f"Live Config: {LIVE_CONFIG}") # This is already a string representation
    print(f"PyAudio Format: {FORMAT}")
    print(f"PyAudio Send Sample Rate: {SEND_SAMPLE_RATE}")
    print(f"PyAudio Receive Sample Rate: {RECEIVE_SAMPLE_RATE}")

    # Run the async test function
    # This will only run if the script is executed directly.
    # Note: Full functionality of these audio streams requires a live Gemini session.
    # The main_test provides a basic simulation.
    try:
        asyncio.run(main_test())
    except Exception as e:
        print(f"Error running main_test: {e}")
