

system_msg_text = """
You are a feedback controller and designed to generate adjustment values in x,y,z directions in incremental way to help the robot gripper to approach the brick and pick it up.
"""
system_msg = {
    "role": "system",
    "content": [
        {
        "type": "text",
        "text": system_msg_text
        },
    ]
}

user_initial_prompt = """
The goal is to pick up the brick near our gripper in this image. But our position is still not perfectly aligned with the brick.
The first image demonstrates the correct way to pick up brick using our grey robot gripper. 
The second image is a side view observation and our goal is to pick up the brick near our gripper in this image.
Remember you only need to give a rough estimation of the adjustment distance, and the offset adjustment unit is 0.002.
The numerical result must be a list in the format:

    ###. X direction adjustment: 
    ###. Y direction adjustment: 
    ###. Z direction adjustment: 
And also collect the numerical offset in X, Y, Z in a tuple ( , , ). Do not use bracket anywhere else.

Be concise. And make sure don't collide with the bricks."""

user_subsequent_prompt = """
The goal is to pick up the brick near our gripper in this image. But our position is still not perfectly aligned with the brick.
The first image demonstrates the correct way to pick up brick using our grey robot gripper. 
The second image is the last side view observation and the third image is our current side view observation.
Give an estimation of the adjustment distance considering the history offset adjustments and their corresponding changes in observation.
The numerical result must be a list in the format:

    ###. X direction adjustment: 
    ###. Y direction adjustment: 
    ###. Z direction adjustment: 
And also collect the numerical offset in X, Y, Z in a tuple ( , , ). Do not use bracket anywhere else.

Be concise. And make sure don't collide with the bricks."""