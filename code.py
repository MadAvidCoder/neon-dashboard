## SET TO TRUE TO TEST WITHOUT API KEYS (will use demo data)
dev_mode = True
############################################################

import time, board, displayio, framebufferio, rgbmatrix, terminalio, adafruit_display_text.label, requests, math, ssl, socket, hashlib, hmac
from adafruit_bitmap_font import bitmap_font
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Adafruit IO dashboard credentials
aio_username = "YOUR_ADAFRUIT_IO_USERNAME_HERE"
aio_key = "<YOUR_ADAFRUIT_IO_API_KEY_HERE>"

# WeatherAPI credentials
weather_api_key = "<YOUR_WEATHAPI_API_KEY_HERE>"

# PTV API credentials
ptv_key = "<YOUR_PTV_KEY_HERE>"
ptv_devid = "<YOUR_PTV_DEVID>"

# Wakatime (Hackatime) credentials
wakatime_userid = "<YOUR_WAKATIME_USER_ID_HERE"

on = True

font = bitmap_font.load_font("5x5-mini-5-5.bdf")

screen = 0

changed = True

if not dev_mode:
    def aio_message(client, topic, message):
        global screen, on, matrix, changed
        if "brightness" in topic:
            matrix.brightness = int(message)/100
        elif "on" in topic:
            changed = True
            if message == "OFF":
                on = False
            elif message == "ON":
                on = True
        elif "next" in topic:
            changed = True
            if message == "1":
                screen += 1
                if screen >= 4:
                    screen = 0

def get_12_time():
    hour = time.localtime().tm_hour
    am = "AM"
    if hour == 0:
        hour = 12
    elif hour == 11:
        am = "PM"
    elif hour > 12:
        am = "PM"
        hour -= 12
    return str(hour).zfill(2) + ":" + str(time.localtime().tm_min).zfill(2) + " " + am

def get_24_time():
    return str(time.localtime().tm_hour).zfill(2) + ":" + str(time.localtime().tm_min).zfill(2)

if not dev_mode:
    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        port=1883,
        username=aio_username,
        password=aio_key,
        socket_pool=socket,
        ssl_context=ssl.create_default_context(),
    )

    mqtt_client.on_message = aio_message
    
    mqtt_client.connect()
    
    mqtt_client.subscribe(aio_username+"/feeds/on")
    mqtt_client.subscribe(aio_username+"/feeds/next")
    mqtt_client.subscribe(aio_username+"/feeds/brightness")

displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=64, height=32, bit_depth=3,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13, latch_pin=board.D0, output_enable_pin=board.D1)
display = framebufferio.FramebufferDisplay(matrix, auto_refresh=False)

### SCREEN 0 - LARGE CLOCK ###
days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

screen_0 = displayio.Group()

s0l1 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0x0077ff
)
s0l1.text = get_12_time()
s0l1.x = 8
s0l1.y = 9

s0l2 = adafruit_display_text.label.Label(
    font,
    color=0xff6f00)
s0l2.text = days[time.localtime().tm_wday]
s0l2.x = 6
s0l2.y = 22

s0l3 = adafruit_display_text.label.Label(
    font,
    color=0xff6f00)
s0l3.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
s0l3.x = 36
s0l3.y = 22

screen_0.append(s0l1)
screen_0.append(s0l2)
screen_0.append(s0l3)

### SCREEN 1 - WEATHER ###

screen_1 = displayio.Group()

weather_icons_key = {
    1000: "sun",
    1003: "partsun",
    1006: "cloud",
    1009: "darkcloud",
    1030: "fogcloud",
    1063: "rain",
    1066: "rain",
    1069: "rain",
    1072: "rain",
    1087: "thunder",
    1114: "rain",
    1117: "rain",
    1135: "fogcloud",
    1147: "fogcloud",
    1150: "rain",
    1153: "rain",
    1168: "rain",
    1171: "rain",
    1180: "rain",
    1183: "rain",
    1186: "rain",
    1189: "rain",
    1192: "rain",
    1195: "rain",
    1198: "rain",
    1201: "rain",
    1204: "rain",
    1207: "rain",
    1210: "rain",
    1213: "rain",
    1216: "rain",
    1219: "rain",
    1222: "rain",
    1225: "rain",
    1237: "rain",
    1240: "rain",
    1243: "rain",
    1246: "rain",
    1249: "rain",
    1252: "rain",
    1255: "rain",
    1258: "rain",
    1261: "rain",
    1264: "rain",
    1273: "thunder",
    1276: "thunder",
    1279: "thunder",
    1282: "thunder"
}

weather_icons = {
    "cloud": displayio.OnDiskBitmap(open("cloud.bmp", "rb")),
    "darkcloud": displayio.OnDiskBitmap(open("darkcloud.bmp", "rb")),
    "fogcloud": displayio.OnDiskBitmap(open("fogcloud.bmp", "rb")),
    "partsun": displayio.OnDiskBitmap(open("partsun.bmp", "rb")),
    "rain": displayio.OnDiskBitmap(open("rain.bmp", "rb")),
    "sun": displayio.OnDiskBitmap(open("sun.bmp", "rb")),
    "thunder": displayio.OnDiskBitmap(open("thunder.bmp", "rb")),
}

last_weather = ""

for i in weather_icons.keys():
    group = displayio.Group()
    temp = displayio.TileGrid(weather_icons[i], pixel_shader=getattr(weather_icons[i], 'pixel_shader', displayio.ColorConverter()))
    temp.x = 7
    temp.y = 17
    group.append(temp)
    screen_1.append(group)
    group.hidden = True
    weather_icons[i] = group

weather_data = {}

def sync_weather():
    global weather_data
    if not dev_mode:
        try:
            weather_data = requests.get(f"https://api.weatherapi.com/v1/forecast.json?key={weather_api_key}&q=Melbourne&days=1&aqi=no&alerts=no").json()
        except:
            print("Failed to fetch weather data")
    else:
        # Use demo data
        weather_data = {
            "current": {
                "temp_c": 27,
                "condition": {
                    "code": 1003
                }
            },
            "forecast": {
                "forecastday": [
                    {
                        "day" : {
                            "mintemp_c": 23,
                            "maxtemp_c": 31
                        }
                    }
                ]
            }
        }

def show_icon():
    global weather_data, weather_icons, weather_icons_key, screen_1, last_weather
    if last_weather:
        weather_icons[last_weather].hidden = True
    last_weather = weather_icons_key[weather_data["current"]["condition"]["code"]]
    weather_icons[last_weather].hidden = False

sync_weather()
show_icon()

s1l1 = adafruit_display_text.label.Label(
    font,
    color=0x0077ff
)
s1l1.text = get_24_time()
s1l1.x = 1
s1l1.y = 4

s1l2 = adafruit_display_text.label.Label(
    font,
    color=0xff6f00)
s1l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
s1l2.x = 39
s1l2.y = 4

s1l3 = adafruit_display_text.label.Label(
    font,
    color=0x96c7ff)
s1l3.text = str(weather_data["forecast"]["forecastday"][0]["day"]["mintemp_c"]) + "C"
s1l3.x = 2
s1l3.y = 13

s1l4 = adafruit_display_text.label.Label(
    font,
    color=0xff9696)
s1l4.text = str(weather_data["forecast"]["forecastday"][0]["day"]["maxtemp_c"]) + "C"
s1l4.x = 37
s1l4.y = 13

s1l5 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xff0000)
s1l5.text = str(weather_data["current"]["temp_c"]) + "C"
s1l5.x = 32
s1l5.y = 24

screen_1.append(s1l1)
screen_1.append(s1l2)
screen_1.append(s1l3)
screen_1.append(s1l4)
screen_1.append(s1l5)

### SCREEN 2 - HACKATIME ###
def wakatime_time():
    if not dev_mode:
        try:
            resp = requests.get(f"https://waka.hackclub.com/api/compat/wakatime/v1/users/{wakatime_userid}/stats/today").json()
            total_seconds = resp["data"]["total_seconds"]
            seconds = total_seconds % 60
            total_minutes = math.floor(total_seconds / 60)
            minutes = total_minutes % 60
            hours = math.floor(total_minutes / 60)
            return str(hours).zfill(2) + ":" + str(minutes).zfill(2)
        except:
            return ""
    else:
        # Use demo data
        return "02:24"

def wakatime_project():
    if not dev_mode:
        try:
            resp = requests.get(f"https://waka.hackclub.com/api/compat/wakatime/v1/users/{wakatime_userid}/stats/today").json()
            return resp["data"]["projects"][0]["name"]
        except:
            return ""
    else:
        return "Neon"

def wakatime_project_time(project):
    if not dev_mode:
        try:
            if project:
                resp = requests.get(f"https://waka.hackclub.com/api/compat/wakatime/v1/users/{wakatime_userid}/stats/all_time?project={project}").json()
                return str(resp["data"]["projects"][0]["hours"]).zfill(2) + ":" + str(resp["data"]["projects"][0]["minutes"]).zfill(2)
            else:
                return "GET CODING!"
        except:
            return ""
    else:
        return "09:17"

screen_2 = displayio.Group()

s2l1 = adafruit_display_text.label.Label(
    font,
    color=0x0077ff
)
s2l1.text = get_24_time()
s2l1.x = 1
s2l1.y = 4

s2l2 = adafruit_display_text.label.Label(
    font,
    color=0xff6f00)
s2l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
s2l2.x = 39
s2l2.y = 4


s2l3 = adafruit_display_text.label.Label(
    terminalio.FONT,
    color=0xfc03ad)
s2l3.text = wakatime_time()
s2l3.x = 17
s2l3.y = 12

s2l4 = adafruit_display_text.label.Label(
    font,
    color=0x13ba50)
s2l4.text = wakatime_project()
s2l4.x = 0
s2l4.y = 23

s2l5 = adafruit_display_text.label.Label(
    font,
    color=0x1388ba)
s2l5.text = wakatime_project_time(s2l4.text)
s2l5.x = 0
s2l5.y = 29

screen_2.append(s2l1)
screen_2.append(s2l2)
screen_2.append(s2l3)
screen_2.append(s2l4)
screen_2.append(s2l5)

### SCREEN 3 - PTV ###

def ptv_request(request):
    if not dev_mode:
        try:
            global ptv_devid, ptv_key
            request = request + ('&' if ('?' in request) else '?')
            raw = request + 'devid={0}'.format(ptv_devid)
            
            # Convert key and raw to bytes, since hmac requires bytes input
            key_bytes = bytes(ptv_key, 'utf-8')
            raw_bytes = bytes(raw, 'utf-8')
            
            hashed = hmac.new(key_bytes, raw_bytes, hashlib.sha1)
            signature = hashed.hexdigest()
            
            return 'http://timetableapi.ptv.vic.gov.au/' + raw + '&signature={}'.format(signature)
        except:
            return ""
    else:
        return ""

def get_train():
    if not dev_mode:
        try:
            r = ptv_request('/v3/departures/route_type/0/stop/1108?max_results=2')
            first = r["departures"][0]["estimated_departure_utc"].split(".")[0]
            second = r["departures"][0]["estimated_departure_utc"].split(".")[0]
            first = time.strptime(first, "%Y-%m-%dT%H:%M:%S")
            second = time.strptime(second, "%Y-%m-%dT%H:%M:%S")
            first_diff = first - time.localtime()
            second_diff = second - time.localtime()
            return [first_diff.tm_min, second_diff.tm_min]
        except:
            return [0,0]
    else:
        return [12, 22]

def get_bus():
    if not dev_mode:
        try:
            r = ptv_request('/v3/departures/route_type/2/stop/761?max_results=2')
            first = r["departures"][0]["estimated_departure_utc"].split(".")[0]
            second = r["departures"][0]["estimated_departure_utc"].split(".")[0]
            first = time.strptime(first, "%Y-%m-%dT%H:%M:%S")
            second = time.strptime(second, "%Y-%m-%dT%H:%M:%S")
            first_diff = first - time.localtime()
            second_diff = second - time.localtime()
            return [first_diff.tm_min, second_diff.tm_min]
        except:
            return [0,0]
    else:
        return [9, 15]

screen_3 = displayio.Group()

s3l1 = adafruit_display_text.label.Label(
    font,
    color=0x0077ff
)
s3l1.text = get_24_time()
s3l1.x = 1
s3l1.y = 4

s3l2 = adafruit_display_text.label.Label(
    font,
    color=0xff6f00)
s3l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
s3l2.x = 39
s3l2.y = 4

s3l3 = adafruit_display_text.label.Label(
    font,
    color=0xd96fad)
s3l3.text = "BUS"
s3l3.x = 1
s3l3.y = 11

s3l4 = adafruit_display_text.label.Label(
    font,
    color=0x926fd9)
s3l4.text = "TRAIN"
s3l4.x = 34
s3l4.y = 11

s3l5 = adafruit_display_text.label.Label(
    font,
    color=0xd96fad)
s3l5.text = str(get_bus()[0]).zfill(2) + "M"
s3l5.x = 1
s3l5.y = 19

s3l6 = adafruit_display_text.label.Label(
    font,
    color=0x926fd9)
s3l6.text = str(get_train()[0]).zfill(2) + "M"
s3l6.x = 34
s3l6.y = 19

s3l7 = adafruit_display_text.label.Label(
    font,
    color=0xd96fad)
s3l7.text = str(get_bus()[1]).zfill(2) + "M"
s3l7.x = 1
s3l7.y = 27

s3l8 = adafruit_display_text.label.Label(
    font,
    color=0x926fd9)
s3l8.text = str(get_train()[1]).zfill(2) + "M"
s3l8.x = 34
s3l8.y = 27

screen_3.append(s3l1)
screen_3.append(s3l2)
screen_3.append(s3l3)
screen_3.append(s3l4)
screen_3.append(s3l5)
screen_3.append(s3l6)
screen_3.append(s3l7)
screen_3.append(s3l8)

screens = [screen_0, screen_1, screen_2, screen_3]
display.root_group = screen_0
display.refresh(minimum_frames_per_second=0)

blank = displayio.Group()

while True:
    if not dev_mode:
        mqtt_client.loop(timeout=1)
        s0l1.text = get_12_time()
        s0l2.text = days[time.localtime().tm_wday]
        s0l3.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s1l1.text = get_24_time()
        s1l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s2l1.text = get_24_time()
        s2l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s3l1.text = get_24_time()
        s3l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        if changed:
            changed = False
            if screen == 1:
                sync_weather()
                show_icon()
                s1l3.text = str(weather_data["forecast"]["forecastday"][0]["day"]["mintemp_c"]) + "C"
                s1l4.text = str(weather_data["forecast"]["forecastday"][0]["day"]["maxtemp_c"]) + "C"
                s1l5.text = str(weather_data["current"]["temp_c"]) + "C"
            elif screen == 2:
                s2l3.text = wakatime_time()
                s2l4.text = wakatime_project()
                s2l5.text = wakatime_project_time(s2l4.text)
            elif screen == 3:
                s3l5.text = str(get_bus()[0]).zfill(2) + "M"
                s3l6.text = str(get_train()[0]).zfill(2) + "M"
                s3l7.text = str(get_bus()[1]).zfill(2) + "M"
                s3l8.text = str(get_train()[1]).zfill(2) + "M"
            if on:
                display.root_group = screens[screen]
            else:
                display.root_group = blank
    else:
        s0l1.text = get_12_time()
        s0l2.text = days[time.localtime().tm_wday]
        s0l3.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s1l1.text = get_24_time()
        s1l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s2l1.text = get_24_time()
        s2l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        s3l1.text = get_24_time()
        s3l2.text = str(time.localtime().tm_mday) + "." + str(time.localtime().tm_mon).zfill(2)
        display.root_group = screens[screen]
        screen += 1
        if screen > 3:
            screen = 0
        time.sleep(5)
    display.refresh(minimum_frames_per_second=0)