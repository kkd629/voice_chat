from __future__ import division

from socket import *
import threading
import pyaudio
import re
import sys
import speech_recognition as sr
import queue
import pygame
import time

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from gtts import gTTS
import pyaudio
from six.moves import queue

import requests
from bs4 import BeautifulSoup

index = 0
api_key = 'RGAPI-3b089c7f-769d-4c84-b780-8ee0b3d0d937'
summoner_name = '신재필'
s_path = 'C:\\Users\\user\\speech\\'


import os
credential_path = 'C:\\Users\\user\\speech\\stt.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path


FORMAT = pyaudio.paInt16
CHANNELS = 2
CHUNK = 1024
RATE = 44100

#소켓 통신
def receive_audio(conn, stream, chunk):
    while True:
        try:
            data = conn.recv(1024)
            stream.write(data)
        except:
            conn.close()
    conn.close()
    pass

def send_audio(conn, stream, chunk):
    while True:
        try:
            data = stream.read(chunk)
            conn.send(data)
        except:
            conn.close()
    conn.close()
    pass

def stt(conn, stream, chunk):
	FORMAT = pyaudio.paInt16
	CHANNELS = 2
	CHUNK = 1024
	RATE = 44100
	#구글 클라우드 스피치
	# See http://g.co/cloud/speech/docs/languages
    	# for a list of supported languages.
	language_code = 'ko-KR'  # a BCP-47 language tag

	client = speech.SpeechClient()
	config = types.RecognitionConfig(
		encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
		sample_rate_hertz=RATE,
		language_code=language_code)
	streaming_config = types.StreamingRecognitionConfig(
		config=config,
		interim_results=True)

	with MicrophoneStream(RATE, CHUNK) as stream:
		audio_generator = stream.generator()
		requests = (types.StreamingRecognizeRequest(audio_content=content)
			for content in audio_generator)

		responses = client.streaming_recognize(streaming_config, requests)

		# Now, put the transcription responses to use.
		listen_print_loop(responses)

def playmusic(soundfile):
    """Stream music with mixer.music module in blocking manner.
       This will stream the sound from disk while playing.
    """
    pygame.init()
    pygame.mixer.init()
    clock= pygame.time.Clock()
    pygame.mixer.music.load(soundfile)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        print("결과 출력중!!")
        time.sleep(1)
        clock.tick(1000)

def getmixerargs():
    pygame.mixer.init()
    freq, size, chan = pygame.mixer.get_init()
    return freq, size, chan


def initMixer():
   BUFFER = 3072  # audio buffer size, number of samples since pygame 1.8.
   FREQ, SIZE, CHAN = getmixerargs()
   pygame.mixer.init(FREQ, SIZE, CHAN, BUFFER)


   '''You definitely need test mp3 file (a.mp3 in example) in a directory, say under 'C:\\Temp'
   * To play wav format file instead of mp3, 
      1) replace a.mp3 file with it, say 'a.wav'
      2) In try except clause below replace "playmusic()" with "playsound()"
	
   '''


def input_prompt(conn):  # thread function to get input from keyboard
    while True:
        # get input to send
        message = input()
        if message == "quit":
            break  # repeat until input "quit"
        conn.send(message.encode())
        print("I > " + message)
    # disconnect socket
    conn.close()
    pass

def server_main(host, port, port2):
    # create socket for server
    sock = socket(AF_INET, SOCK_STREAM)
    sock2 = socket(AF_INET, SOCK_STREAM)	

    p = pyaudio.PyAudio()

    send_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input = True, frames_per_buffer=CHUNK)
    receive_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output = True, frames_per_buffer=CHUNK)
    stt_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input = True, output = True, frames_per_buffer=CHUNK)


    s_addr = (host, port)
    s2_addr = (host, port2)
    print("Server open with " + host + ":%d and %d" % (port, port2))

    # socket bind
    sock.bind(s_addr)
    sock2.bind(s2_addr)

    # socket listen
    sock.listen(1)
    sock2.listen(1)

    while True:
        # accept connection from client
        conn, c_addr = sock.accept()
        conn_audio, c_au_addr = sock2.accept()

        try:
            print("Client " + str(c_addr))

            # make a thread to get sending input
            t = threading.Thread(target=input_prompt, args=(conn,))
            t.daemon = True
            t.start()

            receive_thread = threading.Thread(target=receive_audio, args=(conn_audio, receive_stream, CHUNK))
            receive_thread.daemon = True

            send_thread = threading.Thread(target=send_audio, args=(conn_audio, send_stream, CHUNK))
            send_thread.daemon = True

            stt_thread = threading.Thread(target=stt, args=(conn_audio, stt_stream, CHUNK))
            stt_thread.daemon = True

            receive_thread.start()
            send_thread.start()
            stt_thread.start()
            
            # receive message
            while True:
                # print received message
                #useless = 0
                print("\n<" + str(c_addr[0]) + "> : " + conn.recv(4096).decode())

        except Exception as e:
            print("Error Occured Close socket")
            print(e)
            # disconnect socket
            conn.close()
            conn_audio.close()

    # disconnect socket
    sock.close()
    sock2.close()

#pyaudio
class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)

#크롤링
index = 0
def user_Name(userName):
    global index
    req = requests.get('https://www.op.gg/summoner/userName='+userName)
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')
 
    userSoloRank = soup.select(
        'div.TierRankInfo > div.TierRank'
        )
    userTeamRank = soup.select(
        'div > div.sub-tier__rank-tier'
    )
    userMostChampion = soup.select(
        'div.ChampionInfo > div.ChampionName > a'
    )
    
    for i in userSoloRank:
        print('솔랭티어= ' + i.text)
        sd = userName + (' 솔랭티어는 ') + i.text + ' '
    for i in userTeamRank:
        print('팀랭티어= ' + i.text.strip())
        sd += (' 팀랭티어는' ) + i.text.strip() + ' '
    print('선호 챔피언=')
    sd += (' 선호 챔피언은 ')
    for i in userMostChampion:
        print(i.text.strip())
        sd += i.text.strip() + '  '

    tts = gTTS(text=sd, lang='ko')
    tts.save(s_path + 'Ssound' + str(index) + '.mp3')
    time.sleep(1)
    try:
        initMixer()
        filename= s_path + 'Ssound' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")
    except Exception as ex:
        print("unknown error", ex)
     
    print("Done")


def getId():
    sum_result = {}
    summoner_url = "https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-name/" + str(summoner_name)    #소환사 정보 검색
    params = {'api_key': api_key}
    res = requests.get(summoner_url, params=params)
    if res.status_code == requests.codes.ok:  # 결과값이 정상적으로 반환되었을때만 실행하도록 설정
        summoners_result = res.json()  # response 값을 json 형태로 변환시키는 함수
        if summoners_result:
            sum_result['id'] = summoners_result['id']
            #print(sum_result['id'])
            return (sum_result['id'])

index = 0
def getTier(summonerName):
    global index
    req = requests.get('https://www.op.gg/summoner/userName=' + summonerName)
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')
    userSoloRank = soup.select(
        'div.TierRankInfo > div.TierRank'
    )
    for i in userSoloRank:
        print(summonerName + ' 솔랭티어= ' + i.text)
        sd = summonerName + ('티어는') + i.text + ' '
    tts = gTTS(text=sd, lang='ko')
    tts.save(s_path + 'SgetTier' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'SgetTier' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")
    except Exception as ex:
        print("unknown error", ex)

    print("Done")

def getEnemyInfo(): 
    global summoner_name
    enemy_result = {}
    team = 0
    summoner_url = "https://kr.api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + str(getId())  # 실시간 인게임 정보 검색
    params = {'api_key': api_key}
    res = requests.get(summoner_url, params=params)
    if res.status_code == requests.codes.ok:  # 결과값이 정상적으로 반환되었을때만 실행하도록 설정
        summoners_result = res.json()  # response 값을 json 형태로 변환시키는 함수
        if summoners_result:
            for i in range(0, 10):
                if(summoners_result["participants"][i]['summonerName'] == summoner_name):
                    team = summoners_result["participants"][i]['teamId']
            if(team == 100):
                print(summoner_name + '블루팀 플레이중')
                for i in range(5, 10):
                    enemy_result['summonerName'] = summoners_result["participants"][i]['summonerName']
                    getTier(enemy_result['summonerName'])
            elif(team == 200):
                print(summoner_name + '레드팀 플레이중')
                for i in range(0, 5):
                    enemy_result['summonerName'] = summoners_result["participants"][i]['summonerName']
                    getTier(enemy_result['summonerName'])

def ladder():
    req = requests.get('https://www.op.gg/ranking/ladder/')
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')

    ladder_list = soup.select('#summoner-57671404 > a')
    ladder = str(ladder_list)
    ladder = re.sub('<.+?>', '', ladder, 0).strip()
    result = '현재 랭킹 1위는 ' + ladder + ' 입니다.'
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'ladder' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'ladder' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def temperature():
    req = requests.get('https://search.naver.com/search.naver?sm=top_hty&fbm=1&ie=utf8&query=정릉동+날씨')
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')

    list_temperature = soup.select('div.main_info > div > p > span.todaytemp')
    temperature = str(list_temperature)
    temperature = re.sub('<.+?>', '', temperature, 0).strip()
    temperature_result = temperature[1]

    list_yesterday = soup.select('div.main_info > div > ul > li:nth-child(1) > p')
    yesterday = str(list_yesterday)
    yesterday = re.sub('<.+?>', '', yesterday, 0).strip()
    yesterday_result = ''
    for i in yesterday:
        yesterday_result += i
        if(i=='요'):
            break    
    list_dust = soup.select('div.today_area._mainTabContent > div.sub_info > div > dl > dd:nth-child(2)')
    dust = str(list_dust)
    dust = re.sub('<.+?>', '', dust, 0).strip()

    result = '오늘 온도는 ' + temperature_result + '도 입니다. 날씨는 ' + yesterday_result + '. 미세먼지는 ' + dust + ' 입니다. '
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'temperature' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'temperature' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def movie():
    req = requests.get('https://search.naver.com/search.naver?sm=top_hty&fbm=1&ie=utf8&query=영화')
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')

    list_movie1 = soup.select('div.movie_run.section > ul:nth-child(3) > li:nth-child(1) > dl > dt > a')
    movie1 = str(list_movie1)
    movie1 = re.sub('<.+?>', '', movie1, 0).strip()

    list_movie2 = soup.select('div.movie_run.section > ul:nth-child(3) > li:nth-child(2) > dl > dt > a')
    movie2 = str(list_movie2)
    movie2 = re.sub('<.+?>', '', movie2, 0).strip()

    list_movie3 = soup.select('div.movie_run.section > ul:nth-child(3) > li:nth-child(3) > dl > dt > a')
    movie3 = str(list_movie3)
    movie3 = re.sub('<.+?>', '', movie3, 0).strip()
    movie = '현재 상영 영화 베스트 쓰리는 ' + movie1 + ' ' + movie2 + ' ' + movie3 + ' ' + ' 입니다.'
    print(movie)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'movie' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'movie' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def search():
    html = requests.get('https://www.naver.com/').text
    soup = BeautifulSoup(html, 'html.parser')

    title_list = soup.select('.PM_CL_realtimeKeyword_rolling span[class*=ah_k]')
    cnt = 0
    result = '실시간 검색어 베스트 쓰리는 '
    for idx, title in enumerate(title_list, 1):
        cnt += 1
        result += str(idx) + ' ' + title.text + ' '
        if(cnt == 3):
            break
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'search' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'search' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def epl():
    html = requests.get('https://search.naver.com/search.naver?sm=tab_sug.top&where=nexearch&query=epl+순위').text
    soup = BeautifulSoup(html, 'html.parser')
    epl_list = soup.select('.tb_type2 span a')
    epl = str(epl_list)
    epl = re.sub('<.+?>', '', epl, 0).strip()
    cnt = 0
    result = '이피엘 랭킹 쓰리는 '
    for i in epl:
        result += i
        if(i == ','):
            cnt += 1
            if(cnt == 3):
                result += ' 입니다'
                break
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'epl' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'epl' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def music():
    req = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=음악+차트')
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')
    music_list1 = soup.select('#main_pack > div.sc.sp_music._prs_mus_sen > div.api_subject_bx.type_slim.music_chart > ol > li:nth-child(1) > div > div.music_area > div.music_info > div.title > a')
    music1 = str(music_list1)
    music1 = re.sub('<.+?>', '', music1, 0).strip()

    music_list2 = soup.select('#main_pack > div.sc.sp_music._prs_mus_sen > div.api_subject_bx.type_slim.music_chart > ol > li:nth-child(2) > div > div.music_area > div.music_info > div.title > a')
    music2 = str(music_list2)
    music2 = re.sub('<.+?>', '', music2, 0).strip()

    music_list3 = soup.select('#main_pack > div.sc.sp_music._prs_mus_sen > div.api_subject_bx.type_slim.music_chart > ol > li:nth-child(3) > div > div.music_area > div.music_info > div.title > a')
    music3 = str(music_list3)
    music3 = re.sub('<.+?>', '', music3, 0).strip()
    result = '음악 탑 쓰리는 ' + music1 + ' ' + music2 + ' ' + music3 + ' 입니다.'
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'music' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'music' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

def delicious():
    req = requests.get('https://search.naver.com/search.naver?sm=tab_hty.top&where=nexearch&query=성신여대+맛집')
    html = req.text
    soup = BeautifulSoup(html, 'html.parser')
    delicious_list1 = soup.select('#_business_102119591 > div > div > div.tit')
    delicious1 = str(delicious_list1)
    delicious1 = re.sub('<.+?>', '', delicious1, 0).strip()

    delicious_list2 = soup.select('#_business_34582217 > div > div > div.tit')
    delicious2 = str(delicious_list2)
    delicious2 = re.sub('<.+?>', '', delicious2, 0).strip()

    delicious_list3 = soup.select('#_business_1383041234 > div > div > div.tit')
    delicious3 = str(delicious_list3)
    delicious3 = re.sub('<.+?>', '', delicious3, 0).strip()

    result = '성신여대 추천 맛집으로는 ' + delicious1 + ' ' + delicious2 + ' ' + delicious3 + ' 이 있습니다'
    print(result)

    tts = gTTS(text=result, lang='ko')
    tts.save(s_path + 'delicious' + str(index) + '.mp3')

    try:
        initMixer()
        filename = s_path + 'delicious' + str(index) + '.mp3'
        playmusic(filename)
        index = index + 1
    except KeyboardInterrupt:  # to stop playing, press "ctrl-c"
        stopmusic()
        print("\nPlay Stopped by user")

#음성 출력
def listen_print_loop(responses):
    """Iterates through server responses and prints them.
    The responses passed is a generator that will block until a response
    is provided by the server.
    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.
    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()
            
            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)
            if re.search(r'\b(시리야)\b', transcript, re.I):
                #시리 호출하면 다음 음성을 받아와 유저 검색
                user_Name(listen_print_username(responses))

            if re.search(r'\b(상대방)\b', transcript, re.I):
                #'상대방' 호출하면 상대방 5명 정보 검색
                getEnemyInfo()

            if re.search(r'\b(랭킹)\b', transcript, re.I):
                #'랭킹' 호출하면 현재 랭킹 1위 검색
                ladder()

            if re.search(r'\b(날씨)\b', transcript, re.I):
                #'날씨' 호출하면 날씨 및 미세먼지 검색
                temperature()

            if re.search(r'\b(영화)\b', transcript, re.I):
                #'영화' 호출하면 영화 BEST 3 검색
                movie()

            if re.search(r'\b(실검)\b', transcript, re.I):
                #'실검' 호출하면 실시간 검색어 3위까지 검색
                search()

            if re.search(r'\b(챔스)\b', transcript, re.I):
                #'챔스' 호출하면 챔스 순위 3위까지 검색
                epl()

            if re.search(r'\b(노래)\b', transcript, re.I):
                #'노래' 호출하면 노래 차트 TOP3 까지 검색
                music()

            if re.search(r'\b(맛집)\b', transcript, re.I):
                #'맛집' 호출하면 성신여대 맛집 BEST3까지 검색
                delicious()

            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if re.search(r'\b(영어로)\b', transcript, re.I):
                language_code = 'en-US'
            if re.search(r'\b(exit|quit|종료)\b', transcript, re.I):
                print('Exiting..')
                break
            
            num_chars_printed = 0
 
#값 가져오기           
def listen_print_username(responses):
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript

        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()
            
            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)
            index = 0
            if re.search(r'\b(시리야)\b', transcript, re.I):  
                key = user_Name(listen_print_loop(responses))
                
            if re.search(r'\b(영어로)\b', transcript, re.I):
                language_code = 'en-US'
            if re.search(r'\b(exit|quit|종료)\b', transcript, re.I):
                print('Exiting..')
                break
            return transcript
            num_chars_printed = 0

if __name__ == "__main__":  # main function
    if len(sys.argv) != 4:
        print("[USAGE] : server.py [HOST_IPADDR] [PORT]")  # check if ip and port are specifed
    else:
        try:
            # get host and port
            port = int(sys.argv[2])
            port2 = int(sys.argv[3])
            server_main(sys.argv[1], port, port2)  # call main network main function
        except ValueError:
            print("PORT should be Integer Value")

