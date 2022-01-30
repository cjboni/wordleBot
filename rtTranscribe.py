import websockets
import asyncio
import base64
import json
import string
from pynput.keyboard import Key, Controller
import time
from configure import auth_key
import boto3
import playsound
import pyaudio
 
keyboard = Controller()

buffer = []

polly_client = boto3.Session(aws_access_key_id='AKIAXMKPYUNFS4LGCSEM', aws_secret_access_key='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', region_name='us-east-1').client('polly')

FRAMES_PER_BUFFER = 3200
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
p = pyaudio.PyAudio()
 
# starts recording
stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER
)   
 
# the AssemblyAI endpoint we're going to hit
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000&punctuate=False&format_text=False"
 
async def send_receive():

        print(f'Connecting websocket to url ${URL}')

        async with websockets.connect(
                URL,
                extra_headers=(("Authorization", auth_key),),
                ping_interval=5,
                ping_timeout=20
        ) as _ws:

                await asyncio.sleep(0.1)
                print("Receiving SessionBegins ...")

                session_begins = await _ws.recv()
                print(session_begins)
                print("Sending messages ...")


                async def send():
                        while True:
                                try:
                                        data = stream.read(FRAMES_PER_BUFFER)
                                        data = base64.b64encode(data).decode("utf-8")
                                        json_data = json.dumps({"audio_data":str(data)})    #sends raw audio file to .json
                                        await _ws.send(json_data)                           #sends .json to websocket

                                except websockets.exceptions.ConnectionClosedError as e:
                                        print(e)
                                        assert e.code == 4008
                                        break

                                except Exception as e:
                                        assert False, "Not a websocket 4008 error"

                                await asyncio.sleep(0.01)
                  
                        return True

                async def receive():
                        while True:
                                try:
                                        with open("test.txt", "a") as o:
                                                result_str = await _ws.recv()
                                                if json.loads(result_str)['message_type'] == "FinalTranscript":
                                                        array = (json.loads(result_str)['words'])
                                                        for i in range (len(array)):
                                                                #print(array[i]["text"])
                                                                if array[i]["text"] != "":
                                                                        buffer.append(array[i]["text"].lower().translate(str.maketrans("", "", string.punctuation)))
                                                                if buffer[-1] == "enter":
                                                                        keyboard.type(buffer[-2])
                                                                        mytext = buffer[-2]
                                                                        response = polly_client.synthesize_speech(VoiceId='Joanna',
                                                                                                                  OutputFormat='mp3',
                                                                                                                  Text = mytext,
                                                                                                                  Engine = 'neural')
                                                                        file = open('speech.mp3','wb')
                                                                        file.write(response['AudioStream'].read())
                                                                        file.close()
                                                                        playsound.playsound('speech.mp3')
                                                                        buffer.clear()
                                                                elif buffer[-1] == "stop":
                                                                        raise SystemExit
                                except websockets.exceptions.ConnectionClosedError as e:
                                        print(e)
                                        assert e.code == 4008
                                        break

                                except Exception as e:
                                        assert False, "Not a websocket 4008 error"

                send_result, receive_result = await asyncio.gather(send(), receive())
#keyboard.press(Key.cmd)
#keyboard.press(Key.tab)
#keyboard.release(Key.cmd)
#keyboard.release(Key.tab)
while True:
        asyncio.run(send_receive())
