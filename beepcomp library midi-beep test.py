from beepcomp import *
##whatever=song().MIDIimport().BEEPexport()
##export=whatever
file='SMB3_Boss'
if file:file+='.mid'
#file='Test 2.mid'
output(song().MIDIimport(file).BEEPexport(songname='Invention',composer='me',optional1='(c) my copyright').out())


##print(len(export.channels))
#output(filepicker(file).tracks)
finish()
