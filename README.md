# C3PO_Interactive_Animetronic
RASPBERRY PI CODE TO BE POSTED BY MAY 24 <br/> <br/>
This project invovles a life-size C-3P0 animetronic that utilizes live image processing to identify and interact with people that approach it. The project is on display at the Columbus Center of Science and Industry "Unofficial Galaxies" Star Wars exhibit from May 10 to September 1, 2025.

<img src="https://github.com/user-attachments/assets/d0c824bd-a196-4118-a7f5-44da636a55c9" width="400">
<img src="https://github.com/user-attachments/assets/ac83278d-d18e-473e-9619-aa98a6231adf" width="360">


# System Architecture
The system is primarily controlled by a Raspberry Pi 4b. The Pi runs an image processing algorithm using TensorFlow utilizing a Google Coral hardware accelerator to detect and identify different people on a camera feed looking at the area in front of c3po. The detected people's position is observed to determine the angle that c3po should look to address the person, and the determine if c3po should ask the person to come closer vs begin conversation. The detected people's ID is logged to determine how c3po should address the person and with what voice lines (initial greetings vs regular conversation). The amount of people detected is used to determine if c3po should be addressing one or multiple people. The voice lines are played using an audio Raspberry Pi hat that runs a speaker. The movement/position commands for the c3po animatronic are determined by the conversation logic algorithm running on an Arduino. The animatronic is directly controlled by a Maestro servo controller that recieves position commands from the Arduino. <br />
<img src="https://github.com/user-attachments/assets/f39d6726-093a-48d7-8ab3-8939790a358a" width="400">
<img src="https://github.com/user-attachments/assets/5b0a25a6-44a3-4065-b154-5198c2bc7160" width="400">

