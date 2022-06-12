from beepcomp import chord
channels=[f'@{i+1}L1PRESET=BEEPWAVEFORM=0' for i in range(4)]
def addchord(code):
    for i,note in enumerate(chord(code)):channels[i]+=note
addchord('C')
addchord('G/B')
addchord('A#')
addchord('F')
for channel in channels:print(channel,end='')