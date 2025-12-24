# SEQTRAK MIDI Data Format

```text
MIDI Data Format 
1 Scope 
The specifications described herein apply to transmission and reception of MIDI data by a SEQTRAK. 
 
 
2 Compliance 
The specifications described herein comply with the MIDI 1.0 standard . 
 
 
(1) TRANSMIT FLOW 
MIDI OUT <--[SW1]--+---[SW2]--+---------------NOTE ON/OFF 9nH 
                       |            | 
                       |            +---[SW6]-------CONTROL CHANGE 
                       |            |  PORTAMENTO TIME BnH,05H 
                       |            |  CHANNEL VOLUME BnH,07H 
                       |            |  PAN  BnH,0AH 
                       |            |  MODEL-SPECIFIC BnH,(14H .. 15H) 
                       |            |  MODEL-SPECIFIC BnH,(17H .. 1DH) 
                       |            |  SUSTAIN SWITCH BnH,40H 
                       |            |  PORTAMENTO SWITCH BnH,41H 
                       |            |  FILTER RESONANCE BnH,47H 
                       |            |  EG ATTACK TIME BnH,49H 
                       |            |  FILTER CUTOFF FREQ BnH,4AH 
                       |            |  EG DECAY/RELEASE TIME BnH,4BH 
                       |            |  REVERB SEND  BnH,5BH 
                       |            |  DELAY SEND  BnH,5EH 
                       |            |  MODEL-SPECIFIC BnH,(66H .. 77H) 
                       |            | 
                       |            +---[SW7][SW8]--CONTROL CHANGE 
                       |            |  BANK SELECT MSB BnH,00H 
                       |            |  BANK SELECT LSB BnH,20H 
                       |            | 
                       |            +---[SW9][SW10]-PROGRAM CHANGE CnH 
                       |            | 
                       |            +---------------PITCH BEND CHANGE EnH 
                       | 
                       +---[SW3]------------------SYSTEM REALTIME MESSAGE  
                       |   TIMING CLOCK F8H 
                       | 
                       +---[SW4]------------------SYSTEM REALTIME MESSAGE 
                       |   START  FAH 
                       |   STOP  FCH 
                       | 
                       +--------------------------SYSTEM REALTIME MESSAGE  
                       |   ACTIVE SENSING FEH 
                       |  
                       +---[SW5]------------------SYSTEM EXCLUSIVE MESSAGE 
    BULK DUMP  F0H 43H 0nH 7FH 1CH bhH blH 0CH ahH amH alH ddH....ddH ccH F7H 
    PARAMETER CHANGE F0H 43H 1nH 7FH 1CH 0CH ahH amH alH ddH.....ddH F7H 
    IDENTITY REPLY F0H 7EH 7FH 06H 02H 43H 00H 41H ddH ddH mmH 00H 00H 7FH F7H  
      dd : Device family number / code 
        SEQTRAK : 64H 06H 
      mm : version 
        mm = (version no. - 1.0)) * 10 
        e.g.) version 1.0 mm = (1.0 - 1.0) * 10 = 0 
                version 1.5 mm = (1.5 - 1.0) * 10 = 5 
 
[SW1] SYSTEM Legacy/USB/Bluetooth MIDI In/Out 
[SW2] SYSTEM Legacy/USB/Bluetooth MIDI Transmit Channel Message 
[SW3] SYSTEM MIDI Clock Out 
[SW4] SYSTEM Transmit Sequencer Control  
[SW5] SYSTEM Legacy/USB/Bluetooth MIDI Transmit System Exclusive Message 
[SW6] SYSTEM Legacy/USB/Bluetooth MIDI Transmit Control Change 
[SW7] SYSTEM Legacy/USB/Bluetooth MIDI Transmit Bank Select 
[SW8] SYSTEM Receive/Transmit Bank Select 
[SW9] SYSTEM Legacy/USB/Bluetooth MIDI Transmit Program Change 
[SW10] SYSTEM Receive/Transmit Program Change 
The following System Exclusive messages are not affected by [SW1][SW5]. 
 SYSTEM Legacy/USB MIDI In/Out 
 SYSTEM Sink Current Setting 
  
110
SEQTRAK Data List
MIDI Data Format  
 
(2) RECEIVE FLOW 
MIDI IN >---------+---[SW1]--+--------------NOTE OFF  8nH 
                      |            | 
                      |            +--------------NOTE ON/OFF  9nH 
                      |            | 
                      |            +--------------CONTROL CHANGE 
                      |            |  PORTAMENTO TIME  BnH,05H 
                      |            |  DATA ENTRY MSB  BnH,06H 
                      |            |  DATA ENTRY LSB  BnH,26H 
                      |            |  CHANNEL VOLUME BnH,07H 
                      |            |  PAN  BnH,0AH 
                      |            |  EXPRESSION  BnH,0BH 
                      |            |  MODEL-SPECIFIC BnH,(14H .. 15H) 
                      |            |  MODEL-SPECIFIC BnH,(17H .. 1DH) 
                      |            |  SUSTAIN SWITCH BnH,40H 
                      |            |  PORTAMENTO SWITCH BnH,41H 
                      |            |  SOSTENUTO  BnH,42H 
                      |            |  FILTER RESONANCE BnH,47H 
                      |            |  EG ATTACK TIME BnH,49H 
                      |            |  FILTER CUTOFF FREQ BnH,4AH 
                      |            |  EG DECAY/RELEASE TIME BnH,4BH 
                      |            |  REVERB SEND  BnH,5BH 
                      |            |  DELAY SEND  BnH,5EH 
                      |            |  DATA ENTRY INC BnH,60H 
                      |            |  DATA ENTRY DEC BnH,61H 
                      |            |  MODEL-SPECIFIC BnH,(66H .. 77H) 
                      |            |  RPN 
                      |            |    PITCH BEND SENS. BnH,64H,00H,65H,00H,06H,mmH 
                      |            |    FINE TUNING BnH,64H,01H,65H,00H,06H,mmH,26H,llH 
                      |            |    COARSE TUNING  BnH,64H,02H,65H,00H,06H,mmH 
                      |            |    RPN RESET  BnH,64H,7FH,65H,7FH 
                      |            | 
                      |            +------[SW2]---CONTROL CHANGE 
                      |            |  BANK SELECT MSB BnH,00H 
                      |            |  BANK SELECT LSB BnH,20H 
                      |            | 
                      |            +--------------CHANNEL MODE MESSAGE 
                      |            |  ALL SOUND OFF BnH,78H 
                      |            |  RESET ALL CONTROLLERS BnH,79H 
                      |            |  ALL NOTE OFF BnH,(7BH .. 7DH) 
                      |            |  MONO MODE ON BnH,7EH 
                      |            |  POLY MODE ON BnH,7FH 
                      |            | 
                      |            +------[SW3]---PROGRAM CHANGE  CnH 
                      |            | 
                      |            +--------------PITCH BEND CHANGE EnH 
                      |            | 
                      |            +------[SW4]---SYSTEM REALTIME MESSAGE 
                      |            |  TIMING CLOCK F8H 
                      |            | 
                      |            +--------------SYSTEM REALTIME MESSAGE 
                      |            |  START  FAH 
                      |            |  CONTINUE  FBH 
                      |            |  STOP  FCH 
                      |            |  ACTIVE SENSING FEH 
                      |            | 
                      |            +--------------SYSTEM EXCLUSIVE MESSAGE 
                      |   BULK DUMP  F0H 43H 0nH 7FH 1CH bhH blH 0CH ahH amH alH ddH....ddH ccH F7H 
                      |   PARAMETER CHANGE F0H 43H 1nH 7FH 1CH 0CH ahH amH alH ddH.....ddH F7H 
                      |   DUMP REQUEST F0H 43H 2nH 7FH 1CH 0CH ahH amH alH F7H 
                      |   PARAMETER REQUEST F0H 43H 3nH 7FH 1CH 0CH ahH amH alH F7H 
                      | 
                      +-------------------------SYSTEM EXCLUSIVE MESSAGE 
    IDENTITY REQUEST F0H 7EH 0nH 06H 01H F7H 
 
[SW1] SYSTEM Legacy/USB/Bluetooth MIDI In/Out 
[SW2] SYSTEM Receive/Transmit Bank Select  
[SW3] SYSTEM Receive/Transmit Program Change 
[SW4] SYSTEM MIDI Sync (Internal/Auto) 
The following System Exclusive messages are not affected by [SW1]. 
 SYSTEM Legacy/USB MIDI In/Out 
 SYSTEM Sink Current Setting 
  
111
SEQTRAK Data List
MIDI Data Format  
 
(3) TRANSMIT/RECEIVE DATA 
(3-1) CHANNEL VOICE MESSAGES 
(3-1-1) NOTE OFF 
 STATUS  1000nnnn(8nH) n = 0 - 10 CHANNEL NUMBER 
 NOTE No.  0kkkkkkk  k = 0:C-2 - 127:G8 
 VELOCITY  0vvvvvvv  v = ignored 
 
(3-1-2) NOTE ON/OFF 
 STATUS  1001nnnn(9nH) n = 0 - 10 CHANNEL NUMBER 
 NOTE NUMBER  0kkkkkkk  k = 0:C-2 - 127:G8 
 VELOCITY NOTE ON 0vvvvvvv(v≠0) 
  NOTE OFF 0vvvvvvv(v＝0) Receive only. 
 
(3-1-3) CONTROL CHANGE 
 STATUS  1011nnnn(BnH) n = 0 - 10 CHANNEL NUMBER 
 CONTROL NUMBER 0ccccccc 
 CONTROL VALUE 0vvvvvvv 
 
 TRANSMIT 
 NUMBER NAME  VALUE  MEMO 
 0 BANK SELECT MSB 0 - 127  *1 
 32 BANK SELECT LSB 0 - 127  *1 
 5 PORTAMENTO TIME  0 - 127 
 7 TRACK VOLUME 0 - 127 
 10 PAN  0 - 127 
 20,21 MODEL-SPECIFIC   *4 
 25..29 MODEL-SPECIFIC   *4 
 65 PORTAMENTO SWITCH  0:OFF, 1:ON 
 71 FILTER RESONANCE 0:-64 - 64:0 - 127:+63 
 73 EG ATTACK TIME 0:-64 - 64:0 - 127:+63 
 74 FILTER CUTOFF FREQ 0:-64 - 64:0 - 127:+63 
 75 EG DECAY/RELEASE TIME 0:-64 - 64:0 - 127:+63 
 91 REVERB SEND  0 - 127  
 94 DELAY SEND  0 - 127 
 102..119 MODEL-SPECIFIC   *4 
 
RECEIVE 
 NUMBER NAME  VALUE  MEMO 
 0 BANK SELECT MSB 0 - 127  *1 
 32 BANK SELECT LSB 0 - 127  *1 
 5 PORTAMENTO TIME  0 - 127 
 6 DATA ENTRY MSB 0 - 127  *5 
 38 DATA ENTRY LSB 0 - 127  *5 
 7 TRACK VOLUME 0 - 127 
 10 PAN  0 - 127 
 11 EXPRESSION  0 - 127 
20,21 MODEL-SPECIFIC   *4 
 23..29 MODEL-SPECIFIC   *4 
 64 SUSTAIN SWITCH 0 - 127 
 65 PORTAMENTO SWITCH  0:OFF, 1:ON 
 66 SOSTENUTO  0-63:OFF, 64-127:ON 
 71 FILTER RESONANCE 0:-64 - 64:0 - 127:+63 
 73 EG ATTACK TIME 0:-64 - 64:0 - 127:+63 
 74 FILTER CUTOFF FREQ 0:-64 - 64:0 - 127:+63 
 75 EG DECAY/RELEASE TIME 0:-64 - 64:0 - 127:+63 
 91 REVERB SEND  0 - 127 
 94 DELAY SEND  0 - 127 
 96 DATA ENTRY INC 127  *5 
 97 DATA ENTRY DEC 127  *5 
 102..119 MODEL-SPECIFIC   *4 
 
 *1 Relation between BANK SELECT and PROGRAM is as follows: 
 CATEGORY   MSB LSB PROGRAM No.  
 Project  User 1 64 0 0 - 7 
 Sound  Preset 1 63 0 0 - 127 
   : : : : 
   Preset 32 63 31 0 - 127 
   User 1 63 32 0 - 127 
   : : : : 
   User 16 63 47 0 - 127 
 Sampler Element (*2) Preset 1 62 0 0 - 127 
   : : : : 
   Preset 4 62 3 0 - 127 
   User 1 62 4 0 - 127 
   : : : : 
   User 8 62 11 0 - 127 (*3) 
 
 *2 Regards Channel number as Element number. 
 
 *3 Program No. 72 and later are used as temporary areas for the sampler function. 
 
    Project 1 Elements 1..7, Project 2 Elements 1..7, Project 3… etc. 
  
112
SEQTRAK Data List
MIDI Data Format  
 
 *4 Model-specific controllers are as follows: 
 NUMBER NAME    VALUE   MEMO  
 20 EQ HIGH - GAIN   40:-12dB - 64:0 - 88:+12dB 
 21 EQ LOW - GAIN   40:-12dB - 64:0 - 88:+12dB 
 23 MUTE    0-63:OFF, 64-127:ON  Receive only 
 24 SOLO    0:OFF, 1:TRACK1 .. 11:TRACK11 Receive only 
 25 DRUM PITCH    40:-24 - 64:0 - 88:+24  for Drum 
 26 MONO/POLY/CHORD   0:MONO, 1:POLY, 2:CHORD" for Synth/DX 
 27 ARP TEMPLATE   0 - 15 (0:OFF)  for Synth/DX 
 28 ARP GATE    0:0% - 127:200%  for Synth/DX 
 29 ARP SPEED    0:200% - 3:100% - 9:25%  for Synth/DX 
 102 MASTER EFFECT 1 - ASSIGNED PARAMETER 1 0 - 127 
 103 MASTER EFFECT 1 - ASSIGNED PARAMETER 2 0 - 127 
 104 MASTER EFFECT 1 - ASSIGNED PARAMETER 3 0 - 127 
 105 MASTER EFFECT 2 - ASSIGNED PARAMETER 1 0 - 127 
 106 MASTER EFFECT 3 - ASSIGNED PARAMETER 1 0 - 127 
 107 SINGLE EFFECT - ASSIGNED PARAMETER 1 0 - 127 
 108 SINGLE EFFECT - ASSIGNED PARAMETER 2 0 - 127 
 109 SINGLE EFFECT - ASSIGNED PARAMETER 3 0 - 127 
 110 SEND REVERB - ASSIGNED PARAMETER 1  0 - 127 
 111 SEND REVERB - ASSIGNED PARAMETER 2  0 - 127 
 112 SEND REVERB - ASSIGNED PARAMETER 3  0 - 127 
 113 SEND DELAY - ASSIGNED PARAMETER 1  0 - 127 
 114 SEND DELAY - ASSIGNED PARAMETER 2  0 - 127 
 115 SEND DELAY - ASSIGNED PARAMETER 3  0 - 127 
 116 FM ALGORITHM   0 - 11   for DX 
 117 FM MODULATION AMOUNT   0 - 127   for DX 
 118 FM MODULATOR FREQUENCY 
  0 - 127   for DX 
 119 FM MODULATOR FEEDBACK   0 - 127   for DX 
 
 *5 Used only when a value is set using RPN. 
 
 Bank Select will be actually executed when the Program Change message is received. 
 Bank Select and Program Change numbers that are not supported by this product will be ignored. 
 
(3-1-4) PROGRAM CHANGE 
 STATUS      1100nnnn(CnH) n = 0 - 10 CHANNEL NUMBER 
 PROGRAM NUMBER 0ppppppp  p = 0 - 127  
 
(3-1-5) PITCH BEND CHANGE 
 STATUS  1110nnnn(EnH) n = 0 - 10 CHANNEL NUMBER 
 LSB  0vvvvvvv  PITCH BEND CHANGE LSB 
 MSB  0vvvvvvv  PITCH BEND CHANGE MSB 
 
 
(3-2) CHANNEL MODE MESSAGES 
 STATUS  1011nnnn(BnH) n = 0 - 10 CHANNEL NUMBER 
 CONTROL NUMBER 0ccccccc  c = CONTROL NUMBER 
 CONTROL VALUE 0vvvvvvv  v = DATA VALUE 
 
(3-2-1) ALL SOUND OFF (CONTROL NUMBER = 78H , DATA VALUE = 0) 
 All the sounds currently played, including channel messages such as Note-On and Hold-On 
 of a certain channel are muted this message is received. 
 
(3-2-2) RESET ALL CONTROLLERS (CONTROL NUMBER = 79H , DATA VALUE = 0) 
 Resets the values set for the following controllers. 
 PITCH BEND CHANGE 0 (center) 
 EXPRESSION  127 (maximum) 
 SUSTAIN SWITCH 0 (off) 
 SOSTENUTO SWITCH 0 (off) 
 RPN  Not assigned; No change 
 
(3-2-3) ALL NOTE OFF (CONTROL NUMBER = 7BH , DATA VALUE = 0) 
 All the notes currently set to on in certain channel(s) are muted when receiving this message. 
 However, if Sustain or Sostenuto is on, notes will continue sounding until these are turned off. 
 
(3-2-4) OMNI MODE OFF (CONTROL NUMBER = 7CH , DATA VALUE = 0) 
 Performs the same function as when receiving ALL NOTES OFF. 
 
(3-2-5) OMNI MODE ON (CONTROL NUMBER = 7DH , DATA VALUE = 0) 
 Performs the same function as when receiving ALL NOTES OFF. 
 
(3-2-6) MONO (CONTROL NUMBER = 7EH , DATA VALUE = 0..10) 
 The Channel is set to Mode 4. 
 
(3-2-7) POLY (CONTROL NUMBER = 7FH , DATA VALUE = 0..10) 
 The Channel is set to Mode 3. 
  
113
SEQTRAK Data List
MIDI Data Format  
 
 
(3-3) REGISTERED PARAMETER NUMBER  
 STATUS  1011nnnn(BnH) n = 0 - 10 CHANNEL NUMBER 
 LSB  01100100(64H) 
 RPN LSB  0ppppppp  p = RPN LSB (Refer to the table shown below.) 
 MSB  01100101(65H) 
 RPN MSB  0qqqqqqq  q = RPN MSB（Refer to the table shown below.) 
 DATA ENTRY MSB 00000110(06H) 
 DATA VALUE  0mmmmmmm  m = Data Value 
 DATA ENTRY LSB 00100110(26H) 
 DATA VALUE  0lllllll  l = Data Value 
 
 First, specify the parameter using RPN MSB/LSB numbers. 
 Then, set its value with data entry MSB/LSB. 
 
 RPN      D.ENTRY 
 LSB MSB  MSB LSB  PARAMETER NAME DATA RANGE 
 00H 00H  mmH llH  PITCH BEND SENSITIVITY 00H - 18H (0 - 24 semitones) 
 01H 00H  mmH llH  MASTER FINE TUNE {mmH,llH}={00H,00H}-{40H,00H}-{7FH,7FH} 
     (-8192*100/8192) - 0 - (+8191*100/8192) 
 02H 00H  mmH --- MASTER COARSE TUNE 28H - 40H - 58H (-24 - 0 - +24 semitones) 
 7FH 7FH  --- --- RPN RESET 
   RPN numbers will be left not unspecified. 
   The internal values are not affected. 
 
 
(3-4) SYSTEM REALTIME MESSAGES 
(3-4-1) ACTIVE SENSING 
 STATUS  11111110(FEH) 
 
 Transmitted at every 250 msec. 
 Once this code is received at a legacy MIDI interface, the instrument starts sensing. 
 When no status nor data is received for over approximately 500 ms, 
 The MIDI receiving buffer will be cleared, and any sounds currently playing are forcibly turned off. 
 
 
(3-5) SYSTEM EXCLUSIVE MESSAGES 
(3-5-1) UNIVERSAL NON REALTIME MESSAGE 
(3-5-1-1) IDENTITY REQUEST (Receive only) 
 F0H 7EH 0nH 06H 01H F7H (n = ignored) 
 
(3-5-1-2) IDENTITY REPLY (Transmit only) 
 F0H 7EH 7FH 06H 02H 43H 00H 41H ddH ddH mmH 00H 00H 7FH F7H  
      dd : Device family number / code  
        SEQTRAK : 64H 06H  
    
  mm : version 
        mm = (version no. - 1.0)) * 10 
        e.g.) version 1.0 mm = (1.0 - 1.0) * 10 = 0 
                version 1.5 mm = (1.5 - 1.0) * 10 = 5 
 
(3-5-2) PARAMETER CHANGE 
(3-5-2-1) NATIVE PARAMETER CHANGE, MODE CHANGE 
 11110000 F0 Exclusive status 
 01000011 43 YAMAHA ID 
 0001nnnn 1n Device Number 
 01111111 7F Group ID High 
 00011100 1C Group ID Low 
 00001100 0C Model ID 
 0aaaaaaa aaaaaaa Address High 
 0aaaaaaa aaaaaaa Address Mid  
 0aaaaaaa aaaaaaa Address Low 
 0ddddddd ddddddd Data 
 | | 
 11110111 F7 End of Exclusive 
 
 For parameters with data size of 2 or more, the appropriate number of data bytes will be transmitted. 
 See the following MIDI Data Table for Address. 
 
(3-5-3) BULK DUMP 
 11110000 F0 Exclusive status 
 01000011 43 YAMAHA ID 
 0000nnnn 0n Device Number 
 01111111 7F Group ID High 
 00011100 1C Group ID Low 
 0bbbbbbb bbbbbbb Byte Count 
 0bbbbbbb bbbbbbb Byte Count 
 00001100 0C Model ID 
 0aaaaaaa aaaaaaa Address High 
 0aaaaaaa aaaaaaa Address Mid  
 0aaaaaaa aaaaaaa Address Low  
 0 0 Data 
 | | 
 0ccccccc ccccccc Check-sum 
 11110111 F7 End of Exclusive 
 
 See the following MIDI Data Table for Address and Byte Count. 
 The Check-sum is the value that results in a value of 0 for the lower 7 bits 
 when the Byte Count, Start Address, Data and Check-sum itself are added. 
114
SEQTRAK Data List
MIDI Data Format  
 
(3-5-4) DUMP REQUEST 
 11110000 F0 Exclusive status 
 01000011 43 YAMAHA ID 
 0010nnnn 2n Device Number 
 01111111 7F Group ID High 
 00011100 1C Group ID Low 
 00001100 0C Model ID  
 0aaaaaaa aaaaaaa Address High 
 0aaaaaaa aaaaaaa Address Mid  
 0aaaaaaa aaaaaaa Address Low  
 11110111 F7 End of Exclusive 
 
 See the following MIDI Data Table for Address. 
(3-5-5) PARAMETER REQUEST 
 11110000 F0 Exclusive status 
 01000011 43 YAMAHA ID 
 0011nnnn 3n Device Number 
 01111111 7F Group ID High 
 00011100 1C Group ID Low 
 00001100 0C Model ID 
 0aaaaaaa aaaaaaa Address High 
 0aaaaaaa aaaaaaa Address Mid 
 0aaaaaaa aaaaaaa Address Low 
 11110111 F7 End of Exclusive 
 
 See the following MIDI Data Table for Address. 
 
 
(4) SYSTEM OVERVIEW 
 
 
115
```
