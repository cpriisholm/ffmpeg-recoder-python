#!/usr/bin/env python3

import argparse, subprocess, re, math, sys, os, tempfile

def output_path(output, input):
    """Based on given output and input this generates the actual output path.
    """
    root = ''
                
    if(output.startswith('+')):
        output = output[1:]
        root = os.path.dirname(input)
        
    oPath = os.path.dirname(output)
    oName = os.path.basename(output)
    _,oExt = os.path.splitext(output)
    if(oName.startswith('.')):
        oExt = oName
        oName = ''
    elif(not oPath.endswith('/')):
        oPath += '/'

    if (oPath == output):
        output = root + oPath + os.path.basename(input) 
    elif (not oExt):
        output = root + output + '/' + os.path.basename(input) 
    elif (not oName and oExt):
        output = root
        if(output and not output.endswith('/') and not oPath.startswith('/')):
            output += '/'
        output += oPath if oPath else (os.path.dirname(input) if not root else '')
        if(output and not output.endswith('/')):
            output += '/'
        output += os.path.splitext(os.path.basename(input))[0] + oExt
    return output
    

def parse_streams(probeOutput, verbose=False):
    """List the suggested streams.
    
    Given output from ffprobe this will print (if verbose) all streams and return a map
    with best suggestions - this will be one h264 video stream, one or two audio streams
    (stereo and 5.1 audio streams) and one dvb_subtitle stream (though not ones marked for
    hearing impaired)
    
    The maps returned have the following keys:
    type:    (video|audio|subtitle)<br>
    index:   integer<br>
    desc: comment related to stream - here for user-friendliness
    
    Returns a list of maps.
    """
    
    list = []
    # Seemingly no system when it comes to stream description, examples:
    #--- Kaffeine DVB-T (m2t):
    #Stream #0:0[0xd3]: Video: h264 (High) ([27][0][0][0] / 0x001B), yuv420p(tv, bt470bg), 704x576 [SAR 16:11 DAR 16:9], 25 fps, 50 tbr, 90k tbn, 50 tbc
    #Stream #0:1[0xdd](dan): Audio: aac_latm (HE-AAC) ([17][0][0][0] / 0x0011), 48000 Hz, stereo, fltp
    #Stream #0:2[0xe7](dan): Subtitle: dvb_teletext ([6][0][0][0] / 0x0006)
    #Stream #0:3[0xeb](dan): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006)
    #Stream #0:4[0xec](dan): Subtitle: dvb_subtitle ([6][0][0][0] / 0x0006) (hearing impaired)
    #--- Handbrake-ripped dvd (mkv)
    #Stream #0:0(eng): Video: h264 (High), yuv420p(tv, smpte170m/smpte170m/bt709), 706x300 [SAR 8:9 DAR 1412:675], SAR 127:143 DAR 44831:21450, 23.98 fps, 23.98 tbr, 1k tbn, 180k tbc (default)
    #Stream #0:1(eng): Audio: aac (LC), 48000 Hz, mono, fltp (default)
    #Stream #0:2(eng): Audio: ac3, 48000 Hz, mono, fltp, 192 kb/s
    #Stream #0:3(eng): Subtitle: subrip
    #--- Sony A5000 (MTS)
    #Stream #0:0[0x1011]: Video: h264 (High) (HDMV / 0x564D4448), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 25 fps, 25 tbr, 90k tbn, 50 tbc
    #Stream #0:1[0x1100]: Audio: ac3 (AC-3 / 0x332D4341), 48000 Hz, stereo, fltp, 256 kb/s
    #Stream #0:2[0x1200]: Subtitle: hdmv_pgs_subtitle ([144][0][0][0] / 0x0090), 1920x1080
    streamPattern = re.compile(r'^\s*Stream #\d:(\d)(\[\w+\])?(\(.+\))?: (\w+): (.+)$')
    STREAM_IDX = 1
    OPT_CODE = 2
    AUDIO_LANG = 3
    STREAM_CAT = 4
    REMAINDER = 5
    for it in probeOutput.splitlines():
        m = streamPattern.match(it)
        if m:
            map = {}
            if verbose:
                print(it.strip())
            switch = m.group(STREAM_CAT)
            if switch=='Video':
                if m.group(REMAINDER).startswith('h264'):
                    map['type']='video'
                    map['index']=m.group(STREAM_IDX)
                    #map['desc']=m.group(REMAINDER)
                    list.append(map)
            elif switch=='Audio':                   
                if ((not m.group(AUDIO_LANG) or m.group(AUDIO_LANG) == '(dan)' or m.group(AUDIO_LANG) == '(eng)') 
                    and [x for x in ['aac','ac3','mp3'] if m.group(REMAINDER).startswith(x)]):
                    map['type']='audio'
                    map['index']=m.group(STREAM_IDX)
                    map['desc']=m.group(REMAINDER)
                    list.append(map)
            elif switch=='Subtitle':
                if (m.group(REMAINDER).startswith('dvb_subtitle') or m.group(REMAINDER).startswith('subrip')) and m.group(REMAINDER).find('hearing impaired') == -1:
                    map['type']='subtitle'
                    map['index']=m.group(STREAM_IDX)
                    #map['desc']=m.group(REMAINDER)
                    list.append(map)
    return list


def concat_list(output, inputs):
    """Generates list if input files to be concatenated, as well as the final path for the output file.
    """
    root = ''
    _, default_ext = os.path.splitext(inputs[0])
    if(not output): 
        output = 'concat' + default_ext
    elif (os.path.basename(output) == output and not os.path.splitext(output)[1]):
        output = output + default_ext
    elif (os.path.dirname(output) == output):
        output = root + os.path.dirname(output) + 'concat' + default_ext # just a folder
    elif (not os.path.splitext(output)):
        output = root + output + '/' + 'concat' + default_ext # assume it is a folder without trailing slash
    list = []
    for it in inputs:
        list.append("file '{}'".format(os.path.abspath(it)))
    return (output,list)

    
# Time format [[hh:][mm:]ss] eg. 01:05:27, or 05:00 for five minutes, or 30 for half a minute (01:90 and 2 minute and 30 seconds if so inclined)
def to_seconds(format):
    rev = format.split(':')
    rev.reverse()
    return sum([int(s)*math.pow(60,idx) for idx,s in enumerate(rev)])


def from_seconds(secs):
    seconds = int(secs)
    return '{:0>2}:{:0>2}:{:0>2}'.format(seconds // 3600, (seconds % 3600) // 60, (seconds % 60))


def print_name(name):
    print('='*len(name))
    print(name)
    print('='*len(name))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dryrun", action="store_true",
                        help="Print the commands that would be executed without actually executing them")
    parser.add_argument("-o", "--output",
                        help="Output file (extension determines container). If a folder is given output is stored with the input filename in the given folder. If just an extension (e.g. .mkv) is given the input filename with the given extension is used as output (in either the same folder as the input, of if the extension is prefixed with a path in the folder given by the path, e.g. /tmp/.mp4). If prefixed with + the file is relative to the folder of input, e.g. +.mp4 will place a mp4 file in the input folder")
    parser.add_argument("-b", "--begin",
                        help="If set this marks the time (hh:mm:ss) - in relation to the input - at which to begin the output (default is from the start of input)")
    parser.add_argument("-e", "--end",
                        help="If set this marks the time (hh:mm:ss) - in relation to the input - at which to end the output (default is until the end of input)")
    parser.add_argument("-v", "--video", type=int,
                        help="If given it is the index of the video stream (counting from 0)")
    parser.add_argument("-a", "--audio", type=int,
                        help="If given it is the index of the audio stream (counting from 0)")
    parser.add_argument("-s", "--subtitle", type=int,
                        help="If given it is the index of the subtitle stream (counting from 0)")
    parser.add_argument("-z", "--streams", action="store_true",
                        help="If only the input file is given this print the streams found in that file and quits. If other parameters are given this will attempt to auto-detect the streams (if a stream type is explicitly given on command line, e.g. audio, then that is the only audio included even if input holds say stereo and 5.1 streams)")
    parser.add_argument("-x", "--transcode", action="store_true",
                        help="If given video stream will be encoded with h264, otherwise it will just be copied (as all other streams)")
    parser.add_argument("-c", "--concat", action="store_true",
                        help="If given the videos listed will be concatenated into one output video - if no output file is given then a file 'concat' with appropriate extension (taken from input) is created")
    parser.add_argument("files", nargs='*')
    args = parser.parse_args()
    
    inputs = args.files
    
    if(not inputs 
       or (args.streams and not inputs) 
       or (inputs and not (args.output or args.streams or args.concat))):
        print(parser.format_help())
        sys.exit(2)

    if (args.concat):
        # Don't consider other options - just concat the given inputs and copy to one output
        temp = tempfile.NamedTemporaryFile(prefix="recoder-concat-", suffix=".txt", mode="w+t")
        output, list = concat_list(args.output, inputs)
        # Write temp file with the files to concatenate
        for it in list:
            temp.write(it+'\n')
        temp.flush()
        # Give the file til ffmpeg
        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', temp.name, '-c', 'copy', output]
        if(args.dryrun):
            print("Concatenating:")
            with open(temp.name,'rt') as f:
                print(f.read())
            print("With:")
            print(cmd)
        else:
            proc = subprocess.Popen(cmd,stderr=subprocess.PIPE)
            for line in proc.stderr:
               print(line.rstrip().decode('utf-8'))
            code = proc.wait()
            if(code > 0):
                print("Error: '{}' returned exit code '{}' while '0' was expected".format(cmd, code), file=sys.stderr)
                sys.exit(3)
        temp.close()
        
    elif (args.streams and not args.output):
        #Special case - just probe and list the streams...
        for input in inputs:
            if (len(inputs) > 1):
                print_name(input)
            cmd = ['ffprobe']
            #options are for some detailed output, but getting the error streams holds the relevant info
            cmd.append(input)
            if (args.dryrun):
                print(cmd)
            proc = subprocess.Popen(cmd,stderr=subprocess.PIPE)
            code = proc.wait()
            if (code > 0):
                print("Error: '{}' returned exit code '{}' while '0' was expected".format(cmd, code), file=sys.stderr)
                sys.exit(5)
            else:
                list = parse_streams(proc.stderr.read().decode('utf-8'), args.dryrun)
                print('Suggested mapping:')
                for it in list:
                    print("{:.<8}: {} {}".format(it['type'],it['index'],'-- ' + it['desc'] if 'desc' in it else ''))
            print('')
            
    else:
        #ffmpeg needs the duration so we need to calculate that from begin and end
        period = None
        if (args.begin and args.end):
            period = from_seconds(to_seconds(args.end) - to_seconds(args.begin))
        elif (args.end):
            period = args.end

        videoCodec = 'h264' if args.transcode else 'copy'
        for input in inputs:
            if (len(inputs) > 1):
                print_name(input)
            output = output_path(args.output, input)
            vMap = args.video
            aMap1 = args.audio
            aMap2 = None
            sMap = args.subtitle
            #if streams probe is requested but all streams are given already skip the probing
            if (args.streams and not (vMap and aMap1 and sMap)):
                cmd = ["ffprobe"]
                #options are for some detailed output, but getting the error streams holds the relevant info
                cmd.append(input)
                proc = subprocess.Popen(cmd,stderr=subprocess.PIPE)
                code = proc.wait()
                if (code > 0):
                    print("Error: '{}' returned exit code '{}' while '0' was expected".format(cmd, code), file=sys.stderr)
                    sys.exit(6)
                list = parse_streams(proc.stderr.read().decode('utf-8'), False)
                # we'll consume max one video, two audio and one subtitle - if there are any further they are ignored
                for it in list:
                    if(it['type'] == 'video'):
                        if (not vMap):
                            vMap = it['index']
                    elif(it['type'] == 'audio'):
                        if (not aMap1):
                            aMap1 = it['index']
                        elif (not aMap2):
                            aMap2 = it['index']
                    elif(it['type'] == 'subtitle'):
                        if (not sMap):
                            sMap = it['index']

            #Set up main work (allowing to overwrite existing output)
            cmd = ["ffmpeg",  "-y"]
            if (args.begin): 
                cmd.append("-ss")
                cmd.append(args.begin)
            cmd.append("-i")
            cmd.append(input)
            if (vMap):
                cmd.append("-map")
                cmd.append("0:{}".format(vMap))
                cmd.append("-vcodec")
                cmd.append(videoCodec)
            if (aMap1):
                cmd.append("-map")
                cmd.append("0:{}".format(aMap1))
                cmd.append("-acodec")
                cmd.append("copy")
            if (aMap2):
                 cmd.append("-map")
                 cmd.append("0:{}".format(aMap2))
                 cmd.append("-acodec")
                 cmd.append("copy")
            if (sMap):
                 cmd.append("-map")
                 cmd.append("0:{}".format(sMap))
                 cmd.append("-scodec")
                 cmd.append("copy")                 
            if (period):
                 cmd.append("-t")
                 cmd.append(period)
            cmd.append(output)
    
            if (args.dryrun):
                print(cmd)
            else:
                proc = subprocess.Popen(cmd,stderr=subprocess.PIPE)
                
                reg = re.compile(r'.*time=([0-9]{2}:[0-9]{2}:[0-9]{2})\.[0-9]{2}.*')
                dur = re.compile(r'.*Duration: ([0-9]{2}:[0-9]{2}:[0-9]{2})\.[0-9]{2}.*')
                total = to_seconds(period) if period else None
                #for bytes in proc.stderr: --- fails since it ignores '\r' as a line termination
                line=''
                while True:
                    b = proc.stderr.read(1)
                    if not b:
                        break
                    else:
                        ch = b.decode('utf-8')
                        if ch == '\r' or ch == '\n':
                            m = reg.match(line)
                            if(m):
                                if (total):
                                    progress = to_seconds(m.group(1))
                                    percent = progress*100 / total
                                    print("{:5.1f}% >> {}".format(percent, line), end='\r')
                                else:
                                    print(line+'\r')
                            elif (not total):
                                m2 = dur.match(line)
                                if (m2):
                                    print("Run time: {}".format(m2.group(1)))
                                    total = to_seconds(m2.group(1))
                            line=''
                        else:
                            line += ch
                print('')
    
                code = proc.wait()
                proc.stderr.close()
    
                if (code > 0):
                    print("Error: '{}' returned exit code '{}' while '0' was expected".format(cmd, code), file=sys.stderr)
                    sys.exit(7)
            print('')

    sys.exit(0)
    
