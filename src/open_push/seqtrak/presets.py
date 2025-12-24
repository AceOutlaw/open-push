"""
Seqtrak Preset Name Lookup Tables
Generated from Yamaha Seqtrak Data List documentation.

Bank Select / Program Change mapping:
- MSB 63 (0x3F): Drum/Synth/DX sounds (tracks 1-10)
  - LSB 0-31 = Preset banks 1-32 (sounds 1-4096)
  - LSB 32-47 = User banks 1-16
  - Formula: sound_number = (LSB * 128) + Program + 1

- MSB 62 (0x3E): Sampler sounds (track 11)
  - LSB 0-3 = Preset banks 1-4 (sounds 1-512)
  - LSB 4-11 = User banks 1-8
  - Formula: sound_number = (LSB * 128) + Program + 1
"""

# Drum sounds (1-855)
DRUM_PRESETS = [
    # Kick (1-112)
    "Tight Punchy Kick 1", "Tight Punchy Kick 2", "Tight Punchy Kick 3", "Tight Punchy Kick 4",
    "Tight Punchy Kick 5", "Tight Punchy Kick 6", "Tight Punchy Kick 7", "Tight Punchy Kick 8",
    "Soft Kick 1", "Tight Soft Kick 1", "Tight Soft Kick 2", "Tight Soft Kick 3",
    "Tight Soft Kick 4", "Tight Soft Kick 5", "Tight Soft Kick 6", "Tight Soft Kick 7",
    "Punchy Fat Kick 1", "Punchy Fat Kick 2", "Punchy Fat Kick 3", "Punchy Fat Kick 4",
    "Punchy Fat Kick 5", "Bitcrushed Punchy Kick 1", "Punchy Fat Kick 6", "Punchy Fat Kick 7",
    "Distorted Kick 1", "Distorted Kick 2", "Distorted Kick 3", "Distorted Kick 4",
    "Distorted Kick 5", "Distorted Kick 6", "Distorted Kick 7", "Distorted Kick 8",
    "Saturated Tight Kick 1", "Saturated Fat Kick 1", "Saturated Tight Kick 2", "Saturated Fat Kick 2",
    "Saturated Fat Kick 3", "Saturated Fat Kick 4", "Saturated Fat Kick 5", "Saturated Fat Kick 6",
    "Saturated Fat Kick 7", "Punchy Saturated Kick 1", "Saturated Fat Kick 8", "Saturated Fat Kick 9",
    "Bitcrushed Kick 1", "Bitcrushed Kick 2", "Bitcrushed Kick 3", "Bitcrushed Kick 4",
    "Rumble Kick 1", "Rumble Kick 2", "Rumble Kick 3", "Rumble Kick 4", "Rumble Kick 5",
    "Punchy Kick + Reverb 1", "Punchy Kick + Reverb 2", "Punchy Kick + Reverb 3",
    "Muffled Kick 1", "Muffled Kick 2", "Muffled Kick 3", "Muffled Kick 4", "Muffled Kick 5", "Muffled Kick 6",
    "Lo-Fi Kick 1", "Lo-Fi Kick 2", "RX7 Kick 1", "RX5 Kick 1", "RX15 Kick 1",
    "RX7 Kick 2", "RX5 Kick 2", "RX7 Kick 3", "RX7 Kick 4", "RX7 Kick 5",
    "Acoustic Kick - Standard 1", "Acoustic Kick - Standard 2", "Acoustic Kick - Standard 3", "Acoustic Kick - Standard 4",
    "Acoustic Kick - Rock 1", "Acoustic Kick - Modern Rock 1", "Acoustic Kick - Jazz 1", "Acoustic Kick - Maple 1",
    "Modulated Kick 1", "Modulated Kick 2", "Punchy Kick + Electronic Ping 1", "Muffled Kick + Bell 1",
    "Punchy Kick + Perc 1", "Kick + Shaker 1", "Kick + Open Hat 1", "Kick + Open Hat 2",
    "Tonal Kick C", "Tonal Kick C#", "Tonal Kick D", "Tonal Kick D#",
    "Tonal Kick E", "Tonal Kick F", "Tonal Kick F#", "Tonal Kick G",
    "Tonal Kick G#", "Tonal Kick A", "Tonal Kick A#", "Tonal Kick B",
    "Distorted Tonal Kick C", "Distorted Tonal Kick C#", "Distorted Tonal Kick D", "Distorted Tonal Kick D#",
    "Distorted Tonal Kick E", "Distorted Tonal Kick F", "Distorted Tonal Kick F#", "Distorted Tonal Kick G",
    "Distorted Tonal Kick G#", "Distorted Tonal Kick A", "Distorted Tonal Kick A#", "Distorted Tonal Kick B",
    # Snare (113-214)
    "Tight Snare 1", "Tight Snare 2", "Tight Snare 3", "Short Pitched Snare 1",
    "Tight Snare 4", "Tight Snare + Reverb 1", "Tight Punchy Snare + Reverb 1", "Tight Snare 5",
    "Pitched Snare 1", "Tight Snare 6", "Tight Snare + Reverb 2", "Tight Snare + Reverb 3",
    "Tight Snare + Reverb 4", "Tight Snare + Reverb 5", "Tight Punchy Snare 1", "Punchy Fat Snare 1",
    "Distorted Pitched Snare 1", "Distorted Punchy Snare 1", "Punchy Fat Snare 2", "Distorted Fat Snare 1",
    "Distorted Fat Snare 2", "Punchy Fat Snare 3", "Punchy Fat Snare 4", "Punchy Fat Snare 5",
    "Distorted Low Snare 1", "Distorted Low Snare 2", "Punchy Long Snare 1", "Punchy Long Snare 2",
    "Click Wood Snare 1", "Double Click Snare 1", "Short Slow Snare 1",
    "Lo-Fi Snare 1", "Lo-Fi Snare 2", "Lo-Fi Snare 3", "Lo-Fi Snare 4", "Lo-Fi Snare 5",
    "Short Can Snare 1", "Muffled Snare 1", "Tight Snare + Reverb 6", "Tight Snare + Reverb 7",
    "Snare + Reverb 1", "Snare + Reverb 2", "Muffled Snare + Reverb 1", "Muffled Snare + Reverb 2",
    "Pitched Snare + Reverb 1", "Muffled Snare + Reverb 3", "Muffled Snare + Reverb 4",
    "Fat Snare + Reverb 1", "Punchy Snare + Reverb 1", "Distorted Snare + Reverb 1",
    "Gated Reverb Snare 1", "Gated Reverb Snare 2", "Spring Snare 1",
    "Trash Snare + Reverb 1", "Trash Snare + Reverb 2", "Trash Snare + Reverb 3",
    "Rx5 Snare 1", "Rx5 Snare 2", "RX7 Snare 1", "RX7 Snare 2",
    "RX7 Snare 3", "RX7 Snare 4", "RX7 Snare 5", "RX7 Snare 6",
    "Acoustic Snare - Standard 1", "Acoustic Snare - Standard 2", "Acoustic Snare - Soul 1",
    "Acoustic Snare - Standard 3", "Acoustic Snare - Standard 4",
    "Acoustic Snare - Punchy 1", "Acoustic Snare - Punchy 2", "Acoustic Snare - Metallic 1",
    "Acoustic Snare - Punchy 3", "Acoustic Snare - Tight 1", "Acoustic Snare - Tight 2",
    "Acoustic Snare + Reverb 1", "Acoustic Snare - Punchy 4", "Acoustic Snare - Punchy 5",
    "Acoustic Snare - Brush 1", "Acoustic Snare - Brush Tap 1", "Acoustic Snare - Flam 1",
    "Glitch Snare 1", "Glitch Snare 2", "Glitch Snare 3",
    "Hardcore Snare 1", "Hardcore Snare 2", "Hardcore Snare 3", "Hardcore Snare 4", "Hardcore Snare 5",
    "Snare + Wood Block 1", "Snare + Wood Block 2", "Wood Snare 1", "Factory Snare + Reverb 1",
    "Metallic Snare 1", "Metallic Snare 2", "Metallic Snare 3", "Metallic Snare 4", "Metallic Snare 5",
    "Glass Broken Snare 1", "Glass Broken Snare 2", "SFX Snare 1", "SFX Snare 2",
    # Rim (215-248)
    "Acoustic Rim - Jazz 1", "Acoustic Rim - Oak 1", "Acoustic Rim - Fat 1", "Acoustic Rim - Rock 1",
    "Acoustic Rim - Standard 1", "Acoustic Rim - High 1", "RX11 Rim 1", "RX5 Rim 1",
    "Acoustic Rim - Short 1", "Analog Rim 1", "Analog Rim 2", "Pitched Rim 1",
    "Lo-Fi Rim 1", "Lo-Fi Rim 2", "Lo-Fi Rim 3", "Stick Rim 1",
    "Acoustic Rim - Short 2", "High Pitched Rim 1", "Double Click Rim 1",
    "Acoustic Rim + Reverb 1", "Lo-Fi Rim + Reverb 1", "Acoustic Rim + Reverb 2", "Acoustic Rim + Reverb 3",
    "Noisy Rim 1", "Noisy Rim 2", "Noisy Rim 3", "Noisy Rim 4", "Noisy Rim 5", "Noisy Rim 6", "Noisy Rim 7",
    "Metallic Rim 1", "Double Click Rim 2", "Rim + Low 1", "Click Rim + Low 1",
    # Clap (249-296)
    "Hand Clap 1", "Hand Clap 2", "Hand Clap 3", "Hand Clap 4",
    "Group Clap 1", "Group Clap 2", "Group Clap 3", "Group Clap 4",
    "Hand Clap 5", "Bright Clap 1", "Bright Clap 2", "Lo-Fi Thin Clap 1",
    "Wide Thin Clap 1", "Bright Clap 3", "RX11 Clap 1", "Bitcrushed Clap 1",
    "Lo-Fi Clap 1", "Lo-Fi Clap + Reverb 1", "Slow Clap 1", "Short Clap 1", "Short Clap 2",
    "Short Double Clap 1", "Double Clap + Reverb 1", "Double Clap + Reverb 2",
    "Bright Clap 4", "Clicky Clap 1", "Long Clap + Reverb 1", "Long Clap + Reverb 2",
    "Hand Clap + Reverb 1", "Thin Clap + Reverb 1", "Thin Clap + Reverb 2",
    "Click Clap + Reverb 1", "Hand Clap + Reverb 2", "Hand Clap + Reverb 3",
    "Short Delay Clap 1", "Hand Clap + Reverb 4", "Hand Clap + Reverb 5",
    "Noise Clap 1", "Noise Clap 2", "Glitch Clap 1", "Glitch Clap 2", "Glitch Clap 3", "Glitch Clap 4", "Glitch Clap 5",
    "Modulated Hand Clap 1", "Woody Clap 1", "Arabic Hand Clap 1", "Woody Clap + Reverb 1",
    # Snap (297-311)
    "Finger Snap 1", "Finger Snap 2", "Finger Snap 3", "Finger Snap 4", "Finger Snap 5", "Finger Snap 6",
    "Wide Snap 1", "Wide Snap 2", "Fat Snap 1", "Fat Snap 2", "Woody Snap 1",
    "Snap + Reverb 1", "Snap + Reverb 2", "Click Snap 1", "Click Snap 2",
    # Closed HiHat (312-384)
    "Tight Closed Hat 1", "Tight Closed Hat 2", "Tight Closed Hat 3", "Tight Closed Hat 4",
    "Tight Closed Hat 5", "Tight Closed Hat 6", "Tight Closed Hat 7", "Tight Closed Hat 8",
    "Tight Closed Hat 9", "Tight Closed Hat 10", "Tight Closed Hat 11", "Tight Closed Hat 12",
    "Closed Hat 1", "Closed Hat 2", "Closed Hat 3", "Closed Hat 4", "Closed Hat 5", "Closed Hat 6",
    "Acoustic Closed Hat 1", "Closed Hat 7", "Closed Hat 8", "Closed Hat 9",
    "Acoustic Closed Hat 2", "Closed Hat 10", "Noise Closed Hat 1", "Noise Closed Hat 2",
    "Noise Closed Hat + Low 1", "Low Closed Hat 1", "Closed Hat + High Tone 1",
    "Acoustic Closed Hat 3", "Acoustic Closed Hat 4", "Acoustic Closed Hat 5", "Acoustic Closed Hat 6",
    "Acoustic Closed Hat 7", "Acoustic Closed Hat 8", "Acoustic Closed Hat 9", "Acoustic Closed Hat 10",
    "Acoustic Hat Pedal 1", "Acoustic Hat Pedal 2", "Acoustic Hat Pedal 3",
    "Acoustic Hat Pedal 4", "Acoustic Hat Pedal 5", "Acoustic Hat Pedal 6",
    "Click Closed Hat 1", "Lo-Fi Short Closed Hat 1", "Click Closed Hat 2",
    "Lo-Fi Short Closed Hat 2", "Lo-Fi Short Closed Hat 3", "Lo-Fi Short Closed Hat 4",
    "Lo-Fi Short Closed Hat 5", "Lo-Fi Short Closed Hat 6", "Lo-Fi Short Closed Hat 7",
    "Lo-Fi Short Closed Hat 8", "Lo-Fi Short Closed Hat 9", "Bitcrushed Hat 1",
    "Lo-Fi Closed Hat 1", "Lo-Fi Closed Hat 2", "Lo-Fi Closed Hat 3", "Lo-Fi Closed Hat 4",
    "Lo-Fi Closed Hat 5", "Lo-Fi Closed Hat 6", "Lo-Fi Closed Hat 7", "Lo-Fi Closed Hat 8", "Lo-Fi Closed Hat 9",
    "Closed Hat + Reverb 1", "Lo-Fi Closed Hat + Reverb 1",
    "Closed Hat + Reverb 2", "Closed Hat + Reverb 3", "Closed Hat + Reverb 4", "Closed Hat + Reverb 5",
    "Glitch Hat 1", "Glitch Hat 2", "Glitch Hat 3",
    # Open HiHat (385-456)
    "Bright Open Hat 1", "Bright Open Hat 2", "Bright Open Hat 3", "Bright Open Hat 4", "Bright Open Hat 5",
    "Noise Open Hat 1", "Noise Open Hat 2", "Noise Open Hat 3", "Noise Open Hat 4", "Noise Open Hat 5",
    "Noise Open Hat 6", "Noise Open Hat 7", "Noise Open Hat 8", "Noise Open Hat 9", "Noise Open Hat 10",
    "Noise Open Hat 11", "Noise Open Hat 12", "Noise Open Hat 13", "Noise Open Hat 14", "Noise Open Hat 15",
    "Bright Open Hat 6", "Acoustic Open Hat 1", "Acoustic Open Hat 2", "Acoustic Open Hat 3",
    "Acoustic Open Hat 4", "Acoustic Open Hat 5", "Acoustic Open Hat 6", "Acoustic Open Hat 7",
    "Crash Open Hat 1", "Crash Open Hat 2", "Crash Open Hat 3",
    "Bitcrushed Open Hat 1", "Bitcrushed Open Hat 2", "Bitcrushed Open Hat 3", "Bitcrushed Open Hat 4",
    "Distorted Open Hat 1", "Distorted Open Hat 2", "Distorted Open Hat 3", "Distorted Open Hat 4", "Distorted Open Hat 5",
    "Lo-Fi Open Hat 1", "Lo-Fi Open Hat 2", "Lo-Fi Open Hat 3", "Lo-Fi Open Hat 4", "Lo-Fi Open Hat 5",
    "Gated Open Hat 1", "Gated Open Hat 2", "Gated Open Hat 3", "Gated Open Hat 4", "Gated Open Hat 5",
    "Slow Attack Open Hat 1", "Slow Attack Open Hat 2", "Slow Attack Open Hat 3", "Slow Attack Open Hat 4",
    "Slow Attack Open Hat 5", "Slow Attack Open Hat 6", "Slow Attack Open Hat 7",
    "Open Hat with Bell 1", "Open Hat with Bell 2", "Open Hat with Bell 3",
    "Bell Open Hat 1", "Splash Open Hat 1", "Open Hat + Delay 1",
    "Open Hat + Reverb 1", "Open Hat + Reverb 2", "Panning Open Hat 1", "Panning Distorted Open Hat 1",
    "Modulated Open Hat 1", "Modulated Open Hat 2", "Modulated Open Hat 3",
    "Reversed Floor Hat 1", "Reversed Hat 1",
    # Shaker / Tambourine (457-497)
    "Shaker 1", "Shaker 2", "Shaker 3", "Shaker 4", "Shaker 5", "Shaker 6", "Shaker 7", "Shaker 8",
    "Shaker 9", "Shaker 10", "Shaker 11", "Short Shaker Accent 1", "Short Shaker Accent 2", "Short Shaker Accent 3",
    "Shaker + Reverb 1", "Shaker + Reverb 2", "Short Shaker Accent 4",
    "Shaker 12", "Shaker 13", "Shaker 14", "Shaker 15", "Arabic Maracas 1", "Caxixi 1", "Afoxe Open 1",
    "Muffled Shaker 1", "Tambourine 1", "Tambourine 2", "Tambourine 3", "Tambourine 4",
    "Tambourine 5", "Tambourine 6", "Tambourine 7", "Short Tambourine 1", "Tambourine 8",
    "RX5 Tambourine 1", "Long Tambourine 1", "Long Tambourine 2", "Long Tambourine 3",
    "Long Tambourine 4", "Long Tambourine 5", "Tambourine + Reverb 1",
    # Ride (498-527)
    "Sharp Ride 1", "Sharp Ride 2", "Noise Ride 1", "Sharp Ride 3",
    "Acoustic Ride 1", "Acoustic Ride - Brush 1", "Acoustic Ride 2", "Acoustic Ride 3",
    "RX7 Ride 1", "Ride Cup 1", "Ride Cup 2", "RX5 Ride Cup 1",
    "Color Ride 1", "Color Ride 2", "Color Ride 3", "Color Ride 4", "Color Ride 5",
    "Gate Ride 1", "Crash Ride 1", "Crash Ride 2", "Crash Ride 3",
    "Noise Ride 2", "Noise Long Ride 1", "High Noise Ride 1",
    "Synth Ride 1", "Synth Long Ride 1", "Dark Ride 1", "Slow Ride 1", "Noise Ride 3", "Bitcrushed Ride 1",
    # Crash (528-548)
    "RX5 Crash 1", "Acoustic Crash 1", "Acoustic Crash 2", "Acoustic Crash + Reverb 1",
    "Acoustic Crash 3", "Slow Acoustic Crash 1", "Acoustic Crash 4", "Acoustic Crash 5",
    "Splash Cymbal 1", "Splash Cymbal 2", "Splash Cymbal + Reverb 1",
    "Big Cymbal 1", "Big Cymbal 2", "Big Cymbal 3", "Cymbal Hammer 1", "China Cymbal 1",
    "4th Delay Crash 1", "Long Crash + Reverb 1", "Noise Crash 1", "Noise Crash 2", "Noise Crash 3",
    # Tom (549-618)
    "Acoustic High Tom 1", "Acoustic High Tom 2", "Acoustic Mid Tom 1", "Acoustic Mid Tom 2",
    "Acoustic Mid Tom 3", "Acoustic Mid Tom 4", "Acoustic Low Tom 1", "Acoustic Low Tom 2",
    "Punchy High Tom 1", "Punchy High Tom 2", "Punchy High Tom 3",
    "Punchy Mid Tom 1", "Punchy Mid Tom 2", "Punchy Mid Tom 3", "Punchy Mid Tom 4", "Punchy Mid Tom 5", "Punchy Mid Tom 6",
    "Punchy Low Tom 1", "Punchy Low Tom 2", "Punchy Low Tom 3",
    "Electronic High Tom 1", "Electronic High Tom 2", "Electronic High Tom 3", "Electronic High Tom 4", "Electronic High Tom 5",
    "Electronic Mid Tom 1", "Electronic Mid Tom 2", "Electronic Low Tom 1", "Electronic Low Tom 2",
    "RX5 High Tom 1", "RX5 Mid Tom 1", "RX5 Mid Tom 2", "RX5 Low Tom 1",
    "Acoustic High Tom - Oak 1", "Acoustic Mid Tom - Oak 1", "Acoustic Low Tom - Oak 1",
    "Acoustic High Tom - Jazz 1", "Acoustic Mid Tom - Jazz 1", "Acoustic Low Tom - Jazz 1",
    "Acoustic High Tom - Rock 1", "Acoustic Mid Tom - Rock 1", "Acoustic Low Tom - Rock 1",
    "Acoustic High Tom - Maple 1", "Acoustic Mid Tom - Maple 1", "Acoustic Low Tom - Maple 1",
    "Electronic High Tom + Reverb 1", "Muffled Mid Tom + Reverb 1", "Acoustic Mid Tom + Reverb 1",
    "Modulated Tom 1", "Modulated Tom 2", "Modulated Tom 3",
    "RX5 High Tom 2", "RX5 Mid Tom 3", "RX5 Mid Tom 4", "RX5 Low Tom 2",
    "Distorted Tom 1", "Distorted Tom 2", "Distorted Tom 3", "Distorted Tom 4",
    "Distorted Tom 5", "Distorted Tom 6", "Distorted Tom 7",
    "Bitcrushed Tom 1", "Bitcrushed Tom 2", "Bass Tom 1", "Bass Tom 2",
    "Tonal Bass Tom 1", "Bass Tom 3", "Bass Tom 4", "Bass Tom 5",
    # Bell (619-650)
    "Analog Cowbell 1", "Analog Cowbell Accent 1", "Tonal Cowbell 1", "Tonal Cowbell 2",
    "Metallic Cowbell 1", "Metallic Cowbell 2", "Metallic Cowbell 3",
    "Cowbell High 1", "Cowbell 1", "Cowbell Mid 1", "Cowbell Mid 2",
    "Agogo High 1", "Agogo Low 1", "Small Bell 1", "Short Bell 1", "Short Bell 2",
    "Tingsha Bell 1", "Ringing Bell 1", "Muted Finger Cymbal 1", "Muted Finger Cymbal 2",
    "Sagat1 Open 1", "Sagat1 Close 1", "Sagat2 Open 1", "Sagat2 Close 1",
    "Sagat3 Open 1", "Sagat3 Close 1", "Atarigane 1", "High Bell 1",
    "Mind Bell 1", "Sci-Fi Bell 1", "Bell and Noise 1", "Modulated Bell 1",
    # Conga / Bongo (651-676)
    "RX5 Conga High Open 1", "RX5 Conga High Mute 1", "RX5 Conga Low Open 1",
    "Conga1 High Slap 1", "Conga1 High Slap Open 1", "Conga1 High Open 1", "Conga1 Low Open 1",
    "Conga2 High 1", "Conga2 Mid 1", "Conga2 Mid Mute 1",
    "Conga3 High Mute 1", "Conga3 Mid Slap Open 1", "Khalg Conga Low",
    "Analog Conga High 1", "Analog Conga Mid 1", "Analog Conga Low 1",
    "RX5 Bongo High 1", "RX5 Bongo Low 1", "Bongo1 High Open 1", "Bongo1 Low Open 1",
    "Bongo2 High 1", "Bongo3 High 1", "Bongo3 High 2", "Bongo4 High 1", "Bongo4 Low 1", "Bongo4 Low 2",
    # World (677-787)
    "Djembe 1", "Djembe 2", "Djembe 3", "Djembe 4",
    "Talking Drum 1", "Talking Drum 2", "Talking Drum 3", "Talking Drum 4",
    "Tamborim Up 1", "Tamborim Down 1", "Tamborim Finger Back 1", "Tamborim Open 1",
    "Pandeiro Open 1", "Pandeiro Close 1", "Reco-reco 1",
    "Surdo Mute 1", "Surdo Stop 1", "Surdo Open 1", "Surdo Mute 2", "Surdo Stick 1",
    "Caixa Rim 1", "Vibraslap 1", "Darbuka Dum 1", "Darbuka Dom & Tak 1",
    "Darbuka Tak Finger 1", "Darbuka Tak Close 1", "Darbuka Slap 1", "Darbuka Sak 1",
    "Darbuka Rak 1", "Darbuka Flam 1", "Darbuka Noise 1",
    "Tunisian Bendir Dom 1", "Tunisian Bendir Tak 1", "Tunisian Bendir Tak 2",
    "Moroccan Bendir Dom 1", "Moroccan Bendir Dom 2", "Moroccan Bendir Dom 3", "Moroccan Bendir Edge 1",
    "Moroccan Tamtam 1", "Algerian Bendir Deza 1", "Algerian Bendir Kaf 1", "Algerian Galal Daza 1",
    "Riq Dum Open 1", "Riq Tek Open 1", "Riq Teke Open 1", "Riq Sak 1", "Riq Snouj Close 1",
    "Hollo Finger 1", "Bass Darbuka Dum 1", "Bass Darbuka Tek 1",
    "Bendir Tek 1", "Bendir Slap 1", "Bendir Large 1",
    "Merjaf Group Dom 1", "Merjaf Group Sak 1", "Zeer Dom 1", "Zeer Tak 1",
    "Merwas Group Dom 1", "Merwas Group Tak 1", "Medando Dom 1", "Medando Sak 1",
    "Sigal Marad Dom 1", "Sigal Marad Tak 1", "Doholla Dom 1", "Doholla Sak 1",
    "Katem Med Dom Open 1", "Katem Med Tak 1", "Katem Med Sak 1",
    "Taar Barashim Dom 1", "Taar Barashim Shake 1", "Req Sak 1", "Req Dom 1", "Req Open 1", "Req Sajat 1",
    "Udho Back 1", "Udho Chap Body 1", "Jahla Group Dom 1",
    "Iranian Bendir Tom 1", "Iranian Bendir Chap 1", "Iranian Bendir Back 1",
    "Tombak Tom 1", "Tombak Slap 1", "Tombak Chap 1", "Tombak Flam & Back 1", "Tempo Chap 1",
    "Tabla Dom 1", "Tabla Tak 1", "Tabla Sak 1", "Tabla 1", "Tabla 2", "Tabla 3", "Tabla 4", "Tabla 5",
    "Mridangam 1", "Mridangam 2", "Japanese Wa Taiko 1", "Japanese Oo Taiko 1",
    "Japanese Yagura Taiko 1", "Japanese Shime Taiko 1", "Japanese Tsuzumi 1",
    "Timbale 1", "Timbale 2", "Cajon 1", "Cajon 2", "Claves 1", "Wood Block 1",
    "Bones 1", "Bones 2", "Bones 3", "Bones Triplet 1", "Spoons 1",
    # SFX (788-855)
    "Laser - Falling 1", "Sci-Fi - Detected 1", "Sci-Fi - Drip 1", "Sci-Fi - Buzzed 1",
    "Laser - Falling 2", "Sci-Fi - Repeated 1", "Laser - Blast 1", "Laser - Scratch 1",
    "Fade In Noise 1", "Low Noise 1", "Gritty Noise 1", "Ambient Noise 1",
    "Ambient Percussion 1", "Ambient Percussion 2", "Ambient Percussion 3",
    "Ambient Percussion 4", "Ambient Percussion 5", "Ambient Percussion 6",
    "Percussion + Water 1", "Percussion + Water 2", "Percussion + Water 3",
    "Glass Crash 1", "Glass Broken 1", "Percussion + Glass Broken 1", "Glass Broken + Reverb 1", "Percussion + Glass Broken 2",
    "Foley Sound 1", "Foley Sound 2", "Foley Sound 3", "Foley Sound 4",
    "Foley Sound 5", "Foley Sound 6", "Foley Sound 7", "Foley Sound 8",
    "Camera Shutter 1", "Camera Shutter 2", "Camera Shutter 3", "Old Clock Tick 1",
    "Telephone 1", "Gunshot 1", "Bomb 1", "Scanning 1",
    "SFX High Bell 1", "SFX Pitched Tone 1", "Muffled Pitched Percussion 1", "Sine Percussion 1",
    "Water Tone 1", "Mid Resonated Tone 1", "Mid Resonated Tone 2", "Wood + Reverb 1",
    "Pitched SFX 1", "Trash Can 1", "Distorted Pitched Noise 1", "Dark Hit 1",
    "Percussion Hit 1", "Percussion Hit 2", "Percussion Hit 3", "Percussion Hit 4",
    "Gritty Hit 1", "Gritty Hit 2", "Panning Gritty Hit 1", "Punchy Gritty Hit 1",
    "Industrial Hit 1", "Industrial Hit 2", "Industrial Hit 3", "Industrial Hit 4", "Industrial Hit 5", "Industrial Hit 6",
]

# Synth sounds (856-1932) - index offset is 855
SYNTH_PRESETS = [
    # Bass (856-950)
    "Rn Bass", "Buzz Bass", "Acid3", "Bass Morpher", "3 VCOs", "Brain Bass", "Lo Boy", "Dark Bass",
    "Fundamental", "Fat Sine Resonance", "Moon Bass", "More Fatty", "Chill Out Bass", "Growler",
    "Smacked", "boooooooooom", "Biting", "Boogie A Legato", "Uni Punch", "Noise Bass",
    "Single Oscillator", "Unison", "Long Spit", "Big Bass", "Bass & Comp!", "Rave Blade",
    "Plastic Bass", "Funky Resonance", "Phat Three", "Needle Bass", "Acidd", "Boom Bass",
    "West Coast", "Wazzo", "Fast PWM Bass", "Bass Pedal", "Oxide", "Bowngo", "Wide Synth Bass",
    "Dry Synth Bass", "Kick Bass Legato", "Keep Dancin'", "Velo Master", "Wah Bass", "Pulse Step",
    "Phat Step", "Octave Analog", "Sync Bass", "Sync Big", "Puncher", "Dark Comp", "Simple Bass",
    "Fat Sine", "Kompressor", "Dark Uni", "Fight Bass", "Byon Bass", "One Voice", "Pro-Attack",
    "Bobby Bass", "Trance Bass", "Short SequenceBass", "Lately", "Faaat Pulse", "Short PWM Bass",
    "Hyper Velocity", "Deep Point", "Pulse Stop", "Oh Bee Bass", "Booming Bass", "Army Bass",
    "Punchy Drone", "Dee Tune", "Chorus Pulse", "Sweeper", "Synth Bass 1", "Synth Bass 2",
    "Universal", "Analog Bullet Bass", "Analog Perc Bass", "Analog Step Bass", "Upright",
    "Prec Flat Wound", "Round Wound", "Mid Range Finger", "Pick Open", "Pick Mute",
    "Slap Switch", "Fretless Dry", "Fretless Solo", "Dist Tama Bass", "5th Fuzz Bass",
    "Hybrid Bass 1", "Hybrid Bass 2", "House Organ Bass",
    # Synth Lead (951-1102)
    "Slow Saw Lead", "Darker Things Drone", "Analog Saw Dub", "Percussive Dance 1",
    "Multi Saw DA", "Dance Synth DA", "Percussive Dance 2", "Percussive Dance 2 [Chord]",
    "Power Hook", "Dance Survivor", "P5 Resonance Comp", "P5 Analog Punch", "P5 Analog Punch [Chord]",
    "Saw Lead", "Cool Trance", ">Attack<", "Club Finger", "Wobbly", "Wobbly [Chord]",
    "Ana Dayz", "Airy Nylon", "Progressive Attack", "Oracle", "Big Comp", "Big Comp [Chord]",
    "Rezz Punch", "Resonant Clavi", "Straight", "Straight [Chord]", "Psych Noise",
    "SquiffyMisbehaving", "Lektro Codes", "Lektro Codes [Chord]", "Hard FM Keyboard",
    "W Phaser", "DPCM Attack", "Talk", "Digy SEQ", "Nerve Nasty", "Ring Zplus",
    "Trance Attack", "Trance Attack [Chord]", "Tekno Attack", "PWM Percussion", "Stabby",
    "Detroit Stab", "Corrado", "Synthetique", "Noiz Rezz", "Tuxedo", "Queens", "Hip Voice",
    "GX1", "GX1 [Chord]", "Night Watch", "Pluck Bells", "Power Dance Chords", "Hyper Trance",
    "Cosmic Psyche", "Brightness", "Brightness [Chord]", "Calliope Lead", "Voice Lead",
    "Chiff Lead", "Charan Lead", "Fifth Lead", "Bass & Lead", "PWM Stabs", "Queen of Pop",
    "EDM Talker", "Huge Lead", "Bleep Lead", "Detuned Vintage", "Space Lead", "Square Lead",
    "Dual Square Lead", "Dual Square Lead [Chord]", "Vintage Sync", "Dirty Hook", "Nu Mini",
    "ProgressiveRk Lead", "Lucky", "Opening", "Rap Lead 1", "Mini Soft", "Feeling", "Early Lead",
    "Funky Pulse", "Mr. Finger", "Singleline", "Soft RnB", "Wind Synth", "Broken Sine",
    "Broken Sine [Chord]", "Duck Lead", "In da Night", "Mayday", "On D Line", "Early Soloist",
    "Heterodyne", "Classic 5th", "Vintage Saw", "Mini Three", "Phat Dino", "Dynamic Mini",
    "PWM Lead", "PWM Lead [Chord]", "Pulse Wound", "Think Sync", "Punch Lead", "Bright Saw",
    "Troy", "Wood Panel", "Push Ahead", "Eight", "Sync Power", "Glisten Lead", "Big Drone",
    "Screameemy", "Flange Filter", "Sutra", "Free LFO", "Rap Lead 2", "Space Power Lead",
    "Nyquist", "Digimetal", "Saw Destroy", "Vinalog Saw", "Mady SQU", "Low Undulation",
    "Impact", "Talk Mod", "Digital Gangsta", "Plastic Squeeze", "Pinz Lead", "Dancy Saw Lead",
    "Buzz Around", "Xtreme Wheel", "Supertrance", "Supertrance [Chord]", "Poly Hook",
    "HPF Dance", "Tekk Glide", "Growl Tekk", "Plucked Chordz", "Chordz", "Cool Body",
    "Twist Sync", "TEKIE", "Sonix", "Big SkidHookLead 1", "Big SkidHookLead 2",
    # Piano (1103-1134)
    "Full Concert Grand", "Concert GrandPiano", "Rock Grand Piano", "Rock Grand Piano [Chord]",
    "Rock Brite Piano", "Mellow Grand Piano", "Hall Mellow Grand", "Hall Mellow Grand [Chord]",
    "Glasgow", "Romantic Piano", "Aggressive Grand", "Tacky", "House Piano", "CP80 Layer",
    "CP80", "CP80 [Chord]", "CP80 Amp", "CP80 Chorus", "CP 1979", "CP70 Chorus", "Journey",
    "CP 2007", "Old and Squashed", "Ballad Key", "80s Layer", "Ballad Stack", "Piano Back",
    "Monaural Grand", "Old Blues", "Old Blues [Chord]", "1968", "Honkytonk",
    # Keyboard (1135-1214)
    "E.Piano 1", "Soft Case", "Soft Case [Chord]", "74 Phase", "Vintage'74", "R&B Soft",
    "Early 70's", "Crunchy Comp", "Vintage Case", "Hard Vintage", "Sweetness", "Phaser Vintage",
    "Vintage Phase", "Early Fusion", "Neo Soul", "1983", "1983 [Chord]", "Contempo",
    "Clicky Dyno", "Dyno Straight", "Dyno Chorus", "80s Boosted", "80s Boosted [Chord]",
    "Chorus Hard", "Max Tine", "Bell Chorus", "Drive EP", "Vinyl EP", "Natural Wr",
    "Natural Wr [Chord]", "Wr EP Bright", "Wr Distortion", "Phaze Wr", "E.Piano 2",
    "DX Legend", "Bell DX", "DX Woody", "DX Woody [Chord]", "Full Tine", "DX Mellow",
    "DX Crisp", "DX Celesta EP", "DX Pluck EP", "DX-7 II", "GS Tines", "Galaxy DX",
    "TX816 Bell Piano", "Marimba DX", "DX5-Zero", "Hybrid EP", "Mixed Up", "Dyno Wr",
    "Analog Piano", "AhrAmI", "Electro Piano", "Transistor Piano", "EP Pad", "DX Pad",
    "Grace EP", "Nu Touch Clavi", "Super Clavi 1", "PhaserClavi Mt", "Vintage Clavi",
    "Super Clavi 2", "Stereo Clavi", "Hollow Clavi", "Nu Phasing", "Touch Clavi", "Wah Clavi",
    "Pulse Clavi", "Brite Clavi", "Clavi Bril Treble", "Clavi Bril Treble [Chord]",
    "Clavi Amped", "Clavi Phaser", "Clavi Wah", "Harpsichord", "NaturalHarpsichord",
    "Octave Harpsichord", "E.Harpsichord",
    # Organ (1215-1289)
    "16 + 8 + 5&1/3", "First 3 w/Perc", "Slow Jam", "Cool Cat", "Jazzy 1", "Jazzy 1 [Chord]",
    "Jazzy 2", "Jazzy Chorus", "Draw Organ", "Percussive Organ", "Rock Organ", "On Road",
    "Progressy", "Rocky", "Crunchy", "Glassy", "Clean", "Vib Chorus", "Soulemn", "Mellow",
    "Fully", "FullDraw/CVibrato", "Even Out", "A Few Wheels", "A Few Wheels [Chord]",
    "Left Manual", "Draw Control", "Clean Noise", "Walking Bass", "Greasy", "Swishie",
    "Solo Percussion", "Percussion Vibrato", "Tiny Combo Bars 1", "Tiny Combo Bars 1 [Chord]",
    "Tiny Combo Bars 2", "Panther", "1967 Keyboard", "YD-45C", "Surf Rock", "Early Bird",
    "Vx Full Bars", "Vx Dark Bars", "Fr All Tabs", "Fr String Tabs", "Vx Full Bars Amped",
    "Vx Surf Organ", "Moet", "Bollinger", "Vinyl Organ", "Alternator", "Tradi", "Petit",
    "Petit [Chord]", "Fluty", "Fluty Pipe", "St. Peter", "St. Paul", "Impromptu", "Mixture",
    "Reed Split", "Medieval", "Medieval [Chord]", "Breath Pipe", "Reedy Pipe", "Sunday",
    "Church Organ", "Church Organ [Chord]", "Reed Organ", "Accordion", "Accordions",
    "Accordions [Chord]", "Tango Accordion 1", "Tango Accordion 2", "Master Accordion",
    # Pad (1290-1438)
    "Round Saw Phase", "Ducker Cloud", "Multi Saw Pad", "Poly Synth Pad", "Poly Pad DA",
    "HyperTrance Stereo", "Ethereal", "Ethereal [Chord]", "Saw Pad", "Dark ModulationPad",
    "Dark Light", "Ambient Synth Pad", "5th Lite", "Smooth BPF Sweep", "Trance", "Xtreme Sweep",
    "Warm Pad", "Nu Warm Pad", "Nu Warm Pad [Chord]", "5th Atmosphere", "Dim", "Simple Air",
    "Nature Sine", "Nature Sine [Chord]", "Analog", "Perc Pad", "Dark Atmo Pad",
    "Dark Atmo Pad [Chord]", "Dark Organ Pad", "Soft Brassy", "Road to Nowhere", "Analog Sweep",
    "Sweep Pad", "Sweep Strings", "Brass Motion Pad", "Luminous", "Mother Ship", "Warm Backing Pad",
    "Feather", "Feather [Chord]", "Pan Sphere", "Square", "Shaper", "Early Digital", "Dramana",
    "Dream Shift", "Dream Shift [Chord]", "Sound Track", "Remote Space", "Fathoms", "Mother Earth",
    "Landing Pad", "The Breath", "Feather Pad", "Slow Attack Pad", "Hi Brite", "Pad & Syn",
    "Pad & Syn [Chord]", "Cosmic Swell Pad", "Sweet Flange", "Waterfall", "Phase Pad",
    "Pure Synth", "Pure Synth + Delay", "Pearls", "Flange Wall", "Tornado", "Ice Rink",
    "Bell Pad", "Bell Pad [Chord]", "New Age Pad", "Paradise", "Yellow River", "Love Me",
    "Frozen Pad", "Bowed Pad", "Metal Pad", "Pensive", "Sci-Fi", "Atmosphere", "Halo Pad",
    "Space Vocals", "Haah Pad", "Oooh Pad", "Oooh Pad [Chord]", "Back in Itopian",
    "Strings & Choir", "Angel Eyes", "Glass Choir", "Nativity", "Seraphim", "Aah Choir",
    "Ooh Choir", "Syn Voice", "Choir Pad", "Mellow Swell", "Frozen Glasspad", "Lunar Eclipse",
    "Prayer Call", "Granular Motion", "Mysterious Invention", "Gate of Eden", "Whispering Ghosts",
    "NighttrainToMunich", "Morning Dew", "Calling Mr. Reso", "2 SwitchesToHeaven", "SEKAI-ISAN",
    "Setsunai", "Week End", "TiRiPAD", "Cluster", "Xtreme Rezz", "My Reality", "Magnetics",
    "Sand", "Felicity", "Vibrancy", "Radio Venus", "Elec Blue", "Chyo Ethno", "konjoh BEAM",
    "Blizzard", "SINGING BOWL", "Metalvox Pad", "Refraction", "Philanger", "Ellipsotron",
    "Envelope", "Whatsis", "Pearl Collection", "Four Dimensions", "Hallucination", "Electraid",
    "Clearing", "Long HiPa", "Quad Swell", "New Stab", "Vinyl Hit", "Hit Me", "Ambient Bite",
    "Bollog Puls", "Orchestra Hit", "Rain Pad", "Goblin", "Echoes", "Dripping Quarks",
    "Metallic Airstabs", "Descendant",
    # Strings (1439-1516)
    "Violin", "Violin Solo", "Viola", "Viola Solo 1", "Viola Solo 2", "Cello Solo", "Cello Duo",
    "ContrabassSolo1", "ContrabassSolo2", "Quartet", "Small Section", "Small Ensemble",
    "Small Ensemble [Chord]", "Almighty", "Medium Section", "Medium Hall", "Quick Bows",
    "Large Section", "Strings Section 1", "Strings Section 2", "Octave Ensemble", "Full Chamber",
    "Stryngs", "Stryngs [Chord]", "Dynamic Bow", "Pizzicato", "SymphonicPizzicato",
    "Plucky Pizzicato", "Octave Pizzes", "Tremolo Strings 1", "Tremolo Strings 2",
    "Tremolo Strs Small", "Spicato Large", "Spicato Large [Chord]", "Disco", "Lush",
    "Back Ground", "Warm Back", "Stringy", "Big Strings", "F.Horn + Strings",
    "Wood Winds+Strings", "Synth Strings 1", "Synth Strings 2", "Gleaming Pad",
    "Fat PWM Synth Vel", "VintagePolyStrings", "PWM Strings", "PWM Strings [Chord]",
    "Mourn Strings", "VP Soft", "PWM Simple", "Glassy Rezonant", "Superstrings", "Light Pad",
    "Noble Pad", "Warm Big", "Sentimental", "Analog Strings", "Analog Ensemble", "Phase Strings",
    "Octave Strings", "80s Clean Strings", "3 Oscillators Vin", "Silver Strings",
    "Silver Strings [Chord]", "String Machine", "3 Octave Strings", "TranceIntroduction",
    "Mystic Trance", "Electric Violin", "Tron Violin", "Tron Strings", "Tape Strings",
    "Orchestronic", "Vinyltron", "Beauty Harp", "Stereo Harp",
    # Brass (1517-1589)
    "Trumpet", "Tp Romantic Legato", "Classical Trumpet", "Bright Trumpet", "Tp SoftJazz Legato",
    "SoftTrumpetLegato", "Trumpet Vibrato", "Trumpet Shake Vel", "Legend Mute", "Flugelhorn",
    "Jazzy Flugel", "Trumpet Section", "Trumpet Section [Chord]", "Trombone", "Blown Bone Legato",
    "Bright Trombone", "NewOrleansTrombone", "French Horn", "French Horn Solo", "Tuba",
    "BassTuba(Bb)", "Euphonium", "FrenchHornSection1", "FrenchHornSection2", "French Horns",
    "F.Horn + Trombone", "F.Hrn+Trombone+Trp", "Orchestra Brass", "Orchestra Brass [Chord]",
    "Movie Horns", "Symphonic", "Smooth Brass", "Soft Brass mp-mf", "Dynamic Brass",
    "Accent mf-fall", "Small BrassSection", "MediumBrassSection", "Lots O' Brass",
    "Bright Section", "Power Section", "Shiny Brass", "Big Brass", "Sforzando",
    "Soft Brass & Sax", "Big Band", "Sax Big Band", "Velo Falls", "Hybrid Section",
    "Hybrid Bright", "Hybrid Brass Swell", "The Synth Brass", "T Brass", "Lo-fi", "Quiet Brass",
    "Big Syn", "Thinth", "XP Brass Stereo", "Simple Saw Brass", "Brassy", "Kustom",
    "After 1984", "After 1984 [Chord]", "Finale", "Huge CS80", "CS-90", "Oh Bee Soft",
    "Oh Bee Horns", "Slow PWM Brass", "Soft 5th Brass", "Synth Brass 1", "Synth Brass 2",
    "Oh Bee Syncomp", "Tacky Brass",
    # Woodwind (1590-1642)
    "Soprano Sax", "Soprano Legato", "Soprano Soft", "Mellow Soprano", "Alto Sax",
    "Alto Vib Legato", "Alto Legato", "Alto", "Alto Accent Legato", "Tenor Sax",
    "Tenor Dynamic", "Tenor Soft Legato", "Velo Growl Legato", "Tenor Max",
    "SoftTenorSaxLegato", "Baritone Sax", "Baritone", "Hip Bari", "Tenor Section",
    "Sax Octave Section", "Mixed Sax Section", "Piccolo", "Piccolo Legato", "Flute",
    "Flute Legato", "Sweet Flute", "Wood Flute", "Tron Flute", "Flootz", "2 Flutes", "Oboe",
    "Sweet Oboe Legato", "Oboe Soft Legato", "Clarinet", "Jazzy Cla Legato", "Bassoon 1",
    "Bassoon 2", "English Horn", "Flute & Clari", "2 Oboes & Bassoon", "Woodwindind Quartet",
    "Harmonica", "Gentle Harp", "Woody Harp", "Bluz Distort", "Campfire", "Irish Pipe Legato",
    "Recorder", "Pan Flute", "Shakuhachi", "Whistle", "Ocarina", "Bagpipe",
    # Guitar (1643-1738)
    "Classical", "High Tension", "Sao Paulo", "Barcelona", "Barcelona [Chord]",
    "Nylon Slide Vel", "NylonHarmonics Vel", "Classical12Strings", "Hip-HopNylonGuitar",
    "Old Strings", "Mute & Slide Vel", "SteelHarmonics Vel", "Hip-HopSteelGuitar",
    "Hi Strings", "Two Acoustics", "2 Steel Strings", "Airy 12", "Airy 12 [Chord]",
    "Wide 12 strings", "12Strings Mono", "Clean El & Ac", "Jazzy Pick", "Melodic Jazz",
    "Touch Wah", "Baby", "Good Night", "Dynamic Clean", "Single Coil Chorus",
    "Single Coil Chorus [Chord]", "1coil Clean", "1coil Amped Vel", "Distant", "Some Hair",
    "Hit It Hard", "Paddy Clean", "Dual Coil '65", "Dual Coil '65 [Chord]", "Dual Coil Amp",
    "Roto Guitar", "Dual Coil SlideVel", "Dual Coil Slap Vel", "Dual Coil 80sClean",
    "DualCoil80sCleanMt", "DualCoil80sCleanMt [Chord]", "Mute Guitar", "HIP Mute",
    "Dual Coil Rotary", "Electric 12Strings", "Rotator", "Middy Tremolo", "Retro Flanger",
    "Vintage Strum", "Vintage1coilChorus", "Spanky", "Rockabilly", "Surfin' 60s 1coil",
    "Pedal Steel", "2 Electrics", "Light Blues", "DualCoil SemiClean", "Breakback Mountain",
    "Chorus Dist", "Tex Boogie", "Tex Boogie [Chord]", "59 Combo", "Alternative Rocker",
    "Grunged Up", "Overdrive Mt&Harmo", "Crunched Up 376", "Dynamic Amp", "Chuggin' Guitar",
    "Chugga", "Small Amp", "Small Amp [Chord]", "Metal Mute", "DistortionMt&Harmo",
    "Cool Drive", "Hard Drive", "Hard Ramp", "Heavy Drive", "No.1 Guitar", "No.1 Guitar [Chord]",
    "Snake Finger", "Dual Coil BlueLead", "Voodooman", "Killer Whammy", "Latin Lover",
    "Oct Fuzz Wah", "Dual Coil Lead Wah", "Crunchy Guitar", "Beater", "Mid Drive",
    "Hard Rocker", "Tough Tube", "Drive Wah", "Guitar Harmonics",
    # World (1739-1773)
    "Sitar 1", "Sitar 2", "Sitar 3", "Tambura", "Banjo 1", "Banjo 2", "Shamisen", "Koto",
    "Baglama", "Saz Feeze", "Kanun", "Kotoun", "Bouzuki", "Where Am I?", "Sakura", "Nomad",
    "Nomad [Chord]", "Pluk-o-dy", "Kalimba", "Mbira", "Glass Mbira", "Fiddle", "Kemence",
    "Kemen Wet", "Yayli", "Kawala", "Ney", "Zurna", "Pungi", "Snake Charmer", "Shehnai 1",
    "Shehnai 2", "Mythic Flute", "Didgeridoo", "Kodo",
    # Mallet (1774-1793)
    "Xylophone", "Orch Xylophone", "Marimba", "Orch Marimba", "Soft Marimba", "Glocken",
    "Orch Glockenspiel", "Vibraphone", "Vibraphone Soft", "Vibes", "Vibes [Chord]",
    "Vibes Bow", "Celesta", "Ethnic Dream", "Orc Percussion", "Real Timpani",
    "Timpani + Cymbal", "Steel Drum", "Synth Steel Drum", "Dulcimer",
    # Bell (1794-1827)
    "Metallic Bell", "Twinkle", "Stick Bell", "Ice Bells", "Ice Bells [Chord]", "Bell Ice",
    "Stack Bell", "J-Pop", "Crystal", "Chorus Bell", "Handbell", "Bell Chiff", "Bell Chiff [Chord]",
    "Sako Bell", "Nice Bell", "Noisy Bell", "Pop Bells & Pad", "Pop Bells & Pad [Chord]",
    "Digibox", "Nibelungen", "Wood Bell", "Marimbell", "Gamelan", "Mystic Bowl", "Island Bell",
    "Tibetan", "Tibetan [Chord]", "Rimba Bells", "Lost in Asia", "Music Box", "Tinkle Bell",
    "Tubular Bells 1", "Tubular Bells 2", "Timp/Bell/Glocken",
    # Rhythmic (1828-1891)
    "Bass Morpher [Arp]", "Fat Sine Resonance [Arp]", "Boogie A Legato [Arp]", "Long Spit [Arp]",
    "Acidd [Arp]", "West Coast [Arp]", "Keep Dancin' [Arp]", "Phat Step [Arp]",
    "Short SequenceBass [Arp]", "Upright [Arp]", "Slap Switch [Arp]", "Multi Saw DA [Arp]",
    "Saw Lead [Arp]", "Airy Nylon [Arp]", "Rezz Punch [Arp]", "W Phaser [Arp]", "Noiz Rezz [Arp]",
    "Hip Voice [Arp]", "Hyper Trance [Arp]", "EDM Talker [Arp]", "Space Lead [Arp]",
    "Square Lead [Arp]", "ProgressiveRk Lead [Arp]", "Opening [Arp]", "Feeling [Arp]",
    "Mini Three [Arp]", "Nyquist [Arp]", "HPF Dance [Arp]", "Glasgow [Arp]", "House Piano [Arp]",
    "Vintage Case [Arp]", "Bell Chorus [Arp]", "PhaserClavi Mt [Arp]", "Marimba DX [Arp]",
    "Rocky [Arp]", "Crunchy [Arp]", "Walking Bass [Arp]", "Accordion [Arp]", "Perc Pad [Arp]",
    "Almighty [Arp]", "SymphonicPizzicato [Arp]", "Noble Pad [Arp]", "Trumpet [Arp]",
    "MediumBrassSection [Arp]", "Finale [Arp]", "Alto [Arp]", "Sao Paulo [Arp]",
    "Hip-HopNylonGuitar [Arp]", "Hip-HopSteelGuitar [Arp]", "Wide 12 strings [Arp]",
    "Baby [Arp]", "Dual Coil Amp [Arp]", "HIP Mute [Arp]", "Chorus Dist [Arp]",
    "Dynamic Amp [Arp]", "DistortionMt&Harmo [Arp]", "Heavy Drive [Arp]", "Banjo 2 [Arp]",
    "Sakura [Arp]", "Orch Xylophone [Arp]", "Celesta [Arp]", "J-Pop [Arp]", "Nibelungen [Arp]",
    "Lost in Asia [Arp]",
    # SFX (1892-1932)
    "Blaster Beam", "InsideTheWormhole", "Men In Yellow", "Metamorphosis", "Perplex",
    "Outer Planet", "Industrial", "Space Walking", "Scraper", "SE 02 <Zero Two>",
    "Talking Machines", "Tobi Mage", "Bitzz", "Toda", "Auto Trapeze", "Harpist'sNightmare",
    "Find Newgt!", "Nile River", "New Age Atmo", "Wind Blows", "Fire!", "Scratching Machine",
    "Goa Psyche", "WaitForBadWeather", "Reverse The Audio", "Radio Static", "Surveillance",
    "Noise FX", "Sample&HoldVintage", "Lazerzz", "On The Fritz", "Argentina", "Reverse Cymbal",
    "Fret Noise", "Breath Noiz", "Seashore", "Tweet", "Telephone 2", "Helicopter 1",
    "Applause", "Gunshot 2",
]

# DX sounds (1933-2032) - index offset is 1932
DX_PRESETS = [
    # Bass (1933-1945)
    "FM Lo-Fi Bass", "FM Up Bass", "FM Ducking Bass", "FM Amp Sub", "FM Decay Bass",
    "Wobble Bass", "FM Dark Bass", "Beep Bass", "Feel It", "Attack Bass",
    "FM Jet Bass", "FM Bold Bass", "FM Metal Dissonant",
    # Synth Lead (1946-1959)
    "FM Metallic Lead", "FM Square and 5th Saw", "Dyna Lead", "Mo Dem Lead", "Bit Tune",
    "Bleep Clv", "Uni Lead", "FM Chorus 5th Lead", "FM Square Module", "FM Lil Dist Airy",
    "FM Ring Lead", "FM Pan Trem Lead", "FM Saw Bright", "FM Crush Computer",
    # Piano (1960-1963)
    "FM Simple Piano", "FM B Piano", "FM B Piano [Chord]", "FM Clavi Piano",
    # Keyboard (1964-1972)
    "Legend EP", "Legend EP [Chord]", "Wood EP", "Wood EP [Chord]", "Wood EP Tremolo",
    "Crystal EP", "FM Chorus Jazz EP", "FM Clear EP", "DigiChord",
    # Organ (1973-1975)
    "Cheez Organ", "FM Rotate Organ", "FM Pipe A",
    # Pad (1976-1991)
    "FM 5th Atmosphere", "FM Glass Dream", "FM Glass Dream [Chord]", "Motion Pad",
    "Begin Sweep", "Cloud Pad", "Sol Phase", "Flying Kode", "AlTi Pad", "Star Pad",
    "FM Warm Pad", "FM Warm Pad [Chord]", "FM Glass Harp", "FM Slow Phaser Pad",
    "FM Ambient Pad", "FM Strings Pad",
    # Strings (1992-1993)
    "FM Strings", "FM Cold Strings",
    # Brass (1994-1999)
    "FM Soft Brass", "FM Digital Brass", "FM Brass", "FM Hit Brass", "FM Hit Brass [Chord]",
    "FM Fun Brass",
    # Woodwind (2000-2001)
    "FM Chorus Flute", "FM Sax",
    # Guitar (2002-2006)
    "FM Chorus Guitar", "FM Chorus Guitar [Chord]", "FM Wah Guitar", "FM Dist Guitar", "Ambi Pluck",
    # World (2007-2009)
    "FM Koto", "FM Shamisen", "FM Sitar",
    # Mallet (2010-2012)
    "FM Echo Mallet", "Tin Perc", "FM Marimba",
    # Bell (2013-2015)
    "FM Tubular Bells", "FM Tubular Bells [Chord]", "Future Bell",
    # Rhythmic (2016-2029)
    "FM Decay Bass [Arp]", "FM Dark Bass [Arp]", "Mo Dem Lead [Arp]", "Bit Tune [Arp]",
    "Uni Lead [Arp]", "FM Simple Piano [Arp]", "Legend EP [Arp]", "Wood EP [Arp]",
    "Star Pad [Arp]", "FM Brass [Arp]", "Ambi Pluck [Arp]", "FM Echo Mallet [Arp]",
    "Tin Perc [Arp]", "FM Marimba [Arp]",
    # SFX (2030-2032)
    "D'n Beats", "Buzz Siren", "Chopper",
]

# Sampler sounds (1-392) - separate bank (MSB 62)
SAMPLER_PRESETS = [
    # Vocal Count (1-24)
    "Female Count 1", "Female Count 2", "Female Count 3", "Female Count 4",
    "Female Count 5", "Female Count 6", "Female Count 7", "Female Count 8",
    "Male Count 1 A", "Male Count 2 A", "Male Count 3 A", "Male Count 4 A",
    "Male Count 5 A", "Male Count 6 A", "Male Count 7 A", "Male Count 8 A",
    "Male Count 1 B", "Male Count 2 B", "Male Count 3 B", "Male Count 4 B",
    "Male Count 5 B", "Male Count 6 B", "Male Count 7 B", "Male Count 8 B",
    # Vocal Phrase / Chant (25-75)
    "Female Vocal - Ha", "Female Vocal - Yo", "Female Vocal - Hey", "Female Vocal - Oh",
    "Female Vocal - Money", "Female Vocal - Go", "Male Vocal - Yo", "Male Vocal - Oh",
    "Male Vocal - Uh 1", "Male Vocal - Go", "Male Vocal- Whooh", "Male Vocal - Hey",
    "Male Vocal - OK", "Male Vocal - Say What", "Male Vocal - Big Up", "Male Vocal - Let's Go",
    "Male Vocal - Hey - Loud", "Male Vocal - Ooh - Loud", "Male Vocal - Wow - Loud",
    "Male Vocal - Bon", "Male Vocal - Get Funky", "Male Vocal - Ow", "Male Vocal - Uh 2",
    "Group Vocal - Ah uh", "Group Vocal - Hey", "Group Vocal - R U Ready?",
    "Group Vocal - Check It Out", "Group Vocal - Come On", "Group Vocal - Here We Go",
    "Group Vocal - Ho ho", "Group Vocal- Ho ho uh uh", "Group Vocal - Wussup",
    "Group Vocal - You You You", "Japanese Chant 1", "Japanese Chant 2", "Japanese Chant 3",
    "Japanese Chant 4", "Japanese Chant 5", "Japanese Chant 6", "Japanese Chant 7",
    "Japanese Chant 8", "Japanese Chant 9", "Japanese Chant 10", "Japanese Chant 11",
    "Japanese Chant 12", "Japanese Chant 13", "Japanese Chant 14", "Japanese Chant 15",
    "Japanese Chant 16", "Japanese Chant 17", "Japanese Chant 18",
    # Singing Vocal (76-98)
    "Singing - Female - Ah 1", "Singing - Female - Ah 2", "Singing - Female - Ai",
    "Singing - Female - La ah ah", "Singing - Female - Woo la", "Singing - Female - Aw oh",
    "Singing - Female - Ha ah 1", "Singing - Female - Haaaah", "Singing - Male - Ah ah",
    "Singing - Male - Oh oh woo", "Singing - Male - La a a a", "Singing - Male - Ah",
    "Singing - Male - Hooo", "Singing - Male - Hee", "Singing - Male - Uu",
    "Singing - Male - Everyday", "Singing - Male - Every Night", "Singing - Male - Yeeaaah",
    "Singing - Male - Oh wo", "Singing - Male - Oh wowo ah", "Singing - Male - Yeah ah ah",
    "Singing - Female - Ha ah 2", "Singing - Female - La la la la la",
    # Robotic Vocal / Effect (99-119)
    "High pitched vocal - Ah", "High pitched vocal - Top", "Vocoder Beat The Band",
    "Vocoder Love Is Blind", "Vocoder Freezing Cold", "Vocoder Destiny",
    "Vocoder Forbidden Dreams", "Vocoder Enjoying This", "Vocoder Desperation",
    "Vocoder Born Happy", "Vocoder Day Life", "Vocoder Reality", "Vocoder Dreamin Of U",
    "Vocoder Complicated", "Vocoder Mystery", "Vocoder Revolution", "Vocoder Sweeping",
    "Vocoder Yesterday", "Vocoder Close Eyes", "Vocoder Infinity", "Vocoder Deepwater",
    # Riser (120-136)
    "Riser - Noise 1", "Riser - Synth Lead & Noise 1", "Riser - Synth Lead 1",
    "Riser - Bubble 1", "Riser - Phase Synth Lead 1", "Riser - Phase Synth Lead 2",
    "Riser - Panned Synth Lead 1", "Riser - Panned Synth Lead 2", "Riser - Noise 2",
    "Riser - Bubble 2", "Riser - Noise 3", "Riser - Panned Noise 1", "Riser - Panned Noise 2",
    "Riser - Panned Noise 3", "Riser - Panned Noise 4", "Riser - Panned Noise 5",
    "Riser - Panned Noise 6",
    # Laser / Sci-Fi (137-196)
    "Laser - Blast 2", "Laser - Rapid Fire 1", "Laser - Blast 3", "Laser - Blast 4",
    "Laser - Blast 5", "Laser - Blast 6", "Laser - Blast 7", "Laser - Blast 8",
    "Noisy Laser - Blast 1", "Laser - Motion 1", "Laser - Rapid Fire 2", "Laser - Rapid Fire 3",
    "Laser - Flyby 1", "Laser - Echo 1", "Laser - Echo 2", "Laser - Echo 3", "Laser - Fizzer 1",
    "Laser - Vibration 1", "Laser - Echo 4", "Laser - Fleeting 1", "Laser - Signal 1",
    "Laser - Signal 2", "Laser - Signal 3", "Laser - Signal 4", "Laser - Signal 5",
    "Laser - Random Motion 1", "Laser - Signal 6", "Laser - Blast 9",
    "Sci-Fi - Data Transmission 1", "Sci-Fi - Data Transmission 2", "Sci-Fi - Data Transmission 3",
    "Laser - Falling 3", "Laser - After Shock 1", "Laser - Falling 4", "Laser - Falling 5",
    "Laser - Falling 6", "Laser - Falling 7", "Laser - Falling 8", "Laser - Falling 9",
    "Laser - Blast 10", "Laser - Blast 11", "Laser - Blast 12", "Laser - Echo 5",
    "Noisy Laser - Echo 1", "Noisy Laser - Echo 2", "Sci-Fi - Data Transmission 4",
    "Laser - Falling 10", "Laser - Falling 11", "Laser - Falling 12", "Laser - Signal 7",
    "Sci-Fi - Rapid Fire 1", "Sci-Fi - Detected 2", "Sci-Fi - Access Denied 1",
    "Sci-Fi - Error 1", "Sci-Fi - Calculation 1", "Sci-Fi - Connecting 1",
    "Sci-Fi - Deep Signal 1", "Sci-Fi - Deep Signal 2", "Sci-Fi - Deep Dive 1",
    "Sci-Fi - Deep Dive 2",
    # Impact (197-208)
    "Impact - Dark 1", "Impact - Tom & Cymbal 1", "Impact - Metal Hit 1", "Impact - Metal Hit 2",
    "Impact - Noise 1", "Impact - Noise 2", "Impact - Noise 3", "Impact - Noise 4",
    "Impact - Noise 5", "Impact - Noise 6", "Impact - Noise 7", "Impact - Noise 8",
    # Noise / Distorted Sound (209-242)
    "Noise - Fade In 1", "Noise - Fade In 2", "Noise - Fade In 3", "Noise - Explosion 1",
    "Noise - Explosion 2", "Noise - Explosion 3", "Noise - Explosion 4", "Distorted Hit 1",
    "Distorted Hit 2", "Distorted Hit 3", "Distorted Hit 4", "Distorted Hit 5",
    "Distorted Hit 6", "Distorted Hit 7", "Distorted Hit 8", "Distorted Hit 9",
    "Noise - Blast 1", "Noise - Blast 2", "Noise - Blast 3", "Noise - Blast 4",
    "Noise - Alert 1", "Noise - Signal 1", "Noise - Signal 2", "Noise - Signal 3",
    "Noise - Signal 4", "Noise - Passing 1", "Noise - Passing 2", "Noise - Passing 3",
    "Noise - Passing 4", "Noise - Passing 5", "Noise - Passing 6", "Noise - Take Off 1",
    "Noise - Take Off 2", "Granular Noise 1",
    # Ambient / Soundscape (243-254)
    "Ambient - Noise 1", "Ambient - Noise 2", "Ambient - Unstable 1", "Ambient - Synth bass 1",
    "Ambient - Unstable 2", "Ambient - Noise 3", "Ambient - Noise 4",
    "Ambient - Strings & Noise 1", "Ambient - Strings & Noise 2", "Ambient - Strings 1",
    "Ambient - Pad & Noise 1", "Ambient - Pad & Noise 2",
    # SFX (255-268)
    "Samba Whistle 1", "Gunshot 3", "Helicopter 2", "Police 1", "Can 1", "Cashier 1",
    "Gear 1", "Train Whistle 1", "Train Crossing 1", "Zipper 1", "Tongue Clicking 1",
    "Heart Beat 1", "Water Drop 1", "Metal Hit 1",
    # Scratch (269-292)
    "Scratch 1", "Scratch 2", "Scratch 3", "Scratch 4", "Scratch 5", "Scratch 6",
    "Scratch 7", "Scratch 8", "Scratch 9", "Scratch 10", "Scratch 11", "Scratch 12",
    "Scratch 13", "Scratch 14", "Scratch 15", "Scratch 16", "Scratch 17", "Scratch 18",
    "Scratch 19", "Scratch 20", "Scratch 21", "Scratch 22", "Scratch 23", "Scratch 24",
    # Nature / Animals (293-300)
    "Bird 1", "Bird 2", "Sheep 1", "Lion 1", "Thunder 1", "Thunder 2", "Rain 1", "Rain 2",
    # Hit / Stab / Musical Instrument Sound (301-319)
    "Brass Hit 1", "Brass Hit 2", "Brass Hit 3", "Synth Brass Hit 1", "Synth Brass Hit 2",
    "Synth Brass Hit 3", "Trumpet HIT 1", "String Hit 1", "Synth Chord Hit 1",
    "Piano Chord Hit 1", "Piano Chord Hit 2", "Piano Chord Hit 3", "Piano Chord Hit 4",
    "Guitar Clean - Delay 1", "Guitar Clean - Delay 2", "Guitar Clean - Delay 3",
    "Guitar Mute 1", "Guitar Mute 2", "Donk Bass 1",
    # Percussion (320-390)
    "Bongo3 High 3", "Bongo3 Low 1", "Bongo4 High 2", "Bongo4 Mid 1", "Bongo4 Low 3",
    "Analog Conga 1", "Analog Conga 2", "Conga3 High Slap Open 1", "Conga3 High Open 1",
    "Conga3 High Slap Mute 1", "Conga3 Low Open 1", "Conga3 Low Mute 1", "Repique 1",
    "Repique Rim 1", "Timbale 3", "Tan-tan Body 1", "Tan-tan Close 1", "Tan-tan Open 1",
    "Tan-tan Slap 1", "Surdo Mute 3", "Surdo Open 2", "Surdo Stop 2",
    "High Tom - Standard 1", "Mid Tom - Standard 1", "Low Tom - Standard 1",
    "Low Tom - Standard 2", "Floor Tom - Standard 1", "Cajon Ghost 1", "Cajon Low 1",
    "Analog Cowbell 2", "RX11 Cowbell 1", "Acoustic Cowbell 1", "Acoustic Cowbell 2",
    "Electric Wood Block 1", "Electric Wood Block 2", "Analog Claves 1", "Castanet 1",
    "Agogo High 2", "Agogo Low 2", "Analog Hand Clap 1", "Open Rim Shot 1",
    "Punchy Analog Snare 1", "Analog Snare 1", "Distorted Analog Snare 1",
    "Standard Hand Clap 1", "Electronic Snare 1", "Shaker 16", "Shaker 17", "Shaker 18",
    "Cabasa 1", "Cabasa 2", "Cabasa 3", "Maracas 1", "Shaker 19", "Tambourine 10",
    "Guiro 1", "Vibraslap 2", "Reco-reco 2", "Analog Closed Hat 1", "Analog Closed Hat 2",
    "Electronic Closed Hat 1", "Analog Open Hat 1", "Analog Open Hat 2",
    "Electronic Open Hat 1", "Ride 1", "Ride 2", "Ride 3", "Ride Brush 1",
    "Analog Crash 1", "Analog Crash 2", "Analog Glass 1",
    # Recorded Sound (391-392)
    "Recorded Sample 1", "Recorded Sample 2",
]

# Combined preset list for Drum/Synth/DX (sounds 1-2032)
# This combines all presets accessible via MSB 63
ALL_PRESETS = DRUM_PRESETS + SYNTH_PRESETS + DX_PRESETS


def get_preset_name(track: int, bank_msb: int, bank_lsb: int, program: int):
    """
    Get preset name for a track's bank/program selection.

    Args:
        track: Track number 1-11
        bank_msb: Bank Select MSB value (CC 0)
        bank_lsb: Bank Select LSB value (CC 32)
        program: Program Change value (0-127)

    Returns:
        Preset name string, or None if not found
    """
    # Calculate sound index
    index = (bank_lsb * 128) + program

    if bank_msb == 63:  # Drum/Synth/DX sounds
        if 0 <= index < len(ALL_PRESETS):
            return ALL_PRESETS[index]
    elif bank_msb == 62:  # Sampler sounds
        if 0 <= index < len(SAMPLER_PRESETS):
            return SAMPLER_PRESETS[index]

    return None


def get_preset_name_short(track: int, bank_msb: int, bank_lsb: int, program: int, max_len: int = 17) -> str:
    """
    Get a shortened preset name suitable for LCD display.

    Args:
        track: Track number 1-11
        bank_msb: Bank Select MSB value (CC 0)
        bank_lsb: Bank Select LSB value (CC 32)
        program: Program Change value (0-127)
        max_len: Maximum length (default 17 for Push LCD segment)

    Returns:
        Shortened preset name or fallback string
    """
    name = get_preset_name(track, bank_msb, bank_lsb, program)
    if name:
        # Truncate if needed
        if len(name) > max_len:
            return name[:max_len - 1] + "~"
        return name
    else:
        # Fallback to bank/program display
        return f"B{bank_msb}:{bank_lsb} P{program}"
