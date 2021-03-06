__author__ = 'rodtoll'

import ISY
import threading
import datetime
import logging
import sys
import json
from twilio.rest import TwilioRestClient

MCP_STATE_HOME = 1
MCP_STATE_DOOR_OPEN = 2
MCP_STATE_DOOR_CLOSED_SENSING_BUFFER = 3
MCP_STATE_DOOR_CLOSED_SENSING_FULL = 4
MCP_STATE_HOME_BY_DEVICE = 5
MCP_STATE_AWAY = 6
MCP_STATE_NONE = 7

DEVICE_ID_ALARM_SET = "Office Keypad.C"
DEVICE_ID_CAR_PRESENT = "Office Keypad.D"
DEVICE_ID_DOOR_OPEN = "Office Keypad.E"
DEVICE_ID_RECENT_LIGHT = "Office Keypad.F"
DEVICE_ID_PHONE_PRESENT = "Office Keypad.G"
DEVICE_ID_DEVICE_ACTIVE = "Office Keypad.H"
VAR_ID_ALARM_AWAY_ACTIVE = "AlarmAwayModeActive"
VAR_ID_ALARM_STAY_ACTIVE = "AlarmStayModeActive"
VAR_ID_HOME_STATE = "HomeState"

DEVICE_STATE_ON = "on"

BUFFER_TIMEOUT = 180.0
NO_ACTIVITY_TIMEOUT = 180.0

myisy = None
isy_event = None
car_device = None
door_open_device = None
recent_light_device = None
phone_present_device = None
device_active_device = None
alarm_set_device = None
logger = None
config = None

def load_config():
    global config
    config_file = open('/home/root/houseconfig.json')
    config = json.load(config_file)
    config_file.close()

def log(message):
    if logger == None:
        print message
    else:
        logger.write_log_message(message)

def isy_event_handler(*args):
    global myisy
    global isy_event 

    #log("!!! Woke up... by device: "+myisy[args[0]['node']]['name'])
    log("!!! Woke up")
    isy_event.set()

current_state = MCP_STATE_DOOR_CLOSED_SENSING_FULL
last_known_main_state = MCP_STATE_NONE

def state_as_string(state):
    if state == MCP_STATE_HOME:
        return "HOMEHOME"
    elif state == MCP_STATE_DOOR_OPEN:
        return "DOOROPEN"
    elif state == MCP_STATE_DOOR_CLOSED_SENSING_BUFFER:
        return "DOORBUFF"
    elif state == MCP_STATE_DOOR_CLOSED_SENSING_FULL:
        return "DOORSENS"
    elif state == MCP_STATE_HOME_BY_DEVICE:
        return "HOMEDEVC"
    elif state == MCP_STATE_AWAY:
        return "AWAYAWAY"
    else:
        return "UNKNOWN!"

def current_state_as_string():
    global current_state
    return state_as_string(current_state)

def get_current_state_as_string():

    state_string = current_state_as_string()

    state_string += " ["
    if check_recent_device():
        state_string += "DEVICE-"
    else:
        state_string += "-------"

    if check_door_open():
        state_string += "DOOR-"
    else:
        state_string += "-----"

    if check_phone_present():
        state_string += "PHONE-"
    else:
        state_string += "------"

    if check_for_recent_light_activity():
        state_string += "LIGHT-"
    else:
        state_string += "------"

    if check_car_present():
        state_string += "CAR-"
    else:
        state_string += "----"

    if check_alarm_set():
        state_string += "ALARM-"
    else:
        state_string += "------"

    state_string += "]"

    return state_string

last_state_change = datetime.datetime.now()

def translate_state_to_main(state_to_translate):
    if state_to_translate == MCP_STATE_HOME_BY_DEVICE or state_to_translate == MCP_STATE_HOME:
        return MCP_STATE_HOME
    elif state_to_translate == MCP_STATE_AWAY:
        return MCP_STATE_AWAY
    else: 
        return MCP_STATE_NONE

def is_state_sensing(state_to_check):
    if translate_state_to_main(state_to_check) == MCP_STATE_NONE:
        return True
    else:
        return False

def send_text(text_contents):
    global config

    # Your Account Sid and Auth Token from twilio.com/user/account
    account_sid = config["textcreds"]["accountsid"]
    auth_token  = config["textcreds"]["authtoken"]
    client = TwilioRestClient(account_sid, auth_token)
 
    message = client.messages.create(body=text_contents,
        to=config["textcreds"]["targetnumber"],    # Replace with your phone number
        from_=config["textcreds"]["sourcenumber"]) # Replace with your Twilio number

def handle_house_major_state_change(new_state):
    log("Handling major state change to: "+state_as_string(new_state))
    send_text("House transitioning to: "+state_as_string(new_state))

def change_current_state(new_state):
    global current_state
    global last_state_change
    global last_known_main_state

    log("Transition from "+state_as_string(current_state)+" to "+state_as_string(new_state))
    last_state_change = datetime.datetime.now()

    if not is_state_sensing(new_state):
        translated_new_state = translate_state_to_main(new_state)
        translated_old_state = translate_state_to_main(last_known_main_state)
        if translated_new_state != translated_old_state:
            log("Detected major state change. Changing to "+state_as_string(translated_new_state))
            handle_house_major_state_change(translated_new_state)
            last_known_main_state = translated_new_state

    current_state = new_state

def check_recent_device():
    global device_active_device

    if device_active_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def check_alarm_away_active():
    global myisy

    return myisy.var_get_value(VAR_ID_ALARM_AWAY_ACTIVE) == 1

def set_home_state_variable(home_state):
    global myisy

    log("Setting state..."+str(home_state))

    myisy.var_set_value(VAR_ID_HOME_STATE,home_state)

def check_alarm_stay_active():
    global myisy

    return myisy.var_get_value(VAR_ID_ALARM_STAY_ACTIVE) == 1

def check_alarm_set():
    global alarm_set_device

    if alarm_set_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def check_car_present():
    global car_device

    if car_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def check_door_open():
    global door_open_device

    if door_open_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def check_phone_present():
    global phone_present_device

    if phone_present_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def get_delta_from_state_change_s():
    global last_state_change

    return (datetime.datetime.now() - last_state_change).seconds

def check_for_recent_light_activity():
    global recent_light_device

    if recent_light_device.formatted == DEVICE_STATE_ON:
        return True
    else:
        return False

def handle_state_home():
    if check_door_open():
        log("!!! Door is open transitioning...")
        change_current_state(MCP_STATE_DOOR_OPEN)
    elif check_alarm_away_active():
        log("!!! Alarm is active in away mode, ignoring other signals and transitioning...")
        change_current_state(MCP_STATE_AWAY)
    return

def handle_state_door_open():
    if not check_door_open():
        log("!!! Door is now closed, transitioning...")
        change_current_state(MCP_STATE_DOOR_CLOSED_SENSING_BUFFER)
    return

def handle_state_door_closed_sensing_buffer():
    if check_door_open():
        log("!!! Door was opened, trasitioning...")
        change_current_state(MCP_STATE_DOOR_OPEN)
    elif get_delta_from_state_change_s() >= BUFFER_TIMEOUT:
        log("!!! Buffer state has expired, transitioning...")
        change_current_state(MCP_STATE_DOOR_CLOSED_SENSING_FULL)

def handle_state_door_closed_sensing_full():
    if check_door_open():
        log("!!! Door was opened, transitioning...")
        change_current_state(MCP_STATE_DOOR_OPEN)
    elif check_alarm_set():
        if check_alarm_away_active():
            log("!!! Alarm is active in away mode, ignoring other signals and transitioning...")
            change_current_state(MCP_STATE_AWAY)
        elif check_alarm_stay_active():
            log("!!! Alarm is active in stay mode, transitioning...")
            change_current_state(MCP_STATE_HOME)
    elif check_for_recent_light_activity():
        log("!!! Activity in the Insteon light switches, transitioning...")
        change_current_state(MCP_STATE_HOME)
    elif check_phone_present() or check_recent_device():
        log("!!! Phone is present in range of the network, transitioning...")
        change_current_state(MCP_STATE_HOME_BY_DEVICE)
    elif get_delta_from_state_change_s() >= NO_ACTIVITY_TIMEOUT:
        log("!!! No activity, no one must be home...")
        change_current_state(MCP_STATE_AWAY)

def handle_state_home_by_device():
    if check_door_open():
        log("!!! Door was opened, transitioning...")
        change_current_state(MCP_STATE_DOOR_OPEN)
    elif check_alarm_set():
        if check_alarm_away_active():
            log("!!! Alarm is active in away mode, ignoring other signals and transitioning...")
            change_current_state(MCP_STATE_AWAY)
        elif check_alarm_stay_active():
            log("!!! Alarm is active in stay mode, transitioning...")
            change_current_state(MCP_STATE_HOME)
    elif check_for_recent_light_activity():
        log("!!! Activity in the Insteon light switches, transitioning...")
        change_current_state(MCP_STATE_HOME)
    elif check_recent_device():
        log("!!! Activity in monitored devices, transitioning...")
        change_current_state(MCP_STATE_HOME)
    elif not check_phone_present():
        log("!!! Phone is no longer present, must have been a ghost ping?")
        change_current_state(MCP_STATE_AWAY)

def handle_state_away():
    if check_door_open():
        log("!!! Door was opened, transitioning...")
        change_current_state(MCP_STATE_DOOR_OPEN)
    elif check_alarm_set():
        if check_alarm_away_active():
            log("!!! Alarm is set to away, ignoring other signals")
        elif check_alarm_stay_active():
            log("!!! Alarm is set to stay, ignoring other signals and transitioning...")
            change_current_state(MCP_STATE_HOME)
    elif check_for_recent_light_activity():
        log("!!! Activity in the Insteon light switches, transitioning...")
        change_current_state(MCP_STATE_HOME)
    elif check_recent_device():
        log("!!! Activity on monitored devices, transitioning...")
        change_current_state(MCP_STATE_HOME)
    elif check_phone_present():
        log("!!! Phone is present in range of the network, transitioning...")
        change_current_state(MCP_STATE_HOME_BY_DEVICE)

def set_home_indicators():
    global myisy
    global current_state

    set_home_state_variable(current_state)

    #if someone_home:
    #    myisy['Home Buttons'].on()
    #else:
    #    myisy['Home Buttons'].off()

def check_state():
    global current_state

    start_state = current_state

    log("+++ "+get_current_state_as_string())
    if current_state == MCP_STATE_HOME:
        handle_state_home()
    elif current_state == MCP_STATE_DOOR_OPEN:
        handle_state_door_open()
    elif current_state == MCP_STATE_DOOR_CLOSED_SENSING_BUFFER:
        handle_state_door_closed_sensing_buffer()
    elif current_state == MCP_STATE_DOOR_CLOSED_SENSING_FULL:
        handle_state_door_closed_sensing_full()
    elif current_state == MCP_STATE_HOME_BY_DEVICE:
        handle_state_home_by_device()
    elif current_state == MCP_STATE_AWAY:
        handle_state_away()
    log("--- "+get_current_state_as_string())

    if current_state != start_state:
        set_home_indicators()
        return True
    else:
        return False

def get_wait_period():
    global current_state

    result = None

    if current_state == MCP_STATE_DOOR_CLOSED_SENSING_BUFFER:
        result = BUFFER_TIMEOUT - get_delta_from_state_change_s()
        if result < 0.0:  # Special case where we checked earlier for timeout and wasn't quite there but now it is
            result = 1.0

    elif current_state == MCP_STATE_DOOR_CLOSED_SENSING_FULL:
        result = NO_ACTIVITY_TIMEOUT - get_delta_from_state_change_s()
        if result < 0.0:  # Special case where we checked earlier for timeout and wasn't quite there but now it is
            result = 1.0

    log("!!! sleeping for: "+str(result))
    return result

def init_devices():
    global myisy
    global car_device
    global door_open_device
    global recent_light_device
    global phone_present_device
    global alarm_set_device
    global device_active_device

    car_device = myisy[DEVICE_ID_CAR_PRESENT]
    door_open_device = myisy[DEVICE_ID_DOOR_OPEN]
    recent_light_device = myisy[DEVICE_ID_RECENT_LIGHT]
    phone_present_device = myisy[DEVICE_ID_PHONE_PRESENT]
    device_active_device = myisy[DEVICE_ID_DEVICE_ACTIVE]
    alarm_set_device = myisy[DEVICE_ID_ALARM_SET]

def init_isy():
    global myisy
    global config

    myisy = ISY.Isy(addr=config["isy"]["address"], userp=config["isy"]["password"], userl=config["isy"]["username"], eventupdates=1)

def init_events():
    global isy_event
    global myisy

    isy_event = threading.Event()
    myisy.callback_set(DEVICE_ID_DOOR_OPEN, isy_event_handler)
    myisy.callback_set(DEVICE_ID_DEVICE_ACTIVE, isy_event_handler)
    myisy.callback_set(DEVICE_ID_PHONE_PRESENT, isy_event_handler)
    myisy.callback_set(DEVICE_ID_RECENT_LIGHT, isy_event_handler)
    myisy.callback_set(DEVICE_ID_CAR_PRESENT, isy_event_handler)
    myisy.callback_set(DEVICE_ID_ALARM_SET, isy_event_handler)

def daemon_main(main_logger):
    global isy_event
    global logger
    
    logger = main_logger

    load_config()
    init_isy()
    init_events()
    init_devices()

    while True:
        log(">>> "+get_current_state_as_string())

        while True:
            if not check_state():
                break

        log("<<< "+get_current_state_as_string())

        isy_event.wait(get_wait_period())
        isy_event.clear()

if __name__ == "__main__":
    daemon_main(None)
