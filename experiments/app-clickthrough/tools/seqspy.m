// seqspy: log everything sent TO the SEQTRAK (via MIDI Monitor's spy driver) and FROM it.
// Output lines: "HH:MM:SS.mmm OUT|IN <hex bytes>"  (OUT = app/any client -> SEQTRAK, IN = SEQTRAK -> Mac)
// Build: clang -fobjc-arc -framework CoreMIDI -framework Foundation -F"/Applications/MIDI Monitor.app/Contents/Frameworks" -framework SnoizeMIDISpy -Wl,-rpath,"/Applications/MIDI Monitor.app/Contents/Frameworks" seqspy.m -o seqspy
#import <Foundation/Foundation.h>
#import <CoreMIDI/CoreMIDI.h>
#include <sys/time.h>

typedef struct __MIDISpyClient *MIDISpyClientRef;
typedef struct __MIDISpyPort *MIDISpyPortRef;
extern OSStatus MIDISpyInstallDriverIfNecessary(void);
extern OSStatus MIDISpyClientCreate(MIDISpyClientRef *out);
extern OSStatus MIDISpyPortCreate(MIDISpyClientRef c, MIDIReadBlock block, MIDISpyPortRef *out);
extern OSStatus MIDISpyPortConnectDestination(MIDISpyPortRef p, MIDIEndpointRef dest, void *refCon);

static NSMutableData *sysexBuf[2];

static void emit(const char *dir, const Byte *b, size_t n) {
    struct timeval tv; gettimeofday(&tv, NULL);
    struct tm tm; localtime_r(&tv.tv_sec, &tm);
    NSMutableString *s = [NSMutableString stringWithFormat:@"%02d:%02d:%02d.%03d %s",
                          tm.tm_hour, tm.tm_min, tm.tm_sec, (int)(tv.tv_usec / 1000), dir];
    for (size_t i = 0; i < n; i++) [s appendFormat:@" %02X", b[i]];
    printf("%s\n", s.UTF8String);
    fflush(stdout);
}

// Split a packet into messages; drop clock/active sensing; join SysEx split across packets.
static void handle(int which, const MIDIPacketList *pl) {
    const char *dir = which ? "IN " : "OUT";
    const MIDIPacket *p = &pl->packet[0];
    for (UInt32 k = 0; k < pl->numPackets; k++) {
        const Byte *d = p->data; size_t n = p->length, i = 0;
        while (i < n) {
            Byte st = d[i];
            if (sysexBuf[which].length || st == 0xF0) {
                size_t j = i;
                while (j < n && d[j] != 0xF7) j++;
                [sysexBuf[which] appendBytes:d + i length:(j < n ? j + 1 : n) - i];
                if (j < n) { emit(dir, sysexBuf[which].bytes, sysexBuf[which].length); sysexBuf[which].length = 0; }
                i = (j < n) ? j + 1 : n;
                continue;
            }
            if (st == 0xF8 || st == 0xFE) { i++; continue; }
            size_t len = 1;
            if (st >= 0x80 && st < 0xF0) len = ((st & 0xF0) == 0xC0 || (st & 0xF0) == 0xD0) ? 2 : 3;
            else if (st == 0xF2) len = 3; else if (st == 0xF1 || st == 0xF3) len = 2;
            if (i + len > n) len = n - i;
            emit(dir, d + i, len);
            i += len;
        }
        p = MIDIPacketNext(p);
    }
}

int main(void) {
    @autoreleasepool {
        sysexBuf[0] = [NSMutableData data]; sysexBuf[1] = [NSMutableData data];
        OSStatus e = MIDISpyInstallDriverIfNecessary();
        if (e) fprintf(stderr, "install driver: %d\n", (int)e);
        MIDIEndpointRef dest = 0, src = 0;
        for (ItemCount i = 0; i < MIDIGetNumberOfDestinations(); i++) {
            CFStringRef nm = NULL; MIDIEndpointRef ep = MIDIGetDestination(i);
            MIDIObjectGetStringProperty(ep, kMIDIPropertyDisplayName, &nm);
            if (nm && [(__bridge NSString *)nm containsString:@"SEQTRAK"]) dest = ep;
        }
        for (ItemCount i = 0; i < MIDIGetNumberOfSources(); i++) {
            CFStringRef nm = NULL; MIDIEndpointRef ep = MIDIGetSource(i);
            MIDIObjectGetStringProperty(ep, kMIDIPropertyDisplayName, &nm);
            if (nm && [(__bridge NSString *)nm containsString:@"SEQTRAK"]) src = ep;
        }
        if (!dest || !src) { fprintf(stderr, "SEQTRAK not found (dest %d src %d)\n", (int)dest, (int)src); return 1; }
        MIDISpyClientRef sc; MIDISpyPortRef sp;
        if ((e = MIDISpyClientCreate(&sc))) { fprintf(stderr, "spy client: %d\n", (int)e); return 1; }
        if ((e = MIDISpyPortCreate(sc, ^(const MIDIPacketList *pl, void *rc) { handle(0, pl); }, &sp))) { fprintf(stderr, "spy port: %d\n", (int)e); return 1; }
        if ((e = MIDISpyPortConnectDestination(sp, dest, NULL))) { fprintf(stderr, "spy connect: %d\n", (int)e); return 1; }
        MIDIClientRef cl; MIDIPortRef ip;
        MIDIClientCreate(CFSTR("seqspy"), NULL, NULL, &cl);
        MIDIInputPortCreateWithBlock(cl, CFSTR("in"), &ip, ^(const MIDIPacketList *pl, void *rc) { handle(1, pl); });
        MIDIPortConnectSource(ip, src, NULL);
        fprintf(stderr, "seqspy: listening (OUT = to SEQTRAK, IN = from SEQTRAK)\n");
        CFRunLoopRun();
    }
    return 0;
}
