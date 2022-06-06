from beepcomp import chord
channels=[f'@{i+1}L1PRESET=BEEPWAVEFORM=0' for i in range(4)]
def addchord(code):
    for i,note in enumerate(chord(code)):channels[i]+=note
addchord('G')
addchord('A#')
addchord('C')
addchord('C')
for channel in channels:print(channel)
