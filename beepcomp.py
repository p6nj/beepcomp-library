from string import ascii_uppercase
from mido import Message,MetaMessage,MidiFile,MidiTrack,tempo2bpm,tick2second
from tkinter.filedialog import askopenfilename
from os import path,remove
from os.path import exists
from math import ceil
from copy import deepcopy
Fo=1
pyper=True
musdl_=True

mid=None

try:import pyperclip # OPTIONAL PIP - copy results to clipboard
except ModuleNotFoundError:pyper=False
try:from musdl import OnlineScore
except ModuleNotFoundError:musdl_=False

class note:
    notes=[]
    for o in range(Fo,Fo+8):
        for n in ascii_uppercase[2:7]+ascii_uppercase[0:2]:
            notes.append('O'+str(o)+n)
            if n not in ('E','B'):notes.append('O'+str(o)+n+'#')
    ref={a+24:b for a,b in enumerate(notes)}
    def __init__(self,e='off',l=0,p=60,v=0):
        self.e=e# event of the note, on or off
        self.l=l# lengh of the note
        self.p=p# pitch midi value
        self.v=v# velocity
        if self.e=='on' and self.v==0:self.e='off'
    def bp(self,defaultoctave=4):# pitch in the beepcomp format
        if self.p in range(0,len(self.ref)):
            if self.e=='on':return self.ref[self.p]# the corresponding note in the reference list
            elif self.e=='off':return f'{self.ref[self.p][:2]}:'# a silence
            else:return f'O{defaultoctave}:'
        else:
            if not self.p:return f'O{defaultoctave}:'
            assert self.p<len(self.ref),f"The ref dict isn't big enough : need at least {self.p+1} values."
            return f'O{defaultoctave}:'
    def bl(self):# lengh in beepcomp format
        if not self.l:return None
        def nearest(nb):
            nb=ceil(nb)
            while nb%2:nb-=1
            return nb
        longueurs=[]
        total=self.l
        if self.l<1921:
            if 1920/self.l==nearest(1920/self.l):return int(1920/self.l)# abcdef
            else:# to this point, notes must be divided to keep the lengh intact
                n=2
                result=self.l/(1920/n)
                safetyfirst=0
                maxi=10
                while result!=int(result):
                    n*=2
                    result=self.l/(1920/n)
                    safetyfirst+=1
                    if safetyfirst==maxi:
                        #print('epic fail... self.l was '+str(self.l))
                        return None
                return [n for i in range(int(result))]# look for the smallest lengh that works and then return it the right amount of times
        while total>1920:
            total-=1920
            longueurs.append(1)
        if total:longueurs.append(int(1920/total))
        return longueurs

class track:
    def __init__(self,ns=[],na='Nameless :( (dummy text)'):
        self.ns=ns# list of notes in the note format
        self.na=na# name of the track
        self.garbo=[]# garbage dispenser, a place to put the remaining overlapping notes, waiting to be put in a new track
    def name(self,n):self.na=n# give a name to this track (overwrite)
    def add(self,n):self.ns.append(n)# add notes to the track (accumulate)
    def timefix(self):# set the time attribute of each note to the next notes' time attribute
        if self.ns[0].e=='on' and self.ns[0].l!=0:self.ns.insert(0,note(p=self.ns[0].p))
        for i,n in enumerate(self.ns[:-1]):
            n.l=self.ns[i+1].l
    def timeunfix(self):# undo the action above for BeepComp to midi conversion
        self.ns[0].l=0
        for i,note in enumerate(self.ns[1:]):
            note.l=self.ns[i-1]
    def noseparator(self):# remove the dynamic silence between notes that MuseScore build to play correctly with every instrument
        separator=0
        for i,note in enumerate(self.ns[1:]):
            if note.e=='off' and note.l<26:# i've seen these off notes go as far as 25 ticks
                separator=note.l# separator found
                break
        for note in self.ns:
            if note.e=='off':note.l-=separator
            else:note.l+=separator
        self.ns[-1].l=0
    def yesseparator(self):# undo the action above for BeepComp midi conversion
        pass
    def recycle(self,n):# pop the note from the list to the garbage can with its correct time
        staticlen=len(self.garbo)
        for i in range(staticlen,self.ns.index(n)):self.garbo.append(note(e='off',l=self.ns[i].l,p=self.ns[i].p,v=self.ns[i].v))
        self.garbo.append(self.ns.pop(self.ns.index(n)))
    def emptybin(self,song):
        if self.garbo:
            song.tk.append(track(ns=self.garbo,na=self.na+' (overflow)'))
            self.garbo=[]
            return 1# that's right, this function will return 1 if a track is appened to redo the parsing, how nice !
        return 0
    def isempty(self):# returns 1 if the track does not contain any note on
        return all(note.e=='off' for note in self.ns)

class song:# to stack up every track
    def __init__(self,tk=[],ti=[],to=0,n=0,d=0):
        self.tk=tk# tracks in the track format
        self.ti=ti# midi tempi
        self.to=to# real tempo
        self.n=n# numerator (number of notes in a measure)
        self.d=d# denominator (lengh of these notes)
    # EASY MODIFICATION
    def at(self,tk):self.tk.append(tk)# append a track
    def st(self,to):
        self.ti.append(to)# set tempo ; if there are more tempi in the song, it'll mess up with the notes time attribute.
        self.to=self.gt()
    def gt(self):return int(tempo2bpm(max(self.ti)[0]))# get the tempo that stayed for the longest time
    def timefix(self):# see above in the track section
        for track in self.tk:track.timefix()
    def noseparator(self):# same
        for track in self.tk:track.noseparator()
    # CONVERTION
    def BEEPimport(self):pass
    def MIDIimport(self,path=None):
        global mid
        if path:
            if exists(path):
                try:mid=MidiFile(path)
                except OSError:raise ValueError('Weird file mate... Nope, not parsing that.')
            else:raise RuntimeError('File not found.')
        else:mid=filepicker()
        if mid:
            for i,t in enumerate(mid.tracks):
                name='Nameless :( (dummy text)'# default name :( nameless :( dummy text :( might want to reduce the lengh of this string tho :( i was bored :(
                ns=[]
                last=len(t)-1
                for i,m in enumerate(t):
                    ty=m.type
                    if   'name' in ty:
                        if m.name[-1]=='\x00':name=m.name[:-1]# don't pick up EOL characters, they end lines and give weird results.
                        else:name=m.name
                    elif 'note' in ty:
                        ns.append(note(ty[5:],m.time,m.note,m.velocity))
                    elif 'tempo'in ty:self.st((m.tempo,t[i+1].time))
                    elif 'time' in ty:
                        self.n=m.numerator
                        self.d=m.denominator
                if ns:self.at(track(ns,name))
            self.timefix()
            self.noseparator()
            return self
        raise RuntimeError('File Picker does not approve.')
    def AUDIOimport(self,BPM=60):pass
    if musdl_:
        def MUSEimport(self,url):# import a midi via a MuseScore URL (piracy?)
            OnlineScore(url).export('mid','temp.beepbeep')
            return MidiFile('temp.beepbeep')
    def BEEPexport(self,**args):return beeptext(song=self,**args,MASTERVOLUME=70,V1=5,V2=5,V3=5,V4=5,V6=5,V7=5,V8=5,V9=5,VD=5,DELAY='OFF',DELAYTIME=400,DELAYLEVEL=26)
    def MIDIexport(self):pass

class beeptext:
    def __init__(self,header=None,channels=None,general=None,song=song(),songname='Nameless :( (dummy text)',game='',gameyear='',composer='',album='',albumyear='',
                 optional1='',optional2='',**generalparams):
        self.song=song
        self.songname=songname
        self.game=game
        self.gameyear=gameyear
        self.composer=composer
        self.album=album
        self.albumyear=albumyear
        self.optional1=optional1
        self.optional2=optional2
        self.generalparams=generalparams
        if not 'TEMPO' in self.generalparams:
            self.generalparams={'TEMPO':self.song.gt()}|self.generalparams# tempo must be the first element in the dictionary
        # HEADER
        if header:self.header=header
        else:self.buildHeader()# if a custom header isn't given, build one
        if general:self.general=general
        else:self.buildGeneral()
        if channels:self.channels=channels
        else:self.buildChannels()
    def buildHeader(self):
        def fill(l):return '//'+' '*(42-len(l))
        line=f'{48*"/"}\n'
        separator=f'//{44*" "}//\n'
        self.header=line+separator
        toolong=(len(self.songname)+len(self.game)+3)>43
        lines=[f'"{self.songname}"'*toolong,f'"{self.songname}"{" - "*(not not self.game)}'*(not toolong)+self.game,f'({self.gameyear})'*(not not self.gameyear),
               separator[3:-4]*all([self.composer,self.album,self.optional1,self.optional2]),f'Music by {self.composer}'*(not not self.composer),
               f'From Album "{self.album}"'*(not not self.album),self.optional1,self.optional2]
        for l in lines:
               self.header+=f'{fill(l)+l}  //\n'*(l!='')
        self.header+=separator+line+'\n'
    def buildGeneral(self):
        self.general='@G\n'
        for param in self.generalparams:self.general+=param+'='+str(self.generalparams[param])+'\n'
        self.general+='\n'
    def buildChannels(self):
        # HEADERS
        def fill(l):return f'// {l} '+(44-len(l))*'/'+'\n'
        self.channels=['' for n in self.song.tk]
        for n,track in enumerate(self.song.tk):
            if track.isempty():
                self.song.tk.pop(n)
                self.buildHeader()
                break
            octave=int(track.ns[0].bp()[1])
            lengh=track.ns[0].bl()
            if isinstance(lengh,list):lengh=lengh[-1]
            notes=[f'O{octave} L{lengh}\n']
            openedPitch=None
            for i,note in enumerate(track.ns):
                string=''
                # see if note is overlapping (then it must be opening or closing a new note (different pitch)
                if note.e=='on':
                    if openedPitch==None:openedPitch=note.p
                    else:
                        track.recycle(note)
                        continue
                if note.e=='off':
                    if not openedPitch:pass
                    elif openedPitch==note.p:openedPitch=None
                    else:
                        track.recycle(note)
                        continue
                if note.bl():
                    if isinstance(note.bl(),int):fullnote=f' L{note.bl()} '*(lengh!=note.bl())+note.bp()[2:]# abcdef
                    elif isinstance(note.bl(),list):
                        fullnote=f' L1 '*(lengh!=1)+note.bp()[2:]
                        lengh=1
                        for lenghs in note.bl()[1:]:
                            fullnote+=f' L{lenghs} '*(lengh!=lenghs)+'~'*(note.bp()[2:]!=':')+':'*(note.bp()[2:]==':')
                            lengh=lenghs
                else:fullnote=''
                try:
                    if note.bl():notes.append((octave-int(note.bp(octave)[1]))*'<'+(-1)*(int(octave)-int(note.bp(octave)[1]))*'>'+fullnote)
                except TypeError:raise RuntimeError('Nonetype in the variable'+'s'*((not octave)+(not lengh)+(not note.bp())+(not note.bl)>1)+' '+'octave '*(not octave)+'lengh '*(not lengh)+'note.bp() '*(not note.bp(octave))+'note.bl() '*(not note.bl())+f'(note {i} track {n+1})'+output(mid.tracks))
                octave=int(note.bp()[1])
                if note.bl():lengh=note.bl()
            if track.emptybin(self.song) and not self.song.tk[-1].isempty():
                self.buildChannels()
                break
            try:self.channels[n]+=fill(f'channel {n+1} - '+track.na)+f'\n@{n+1}\n'+(''.join(notes))
            except IndexError:print(len(self.channels))
    def out(self):return self.header+self.general+('\n\n'.join(self.channels))

# AfterEffects : reviewing the produced text looking for patterns (/!\ OLD CODE /!\)
def RecursiveRLE(e,m):
    if m==0:return e
    if m==1:
        for i in range(len(e)-1):
            print(e[i])
            end='' # output string
            lastletter='' # e[i-1]
            seen=1 # number of occurences of e[i-1] in e[:i-1]
            if e[i]==e[i+1]: # two matching letters
                if e[i]==lastletter:seen+=1 # the letter was already seen before
                else: # a new letter : release the temp variables
                    if seen>3:end+='{'+str(seen)+lastletter+'}' # when the modification is allowed and saves space
                    else:end+=seen*lastletter # the modification does not save space
                    # temp variables released, it can safely update them
                    lastletter=e[i]
                    seen=2 # seen twice since there is a match
            else: # the two letters do not match
                # release temporary variables in the output string
                if seen>3:end+='{'+str(seen)+lastletter+'}' # see above for this line and the next
                else:end+=seen*lastletter
                end+=e[i]
                lastletter=e[i]
                seen=1
        return end
    for i in range(len(e)-2*m+3+(len(e)%2==0)-m):
        if e[i:i+m-1]==e[i+m:2*m-1]:
            return('{'+RecursiveRLE(e[i:i+m-1],m-1)+'}')
    return(RecursiveRLE(e,m-1))

def prepareMasks():
    _notes_=note.notes[:12*2]
    notes=[]
    for i in range(len(_notes_)):
        n=_notes_.pop(0)
        if not '#' in n:notes.append(n[2:])
    m=[1,1,0,1,1,1,0]
    masks={}
    for n in notes:
        masks[n]=deepcopy(m)
        m.append(m.pop(0))
    return masks

masks=prepareMasks()

def mode(mode='C',base='C',reverse=False):
    cursor=note.notes.index('O4'+base)
    output=base
    octave=4
    mask=masks[mode]
    print(mask)
    if reverse:mask.reverse()
    for step in mask:
        if reverse:cursor-=step+1
        else:cursor+=step+1
        if octave!=int(note.notes[cursor][1]):output+=(-1)*(octave-int(note.notes[cursor][1]))*'>'
        output+=note.notes[cursor][2:]
        octave=int(note.notes[cursor][1])
    if reverse:
        output=output[1:]
        if output[0]=='>':output=output[1:]
    else:
        output=output[:-1]
        if output[-1]=='>':output=output[:-1]
    return output

def scale(tonality='C',reverse=False):
    if tonality[-1]=='m':return mode('A',tonality[:-1],reverse)
    return mode('C',tonality.replace('M',''),reverse)

def chordOLD(code='C'):
    if len(code)>1:
        if '/' in code:first,base=code.split('/')
        else:
            first,base=code,code[:2]
            if base[1]!='#':base=base[0]
    else:first,base=code,code
    print(first)
    print(base)

def chord(code='C'):
    #[tonality,color,more,base]
    fillers=['' for i in range(4)]
    fill=0
    color=
    for i,c in enumerate(code):
        if c.isnumeric() and code[i-1]=='m':
        fillers[fill]+=c

chord('Cm7')

class pattern:
    def __init__(self,string=''):
        self.string=string
    def scale(self):pass

def filepicker(midi=True):
    print('Waiting for file...')
    path=askopenfilename(title="Pick a MIDI", filetypes=[('penis music', '.mid .midi')])
    if not path:raise RuntimeError('Nothing selected.')
    try:mid=MidiFile(path)
    except OSError:raise ValueError('Weird file mate... Nope, not parsing that.')
    return mid

def output(o):
    o=str(o)
    if pyper:
        pyperclip.copy(o)
        print('Copied to clipboard.')
    else:
        copy=False
        npath='userdata/'+path.split("/")[-1].split(".")[0]+'.txt'
        c=1
        if path.isfile(npath):copy=True*(input('BeepComp .txt file already exists. Overwrite ? (y/*)')!='y')
        if copy:
            while os.path.isfile(npath):
                npath='userdata/'+path.split("/")[-1].split(".")[0]+f' ({c}).txt'
                c+=1
        file=open(npath,'w')
        file.write(o)
        file.close()
        print(f'Output written in "{npath}".')
    return ''
    #system('COLOR 0A')# attempt to change the colors of the console

def compact(string):
    output=string
    for l,line in enumerate(output.split('\n')):
        if line[:2]=='//' or line=='\n':output.split('\n')[l]=''
    return output.replace(' ','').replace('\n','')

def finish():
    if musdl_ and os.path.exists("temp.beepbeep"):os.remove("temp.beepbeep")
