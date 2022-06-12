from beepcomp import chord
from sys import argv
#input='C,Am,Dm,G'
input=''.join(argv[2:]).replace(' ','')
codes=input.split(',')
channels=[f'@{i+1}L1PRESET=BEEPWAVEFORM={argv[1]}' for i in range(max((len(chord(c)) for c in codes)))]
def addchord(code):
    for i,note in enumerate(chord(code)):channels[i]+=note.replace('>','')
for code in codes:addchord(code)
for channel in channels:print(channel,end='')