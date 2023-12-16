#!/usr/bin/env python
import rospy
from std_msgs.msg import String
from std_msgs.msg import Int8, Float32MultiArray
import numpy as np
import cv2
from sensor_msgs.msg import CompressedImage
from openai import OpenAI
import base64
import requests
from lego_manipulation.srv import GPTFeedbackControl, GPTFeedbackControlResponse
import os
from gpt_helper_func import *
import copy

CUR_IMG_OBS = None

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Path to your image
pickup_img_path = os.getcwd() + "/correct_pickup.png"
# Getting the base64 string
CORRECT_PICKUP_OBS = encode_image(pickup_img_path)

# openai_api_key = "YOUR OPENAI KEY"
openai_api_key = "YOUR OPENAI KEY"
client = OpenAI(api_key=openai_api_key)



gpt_msg_history = [system_msg]
history_imgs = []
history_loc = []
history_offset = []
is_first_call = True

def GPT_call(cur_loc):
    global is_first_call, history_imgs, history_loc, history_offset, gpt_msg_history

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    """
    loc_str = f"Current robot gripper location is x: {cur_loc[0]}, y: {cur_loc[1]}, z: {cur_loc[2]}."
    user_mg = {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": user_initial_prompt + loc_str
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{CORRECT_PICKUP_OBS}"
            }
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{CUR_IMG_OBS}"
            }
            }
        ]
    }
    """
    if (is_first_call):
        loc_str = f"Current robot gripper location is x: {cur_loc[0]}, y: {cur_loc[1]}, z: {cur_loc[2]}."
        user_mg = {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": user_initial_prompt + loc_str
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{CORRECT_PICKUP_OBS}"
                }
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{CUR_IMG_OBS}"
                }
                }
            ]
        }
        is_first_call = False
    else:
        loc_str = f"Last robot gripper is x: {history_loc[-1][0]}, y: {history_loc[-1][1]}, z: {history_loc[-1][2]}, current gripper location is x: {cur_loc[0]}, y: {cur_loc[1]}, z: {cur_loc[2]}. "
        user_mg = {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": user_subsequent_prompt + loc_str
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{CORRECT_PICKUP_OBS}"
                }
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{history_imgs[-1]}"
                }
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{CUR_IMG_OBS}"
                }
                }
            ]
        }
    gpt_msg_history.append(user_mg)
    history_imgs.append(copy.deepcopy(CUR_IMG_OBS))
    history_loc.append((cur_loc[0], cur_loc[1], cur_loc[2]))

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": gpt_msg_history,
        "max_tokens": 512
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response


def parse_response(response: str):
    string_list = response.strip().split('\n')
    # each task starts with #.
    strokes = []
    stroke = []
    for string in string_list:
        idx1 = string.find('(')
        idx2 = string.find(')')
        if (idx1 != -1 and idx2 != -1):
            xyz_string = string[idx1+1:idx2]
            tmp = xyz_string.split(",")
            if (len(tmp) == 3):
                try:
                    x = float(tmp[0])
                    y = float(tmp[1])
                    z = float(tmp[2])
                    return (x,y,z)
                except:
                    continue
    return None

def handle_feedback_control(req):
    global gpt_msg_history
    cur_loc = (round(req.x,3), round(req.y,3), round(req.z,3))
    if (CUR_IMG_OBS is not None):
        response = GPT_call(cur_loc)
        print(f"content {response.json()}")
        response = response.json()['choices'][0]['message']['content']
        assistant_msg = {
            "role": "assistant",
            "content": [
                {
                "type": "text",
                "text": response
                },
            ]
        }
        gpt_msg_history.append(assistant_msg)
        
        result = parse_response(response)
        print(f"result {result}\n\n")
        if (result is not None):
            return GPTFeedbackControlResponse(0,result[0],result[1],result[2]) 
        else:
            return GPTFeedbackControlResponse(0,0,0,0)
        
    

def img_callback(img_data):
    global CUR_IMG_OBS
    #### direct conversion to CV2 ####
    np_arr = np.fromstring(img_data.data, np.uint8)
    #CUR_IMG_OBS = base64.b64encode(np_arr).decode('utf-8')
    #cv2.imwrite("./save.jpg", CUR_IMG_OBS)
    image_np = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    image_np = cv2.rotate(image_np, cv2.ROTATE_180)
    #CUR_IMG_OBS = image_np
    #cv2.imwrite("./save.jpg", image_np)

    im_arr = cv2.imencode('.jpg', image_np)[1]  # im_arr: image in Numpy one-dim array format.
    im_bytes = im_arr.tobytes()
    CUR_IMG_OBS = base64.b64encode(im_bytes).decode('utf-8')

    #print("save img")
    #cv2.imshow('cv_img', image_np)


def gpt_server():

    # In ROS, nodes are uniquely named. If two nodes with the same
    # name are launched, the previous one is kicked off. The
    # anonymous=True flag means that rospy will choose a unique
    # name for our 'listener' node so that multiple listeners can
    # run simultaneously.
    rospy.init_node('gpt_server', anonymous=True)
    rospy.Subscriber("/fanuc_gazebo/wrist_camera/image_raw/compressed", CompressedImage, img_callback,  queue_size = 1)
    
    s = rospy.Service('/gpt_feedback_control', GPTFeedbackControl, handle_feedback_control)

    #rospy.Subscriber("/stmotion_controller_task_planning_cartesian/gpt_control_topic", Int8, callback)
    
    print("Ready to take client request.")

    # spin() simply keeps python from exiting until this node is stopped
    rospy.spin()

if __name__ == '__main__':
    gpt_server()