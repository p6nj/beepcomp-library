from timidity import Parser, play_notes
from scipy import signal
from glob import glob
midi_list = glob("C:/Users/breva/Documents/midi/Mario & Luigi (and other Mario games) midis/songs/*.mid")
for filename in midi_list:
    ps = Parser(filename)
    print(filename.split('/')[-1].split('.')[0])
    play_notes(*ps.parse(),signal.square,basename=filename.split('\\')[-1].split('.')[0])