import base64
import os
import json

from flask import Flask, request, Response
from flask_sock import Sock
import ngrok 
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

from twilio_transcriber import TwilioTranscriber

# Flask settings
PORT = 5000
DEBUG = False
INCOMING_CALL_ROUTE = '/'
WEBSOCKET_ROUTE = '/realtime'

# Twilio authentication
account_sid = os.environ['TWILIO_ACCOUNT_SID']
api_key = os.environ['TWILIO_API_KEY_SID']
api_secret = os.environ['TWILIO_API_SECRET']
auth_token = os.environ['TWILIO_AUTHTOKEN']
client = Client(account_sid, auth_token)

# Twilio phone number to call
TWILIO_NUMBER = os.environ['TWILIO_NUMBER']

# ngrok authentication
ngrok.set_auth_token(os.getenv("NGROK_AUTHTOKEN")) # type: ignore
app = Flask(__name__)
sock = Sock(app)

# TwilioTranscriber instance
@app.route(INCOMING_CALL_ROUTE, methods=['GET','POST'])
def receive_call():
    if request.method == 'POST':
        xml = f"""
            <Response>
                <Say>
                    Speak to see your speech transcribed in the console
                </Say>
                <Connect>
                    <Stream url='wss://0e91-89-208-59-165.ngrok-free.app/{WEBSOCKET_ROUTE}' />
                </Connect>
            </Response>
            """.strip()
        return Response(xml, mimetype='text/xml')
    else:
        return f"Real-time phone call transcription app"
    

@sock.route(WEBSOCKET_ROUTE)
def transcription_websocket(ws):
    print(">>> WebSocket connection established with Twilio!")
    while True:
        # Read the message from Twilio
        msg = ws.receive()
        if not msg:
            break

        data = json.loads(msg)

        match data['event']:
            case 'connected':
                transcriber = TwilioTranscriber()
                transcriber.connect()
                print('Connected to Twilio')

            case 'start':
                print('Transcription started')

            case 'media':
                payload_b64 = data['media']['payload']
                payload_mulaw = base64.b64decode(payload_b64)
                transcriber.stream(payload_mulaw) # type: ignore

            case 'stop':
                print('Transcription stopped')
                transcriber.close() # type: ignore
                print('Connection closed')
                break

if __name__ == '__main__':
    try:
        # Open Ngrok tunnel
        listener = ngrok.forward(f'http://localhost:{PORT}')
        print(f'Listening at {listener.url()} for port {PORT}')
        NGROK_URL = listener.url()

        # Set Ngrok URL to the webhook for the Twilio Number
        twilio_numbers = client.incoming_phone_numbers.list() # type: ignore
        twilio_number_sid = [num.sid for num in twilio_numbers if num.phone_number == TWILIO_NUMBER][0]
        #client.incoming_phone_numbers(twilio_number_sid).update(account_sid, voice_url=f'{NGROK_URL}{INCOMING_CALL_ROUTE}') # type: ignore
        client.incoming_phone_numbers(
            "PNada5ddc9451efdb70268dc406b694c49"
        ).update(voice_url="https://0e91-89-208-59-165.ngrok-free.app")




        # incoming_phone_numbers = client.incoming_phone_numbers(
        #     "PNada5ddc9451efdb70268dc406b694c49"
        # ).fetch()
        # print(incoming_phone_numbers.account_sid)
        ###
        # Start Flask app
        app.run(port=PORT, debug=DEBUG)
    finally:
        ngrok.disconnect()