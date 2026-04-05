# convert the videos to mp3
import os
import subprocess

files = os.listdir("videos")

for file in files:
    tutorial_number = file.split(".mp")[0].split("ial ")[1]
    file_name = file.split(" Sigma")[0]
    print(tutorial_number, file_name)
    #subprocess.run(["ffmpeg", "-i",f"videos{file}", f"audios/{tutorial_number}_{file_name}.mp3"])
    subprocess.run(["ffmpeg", "-i", f"videos/{file}", f"audios/{tutorial_number}_{file_name}.mp3"])